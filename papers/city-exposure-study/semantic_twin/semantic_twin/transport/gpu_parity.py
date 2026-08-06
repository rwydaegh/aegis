"""Reproducible CPU and CUDA checks for the Mitsuba SBR path.

Mitsuba variants are process global.  This module therefore runs each variant
in a fresh Python process and compares artifacts only after every process has
exited.  The parent creates the ray directions once, so the raw intersection
check sends exactly the same floating-point inputs to every backend.
"""

from __future__ import annotations

import json
import pathlib
import statistics
import time
from dataclasses import asdict, dataclass, replace
from typing import Any

import numpy as np

from ..illumination import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL, sample_sphere
from .gpu_parity_orchestration import compare_variants as _compare_variants, run_workers as _run_workers
from .gpu_parity_report import (
    acceptance as _acceptance,
    compare_artifacts,
    compare_device_artifacts,
    cross_worker_consistency as _cross_worker_consistency,
    sha256_array as _sha256_array,
)
from .gpu_parity_runtime import collect_provenance, sha256_file as _sha256_file

__all__ = [
    "ParityConfig",
    "compare_artifacts",
    "compare_device_artifacts",
    "fixed_rays",
    "run_harness",
    "run_variant",
]


MODEL_CATALOGUE = {
    "isotropic": ISOTROPIC,
    "rooftop": ROOFTOP,
    "street_small_cell": STREET_SMALL_CELL,
}


@dataclass(frozen=True)
class ParityConfig:
    """Inputs shared by all variant subprocesses."""

    mesh: str
    output: str
    variants: tuple[str, ...] = ("llvm_ad_rgb", "cuda_ad_rgb")
    face_class: str | None = None
    origin: tuple[float, float, float] = (0.0, 0.0, 52.34)
    rays: int = 200_000
    repeats: int = 3
    seed: int = 20_260_804
    epsilon: float = 1.0e-5
    max_hit_mismatch_fraction: float = 0.0
    max_material_mismatch_fraction: float = 5.0e-4
    max_distance_error_m: float = 5.0e-5
    max_scientific_error_db: float = 1.0e-4
    max_device_error: float = 1.0e-3
    require_device_sbr: bool = True
    ray_epsilon_m: float = 1.0e-3
    frequency_hz: float = 15.0e9
    local_cells: int = 256
    exit_bands: int = 18
    max_bounces: int = 3
    permittivity_real: float = 5.31
    permittivity_imag: float = -0.4
    rms_height_m: float = 0.0

    def validate(self) -> None:
        mesh = pathlib.Path(self.mesh)
        if not mesh.is_file():
            raise FileNotFoundError(f"mesh does not exist: {mesh}")
        if self.face_class is not None and not pathlib.Path(self.face_class).is_file():
            raise FileNotFoundError(f"face-class array does not exist: {self.face_class}")
        if len(self.variants) < 2:
            raise ValueError("at least two Mitsuba variants are required")
        if len(set(self.variants)) != len(self.variants):
            raise ValueError("Mitsuba variants must be unique")
        if self.rays <= 0 or self.repeats <= 0:
            raise ValueError("rays and repeats must be positive")
        tolerances = (
            self.epsilon,
            self.ray_epsilon_m,
            self.max_hit_mismatch_fraction,
            self.max_material_mismatch_fraction,
            self.max_distance_error_m,
            self.max_scientific_error_db,
            self.max_device_error,
        )
        if any(value < 0.0 for value in tolerances):
            raise ValueError("epsilon values must be non-negative")
        if self.max_hit_mismatch_fraction > 1.0 or self.max_material_mismatch_fraction > 1.0:
            raise ValueError("mismatch fractions cannot exceed one")
        if self.local_cells <= 0 or self.exit_bands <= 0 or self.max_bounces < 0:
            raise ValueError("grid sizes must be positive and max_bounces non-negative")


def fixed_rays(config: ParityConfig) -> tuple[np.ndarray, np.ndarray]:
    """Return the exact first SBR batch for ``config.seed``."""
    rng = np.random.default_rng(config.seed)
    directions = sample_sphere(config.rays, rng)
    origins = np.tile(np.asarray(config.origin, dtype=np.float64), (config.rays, 1))
    origins += config.ray_epsilon_m * directions
    return origins, directions


def _synchronise() -> None:
    """Wait for queued Dr.Jit work when the installed release exposes a hook."""
    try:
        import drjit as dr
    except ImportError:
        return
    for name in ("sync_thread", "sync_device"):
        hook = getattr(dr, name, None)
        if callable(hook):
            try:
                hook()
            except (RuntimeError, TypeError):
                continue


def _timed(call: Any) -> tuple[Any, float]:
    _synchronise()
    started = time.perf_counter()
    answer = call()
    _synchronise()
    return answer, time.perf_counter() - started


def _timing(first: float, warm: list[float], *, first_label: str) -> dict[str, Any]:
    return {
        "first_seconds": first,
        "first_label": first_label,
        "warm_seconds": warm,
        "warm_median_seconds": statistics.median(warm),
        "warm_min_seconds": min(warm),
    }


def _load_face_class(path: str | None, face_count: int) -> np.ndarray:
    if path is None:
        return np.zeros(face_count, dtype=np.int64)
    face_class = np.asarray(np.load(path), dtype=np.int64)
    if face_class.shape != (face_count,):
        raise ValueError(f"face-class array has shape {face_class.shape}, expected ({face_count},)")
    if np.any(face_class < 0):
        raise ValueError("face-class values must be non-negative")
    return face_class


def _load_fixed_rays(
    config: ParityConfig, rays_path: pathlib.Path, expected_hashes: dict[str, str]
) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    with np.load(rays_path) as saved:
        origins = np.asarray(saved["origins"], dtype=np.float64)
        directions = np.asarray(saved["directions"], dtype=np.float64)
    expected_shape = (config.rays, 3)
    if origins.shape != expected_shape or directions.shape != expected_shape:
        raise ValueError(f"fixed-ray arrays must both have shape {expected_shape}")
    hashes = {"origins": _sha256_array(origins), "directions": _sha256_array(directions)}
    if hashes != expected_hashes:
        raise ValueError(f"fixed-ray hashes changed: expected {expected_hashes}, read {hashes}")
    return origins, directions, hashes


def run_variant(
    config: ParityConfig,
    variant: str,
    rays_path: pathlib.Path,
    artifact_path: pathlib.Path,
    expected_ray_hashes: dict[str, str],
) -> dict[str, Any]:
    """Run one backend.  The CLI calls this only inside a fresh process."""
    from ..propagation.geometry import MitsubaGeometry
    from .tracer import SbrTracer, TraceConfig

    config.validate()
    started = time.perf_counter()
    geometry = MitsubaGeometry(config.mesh, variant=variant)
    _synchronise()
    load_seconds = time.perf_counter() - started
    provenance = collect_provenance(config, variant)
    face_class = _load_face_class(config.face_class, geometry.face_count)
    origins, directions, ray_hashes = _load_fixed_rays(config, rays_path, expected_ray_hashes)

    raw, raw_cold = _timed(lambda: geometry.intersect(origins, directions))
    raw_warm: list[float] = []
    for _ in range(config.repeats):
        raw, seconds = _timed(lambda: geometry.intersect(origins, directions))
        raw_warm.append(seconds)
    hit, distance, normal, face = raw
    material = np.full(config.rays, -1, dtype=np.int64)
    material[hit] = face_class[face[hit]]

    trace_config = TraceConfig(
        frequency_hz=config.frequency_hz,
        rays=config.rays,
        local_cells=config.local_cells,
        exit_bands=config.exit_bands,
        max_bounces=config.max_bounces,
        roulette_start=config.max_bounces + 1,
        ray_epsilon_m=config.ray_epsilon_m,
        seed=config.seed,
        batch=config.rays,
    )
    maximum_class = int(face_class.max(initial=0))
    permittivity = np.full(
        maximum_class + 1,
        complex(config.permittivity_real, config.permittivity_imag),
        dtype=np.complex128,
    )
    rms_height = np.full(maximum_class + 1, config.rms_height_m, dtype=np.float64)
    tracer = SbrTracer(geometry, face_class, permittivity, rms_height, trace_config)
    result, trace_first = _timed(lambda: tracer.trace(np.asarray(config.origin), MODEL_CATALOGUE, seed=config.seed))
    trace_warm: list[float] = []
    for _ in range(config.repeats):
        result, seconds = _timed(lambda: tracer.trace(np.asarray(config.origin), MODEL_CATALOGUE, seed=config.seed))
        trace_warm.append(seconds)

    arrays: dict[str, np.ndarray] = {
        "hit": np.asarray(hit, dtype=bool),
        "face": np.asarray(face, dtype=np.int64),
        "material": material,
        "distance": np.asarray(distance, dtype=np.float64),
        "normal": np.asarray(normal, dtype=np.float64),
        "exit_profile": np.asarray(result.exit_profile, dtype=np.float64),
        "local_grid": np.asarray(result.local_grid, dtype=np.float64),
    }
    for name, rho in result.rho.items():
        arrays[f"rho__{name}"] = np.asarray(rho, dtype=np.float64)
    for name, value in result.susceptibility.items():
        arrays[f"chi__{name}"] = np.asarray(value, dtype=np.float64)
    for name, value in result.susceptibility_direct.items():
        arrays[f"chi_direct__{name}"] = np.asarray(value, dtype=np.float64)
    for name, value in result.scalars().items():
        arrays[f"scalar__{name}"] = np.asarray(value, dtype=np.float64)
    legacy_array_hashes = {name: _sha256_array(array) for name, array in arrays.items()}

    device_summary: dict[str, Any] | None = None
    if variant.startswith(("llvm_", "cuda_")):
        from .device_kernel import DeviceSbrKernel

        device = DeviceSbrKernel(geometry, face_class, permittivity, rms_height, trace_config)
        records, device_first = _timed(
            lambda: device.trace_escape_records(np.asarray(config.origin), rays=config.rays, seed=config.seed)
        )
        device_warm: list[float] = []
        for _ in range(config.repeats):
            records, seconds = _timed(
                lambda: device.trace_escape_records(np.asarray(config.origin), rays=config.rays, seed=config.seed)
            )
            device_warm.append(seconds)
        if records.ray_start != 0 or records.rays != config.rays:
            raise RuntimeError(
                f"device records cover ray_start={records.ray_start}, rays={records.rays}; expected 0, {config.rays}"
            )
        if records.all_launch_direction.shape != (config.rays, 3):
            raise RuntimeError(
                f"device all-launch array has shape {records.all_launch_direction.shape}, expected {(config.rays, 3)}"
            )
        device_arrays = {
            "device__ray_index": records.ray_index,
            "device__all_launch_direction": records.all_launch_direction,
            "device__escaped_launch_direction": records.escaped_launch_direction,
            "device__exit_direction": records.exit_direction,
            "device__throughput": records.throughput,
            "device__path_length": records.path_length,
            "device__last_vertex": records.last_vertex,
            "device__bounces": records.bounces,
            "device__truncated_throughput_terms": records.truncated_throughput_terms,
        }
        arrays.update(device_arrays)
        device_summary = {
            "status": "prototype_device_resident_escape_records",
            "rng": {
                "algorithm": "Mitsuba sample_tea_float32 keyed by seed, ray index, bounce, and dimension",
                "seed": config.seed,
                "ray_start": records.ray_start,
                "all_launch_direction_sha256": _sha256_array(records.all_launch_direction),
                "escaped_launch_direction_sha256": _sha256_array(records.escaped_launch_direction),
            },
            "ray_start": records.ray_start,
            "rays": records.rays,
            "escaped": records.escaped,
            "truncated": records.truncated,
            "truncated_throughput": records.truncated_throughput,
            "roulette_killed": records.roulette_killed,
            "timing": _timing(
                device_first,
                device_warm,
                first_label="first device-resident trace after geometry construction",
            ),
            "array_sha256": {name: _sha256_array(array) for name, array in device_arrays.items()},
        }
    np.savez(artifact_path, **arrays)

    return {
        "provenance": provenance,
        "artifact": str(artifact_path.resolve()),
        "artifact_sha256": _sha256_file(artifact_path),
        "fixed_ray_sha256": ray_hashes,
        "intersection": {
            "hits": int(np.count_nonzero(hit)),
            "timing": {
                "load_seconds": load_seconds,
                **_timing(raw_cold, raw_warm, first_label="first raw intersection in a fresh variant process"),
            },
        },
        "legacy_hybrid_sbr": {
            "status": "NumPy transport loop with Mitsuba intersections; not device-resident SBR",
            "launch_rng": {
                "algorithm": "NumPy PCG64 through sample_sphere",
                "seed": config.seed,
                "directions_sha256": ray_hashes["directions"],
            },
            "timing": _timing(
                trace_first,
                trace_warm,
                first_label="first full hybrid trace after raw intersection warm-up",
            ),
            "susceptibility": {name: float(value) for name, value in result.susceptibility.items()},
            "susceptibility_direct": {name: float(value) for name, value in result.susceptibility_direct.items()},
            "scalars": result.scalars(),
            "array_sha256": legacy_array_hashes,
        },
        "device_sbr": device_summary,
    }


def run_harness(config: ParityConfig) -> pathlib.Path:
    """Run all variants in subprocesses and write the combined JSON report."""
    config.validate()
    output = pathlib.Path(config.output).resolve()
    config = replace(
        config,
        mesh=str(pathlib.Path(config.mesh).resolve()),
        output=str(output),
        face_class=str(pathlib.Path(config.face_class).resolve()) if config.face_class is not None else None,
    )
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise FileExistsError(f"refusing to use nonempty output path: {output}")
    report_path = output / "report.json"
    output.mkdir(parents=True, exist_ok=True)
    origins, directions = fixed_rays(config)
    ray_hashes = {"origins": _sha256_array(origins), "directions": _sha256_array(directions)}
    rays_path = output / "fixed_rays.npz"
    np.savez(rays_path, origins=origins, directions=directions)
    config_path = output / "config.json"
    config_path.write_text(json.dumps(asdict(config), indent=2, sort_keys=True) + "\n")
    variants, artifacts, errors = _run_workers(config, output, config_path, rays_path, ray_hashes)
    comparisons = _compare_variants(config, variants, artifacts, errors)
    consistency = _cross_worker_consistency(variants, ray_hashes)
    acceptance = _acceptance(config, comparisons, consistency, errors)
    report = {
        "schema_version": 2,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": asdict(config),
        "fixed_rays": {
            "path": str(rays_path),
            "file_sha256": _sha256_file(rays_path),
            "origins_sha256": ray_hashes["origins"],
            "directions_sha256": ray_hashes["directions"],
        },
        "variants": variants,
        "comparisons": comparisons,
        "cross_worker_consistency": consistency,
        "worker_errors": errors,
        "acceptance": acceptance,
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report_path
