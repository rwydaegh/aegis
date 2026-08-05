"""High-resolution angular and body-coupling convergence study.

The study freezes the accepted Korenmarkt production run as its scene and walk
identity. It then varies only the angular cell count, ray count, and random
seed. Each run stores its raw rooftop spectrum before aggregate metrics are
computed, so a later plotting or convergence rule cannot change the trace.
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import math
import os
import pathlib
import platform
import subprocess
import time
from dataclasses import dataclass
from importlib import metadata
from typing import Any

import numpy as np

from semantic_twin.illumination import ROOFTOP, fibonacci_sphere

PRODUCTION_CELLS = (512, 1024, 2048, 4096)
PRODUCTION_RAYS = (200_000, 400_000, 800_000, 1_600_000)
PRODUCTION_INITIAL_SEEDS = (7, 8, 9, 10)
PRODUCTION_EXTENDED_SEEDS = tuple(range(7, 15))
PRODUCTION_REFERENCE_CELLS = 4096
PRODUCTION_REFERENCE_RAYS = 1_600_000


@dataclass(frozen=True, order=True)
class AngularRunSpec:
    """One unique trace in the two convergence sweeps."""

    cells: int
    rays: int
    seed: int

    @property
    def name(self) -> str:
        return f"cells{self.cells}_rays{self.rays}_seed{self.seed}"


@dataclass(frozen=True)
class FixedSector:
    """A world-fixed azimuth and elevation rectangle."""

    name: str
    azimuth_deg: tuple[float, float]
    elevation_deg: tuple[float, float]

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> FixedSector:
        azimuth = tuple(float(value) for value in document["azimuth_deg"])
        elevation = tuple(float(value) for value in document["elevation_deg"])
        if len(azimuth) != 2 or len(elevation) != 2:
            raise ValueError("sector angle ranges must each contain two values")
        if not -90.0 <= elevation[0] < elevation[1] <= 90.0:
            raise ValueError(f"invalid elevation range {elevation}")
        if not all(0.0 <= value <= 360.0 for value in azimuth):
            raise ValueError(f"invalid azimuth range {azimuth}")
        return cls(str(document["name"]), azimuth, elevation)


@dataclass(frozen=True)
class AngularConvergenceConfig:
    """Validated file-backed definition of the angular sweep."""

    root: pathlib.Path
    output_dir: pathlib.Path
    reference_manifest: pathlib.Path
    reference_locations: pathlib.Path
    reference_spectra: pathlib.Path
    cells: tuple[int, ...]
    cells_rays: int
    rays: tuple[int, ...]
    rays_cells: int
    initial_seeds: tuple[int, ...]
    extended_seeds: tuple[int, ...]
    fixed_sectors: tuple[FixedSector, ...]
    body_chunk_cells: int
    contract: str
    config_path: pathlib.Path
    config_sha256: str

    @classmethod
    def load(cls, path: str | pathlib.Path) -> AngularConvergenceConfig:
        config_path = pathlib.Path(path).resolve()
        document = json.loads(config_path.read_text())
        root_value = pathlib.Path(document.get("root", ".."))
        root = (config_path.parent / root_value).resolve()

        def resolve(value: str) -> pathlib.Path:
            candidate = pathlib.Path(value)
            return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()

        reference = document["reference"]
        cell_sweep = document["sweeps"]["cells"]
        ray_sweep = document["sweeps"]["rays"]
        seeds = document["seeds"]
        config = cls(
            root=root,
            output_dir=resolve(document["output_dir"]),
            reference_manifest=resolve(reference["manifest"]),
            reference_locations=resolve(reference["locations"]),
            reference_spectra=resolve(reference["spectra"]),
            cells=tuple(int(value) for value in cell_sweep["values"]),
            cells_rays=int(cell_sweep["rays"]),
            rays=tuple(int(value) for value in ray_sweep["values"]),
            rays_cells=int(ray_sweep["cells"]),
            initial_seeds=tuple(int(value) for value in seeds["initial"]),
            extended_seeds=tuple(int(value) for value in seeds["extended"]),
            fixed_sectors=tuple(FixedSector.from_dict(value) for value in document["fixed_sectors"]),
            body_chunk_cells=int(document["body_chunk_cells"]),
            contract=str(document.get("contract", "synthetic")),
            config_path=config_path,
            config_sha256=file_sha256(config_path),
        )
        config.validate()
        return config

    def validate(self) -> None:
        """Reject ambiguous or duplicated sweep definitions."""
        if not self.cells or not self.rays or not self.initial_seeds:
            raise ValueError("cell, ray, and seed sweeps must be nonempty")
        for name, values in (
            ("cells", self.cells),
            ("rays", self.rays),
            ("initial seeds", self.initial_seeds),
            ("extended seeds", self.extended_seeds),
        ):
            if any(value < 1 for value in values):
                raise ValueError(f"{name} must be positive")
            if len(set(values)) != len(values):
                raise ValueError(f"{name} contains duplicates")
        if not set(self.initial_seeds).issubset(self.extended_seeds):
            raise ValueError("extended seeds must contain every initial seed")
        if self.cells_rays < 1 or self.rays_cells < 1 or self.body_chunk_cells < 1:
            raise ValueError("fixed sweep values and body_chunk_cells must be positive")
        if self.rays_cells not in self.cells or self.cells_rays not in self.rays:
            raise ValueError("the cell and ray sweeps must both contain their shared reference run")
        sector_names = [sector.name for sector in self.fixed_sectors]
        if len(set(sector_names)) != len(sector_names):
            raise ValueError("fixed sector names must be unique")
        if self.contract == "korenmarkt_angular_4096_v1":
            self.validate_production_contract()

    def validate_production_contract(self) -> None:
        """Pin the requested 4096-cell experiment exactly."""
        expected = {
            "cells": PRODUCTION_CELLS,
            "cells_rays": PRODUCTION_REFERENCE_RAYS,
            "rays": PRODUCTION_RAYS,
            "rays_cells": PRODUCTION_REFERENCE_CELLS,
            "initial_seeds": PRODUCTION_INITIAL_SEEDS,
            "extended_seeds": PRODUCTION_EXTENDED_SEEDS,
        }
        actual = {name: getattr(self, name) for name in expected}
        if actual != expected:
            raise ValueError(f"production angular convergence contract changed: {actual} != {expected}")

    def specs(self, *, extended: bool = False) -> tuple[AngularRunSpec, ...]:
        seeds = self.extended_seeds if extended else self.initial_seeds
        specs = {AngularRunSpec(cells, self.cells_rays, seed) for seed in seeds for cells in self.cells}
        specs.update(AngularRunSpec(self.rays_cells, rays, seed) for seed in seeds for rays in self.rays)
        return tuple(sorted(specs))

    @property
    def reference_spec(self) -> tuple[int, int]:
        """Cell and ray counts shared by both convergence sweeps."""
        return self.rays_cells, self.cells_rays

    def scientific_config(self) -> dict[str, Any]:
        """Return every file-backed value that can change the experiment."""
        return {
            "contract": self.contract,
            "config_path": str(self.config_path),
            "config_sha256": self.config_sha256,
            "output_dir": str(self.output_dir),
            "reference_manifest": str(self.reference_manifest),
            "reference_locations": str(self.reference_locations),
            "reference_spectra": str(self.reference_spectra),
            "cells": list(self.cells),
            "cells_rays": self.cells_rays,
            "rays": list(self.rays),
            "rays_cells": self.rays_cells,
            "initial_seeds": list(self.initial_seeds),
            "extended_seeds": list(self.extended_seeds),
            "fixed_sectors": [dataclasses.asdict(sector) for sector in self.fixed_sectors],
            "body_chunk_cells": self.body_chunk_cells,
        }


@dataclass(frozen=True)
class FrozenStandpoints:
    """Exact observation arrays recovered from the accepted v2 result rows."""

    index: np.ndarray
    points: np.ndarray
    ground_z_m: np.ndarray
    point_kind: tuple[str, ...]
    sha256: str


@dataclass(frozen=True)
class ReferenceIdentity:
    """Files and numerical arrays that define the production scene."""

    manifest: dict[str, Any]
    standpoints: FrozenStandpoints
    files: dict[str, dict[str, Any]]
    mesh_sha256: str
    body_sha256: str
    material_evidence_role: str
    material_evidence_sha256: str | None
    surface_binding_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "reference_files": self.files,
            "mesh_sha256": self.mesh_sha256,
            "body_sha256": self.body_sha256,
            "material_evidence_role": self.material_evidence_role,
            "material_evidence_sha256": self.material_evidence_sha256,
            "surface_binding_sha256": self.surface_binding_sha256,
            "standpoint_array_sha256": self.standpoints.sha256,
            "standpoints": int(self.standpoints.index.size),
            "reference_run_digest": self.manifest["run_digest"],
        }


def load_reference(config: AngularConvergenceConfig) -> ReferenceIdentity:
    """Load and hash the accepted manifest, rows, spectra, scene, and body."""
    reference_paths = {
        "manifest": config.reference_manifest,
        "locations": config.reference_locations,
        "spectra": config.reference_spectra,
    }
    missing = [str(path) for path in reference_paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing reference files: {', '.join(missing)}")
    content = {name: path.read_bytes() for name, path in reference_paths.items()}
    manifest = json.loads(content["manifest"])
    if not isinstance(manifest, dict) or not _same_output_generation_snapshot(
        manifest,
        reference_paths,
        content,
    ):
        raise ValueError("reference exposure files are not one sealed output generation")
    rows = [json.loads(line) for line in content["locations"].decode().splitlines()]
    if len(rows) != manifest["locations_traced"]:
        raise ValueError("reference row count does not match its manifest")
    if not rows:
        raise ValueError("reference run contains no standpoints")
    index = np.asarray([row["index"] for row in rows], dtype=np.int64)
    points = np.asarray([[row[axis] for axis in ("x", "y", "z")] for row in rows], dtype=np.float64)
    ground = np.asarray([row["ground_z_m"] for row in rows], dtype=np.float64)
    point_kind = tuple(str(row.get("point_kind", "")) for row in rows)
    standpoint_sha = _joined_array_sha256(index, points, ground)
    standpoints = FrozenStandpoints(index, points, ground, point_kind, standpoint_sha)

    with np.load(io.BytesIO(content["spectra"])) as spectra:
        spectra_index = np.array(spectra["index"], dtype=np.int64, copy=True)
        rho = np.array(spectra["rho_rooftop"], dtype=np.float64, copy=True)
        grid = np.array(spectra["local_grid"], dtype=np.float64, copy=True)
        solid_angle = float(spectra["solid_angle"])
    expected_cells = int(manifest["run"]["local_cells"])
    if not np.array_equal(spectra_index, index):
        raise ValueError("reference spectra and location rows use different standpoint indices")
    if rho.shape != (index.size, expected_cells) or grid.shape != (expected_cells, 3):
        raise ValueError("reference spectra arrays do not match the accepted run dimensions")
    if not _valid_spectrum_arrays(rho, grid, solid_angle, expected_cells):
        raise ValueError("reference spectra contain invalid values or angular geometry")

    mesh = pathlib.Path(manifest["mesh"])
    if not mesh.is_file():
        mesh = config.root / "data" / "geometry" / manifest["site"] / pathlib.Path(manifest["mesh"]).name
    mesh_sha = file_sha256(mesh)
    if mesh_sha != manifest["mesh_sha256"]:
        raise ValueError("production mesh bytes no longer match the accepted v2 manifest")
    body = pathlib.Path(os.environ.get("AEGIS_DATA_DIR", "/home/user/aegis/data")) / "duke.stl"
    evidence_role, material_evidence = _material_evidence_path(config.root, manifest)
    files = {
        name: {"path": str(path), "sha256": hashlib.sha256(content[name]).hexdigest()}
        for name, path in reference_paths.items()
    }
    return ReferenceIdentity(
        manifest=manifest,
        standpoints=standpoints,
        files=files,
        mesh_sha256=mesh_sha,
        body_sha256=file_sha256(body),
        material_evidence_role=evidence_role,
        material_evidence_sha256=file_sha256(material_evidence) if material_evidence is not None else None,
        surface_binding_sha256=canonical_sha256(manifest["surface_binding"]),
    )


def _same_output_generation_snapshot(
    manifest: dict[str, Any],
    paths: dict[str, pathlib.Path],
    content: dict[str, bytes],
) -> bool:
    """Verify one in-memory rows/spectra snapshot against its manifest bytes."""
    generation = manifest.get("output_generation")
    if not isinstance(generation, dict) or generation.get("format_version") != 1:
        return False
    generation_id = generation.get("id")
    if not _valid_hex(generation_id, 32):
        return False
    artifacts = generation.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {"locations", "spectra"}:
        return False
    for name in ("locations", "spectra"):
        record = artifacts[name]
        payload = content[name]
        if (
            not isinstance(record, dict)
            or set(record) != {"path", "sha256", "bytes"}
            or record.get("path") != paths[name].name
            or not _valid_hex(record.get("sha256"), 64)
            or type(record.get("bytes")) is not int
            or record["bytes"] < 0
            or record["bytes"] != len(payload)
            or record["sha256"] != hashlib.sha256(payload).hexdigest()
        ):
            return False
    return True


def _valid_hex(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _material_evidence_path(
    root: pathlib.Path,
    manifest: dict[str, Any],
) -> tuple[str, pathlib.Path | None]:
    """Resolve the file that defines the reference run's material evidence."""
    run = manifest["run"]
    mode = str(run["materials"])
    if mode == "atlas":
        value = run.get("atlas_npz") or manifest.get("semantic_binding", {}).get("atlas_npz")
        role = "joint_surface_atlas"
    elif mode == "walk":
        value = run.get("walk_npz")
        role = "walk_semantics"
    elif mode == "geometric":
        return "geometric_only", None
    else:
        raise ValueError(f"angular convergence does not yet freeze material evidence for mode {mode!r}")
    if not isinstance(value, str) or not value:
        raise ValueError(f"reference material mode {mode!r} does not name its evidence artifact")
    path = pathlib.Path(value)
    path = path if path.is_absolute() else root / path
    if not path.is_file():
        raise FileNotFoundError(f"reference material evidence is missing: {path}")
    return role, path


def spectrum_metrics(
    local_grid: np.ndarray,
    rho: np.ndarray,
    solid_angle: float,
    sectors: tuple[FixedSector, ...],
) -> dict[str, Any]:
    """Reduce one raw spectrum using only world-fixed angular definitions."""
    grid = np.asarray(local_grid, dtype=np.float64)
    values = np.asarray(rho, dtype=np.float64)
    if grid.shape != (values.size, 3):
        raise ValueError("local_grid and rho shapes disagree")
    if not np.all(np.isfinite(grid)) or np.any(np.linalg.norm(grid, axis=1) <= 0.0):
        raise ValueError("local_grid must contain finite nonzero directions")
    if np.any(values < 0.0) or not np.all(np.isfinite(values)):
        raise ValueError("rho must be finite and nonnegative")
    if not np.isfinite(solid_angle) or solid_angle <= 0.0:
        raise ValueError("solid_angle must be positive and finite")
    mass = values * float(solid_angle)
    chi = float(np.sum(mass, dtype=np.float64))
    top_count = max(1, math.ceil(values.size * 0.01))
    top_mass = float(np.sum(np.partition(mass, -top_count)[-top_count:], dtype=np.float64))
    peak_cell_mass = float(np.max(mass))
    peak_cell = int(np.argmax(values))
    peak = grid[peak_cell] / np.linalg.norm(grid[peak_cell])
    return {
        "chi": chi,
        "peak_rho_per_sr": float(np.max(values)),
        "peak_cell_mass": peak_cell_mass,
        "peak_cell_share": peak_cell_mass / chi if chi > 0.0 else 0.0,
        "peak_direction": {
            "cell": peak_cell,
            "unit_vector": [float(value) for value in peak],
            "azimuth_deg": float(np.mod(np.degrees(np.arctan2(peak[1], peak[0])), 360.0)),
            "elevation_deg": float(np.degrees(np.arcsin(np.clip(peak[2], -1.0, 1.0)))),
        },
        "top_1_percent_mass": top_mass,
        "top_1_percent_share": top_mass / chi if chi > 0.0 else 0.0,
        "fixed_sector_mass": fixed_sector_mass(grid, mass, sectors),
    }


def angular_distance_deg(first: np.ndarray, second: np.ndarray) -> float:
    """Great-circle distance between two nonzero direction vectors."""
    left = np.asarray(first, dtype=np.float64)
    right = np.asarray(second, dtype=np.float64)
    if left.shape != (3,) or right.shape != (3,):
        raise ValueError("directions must each have shape (3,)")
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        raise ValueError("directions must be nonzero")
    cosine = float(np.dot(left, right) / (left_norm * right_norm))
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def fixed_sector_mass(
    local_grid: np.ndarray,
    cell_mass: np.ndarray,
    sectors: tuple[FixedSector, ...],
) -> dict[str, float]:
    """Integrate cell masses inside each declared world-fixed sector."""
    azimuth = np.mod(np.degrees(np.arctan2(local_grid[:, 1], local_grid[:, 0])), 360.0)
    elevation = np.degrees(np.arcsin(np.clip(local_grid[:, 2], -1.0, 1.0)))
    out: dict[str, float] = {}
    for sector in sectors:
        az0, az1 = sector.azimuth_deg
        if az0 == az1:
            azimuth_mask = np.ones(azimuth.shape, dtype=bool)
        elif az0 < az1:
            azimuth_mask = (azimuth >= az0) & (azimuth < az1)
        else:
            azimuth_mask = (azimuth >= az0) | (azimuth < az1)
        el0, el1 = sector.elevation_deg
        elevation_mask = (elevation >= el0) & (elevation < el1)
        if el1 == 90.0:
            elevation_mask |= elevation == 90.0
        out[sector.name] = float(np.sum(cell_mass[azimuth_mask & elevation_mask], dtype=np.float64))
    return out


def run_study(
    config: AngularConvergenceConfig,
    *,
    extended_seeds: bool = False,
    dry_run: bool = False,
    aggregate_only: bool = False,
) -> pathlib.Path:
    """Run or resume every configured trace and write aggregate convergence."""
    reference = load_reference(config)
    code = code_provenance(config.root)
    specs = config.specs(extended=extended_seeds)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    mode_name = "extended_seeds" if extended_seeds else "initial_seeds"
    analysis_dir = config.output_dir / mode_name
    analysis_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "schema": "angular-convergence-plan-v2",
        "contract": config.contract,
        "scientific_config": config.scientific_config(),
        "reference": reference.as_dict(),
        "code": code,
        "extended_seeds": extended_seeds,
        "seed_mode": mode_name,
        "analysis_dir": str(analysis_dir),
        "shared_raw_run_dir": str(config.output_dir / "runs"),
        "runs": [dataclasses.asdict(spec) for spec in specs],
        "aggregation": "arithmetic mean of rho in linear power units over independent seeds",
        "smoothing": "none",
    }
    _write_json_atomic(analysis_dir / "plan.json", plan)
    if dry_run:
        return analysis_dir / "plan.json"

    from semantic_twin.exposure import study

    coupler = study.BodyCoupler(
        study.PHANTOM,
        float(reference.manifest["run"]["frequency_hz"]),
        body_mass_kg=study.PHANTOM_MASS_KG,
    )
    if not aggregate_only:
        shared = _prepare_shared_scene(config, reference)
        for spec in specs:
            run_dir = config.output_dir / "runs" / spec.name
            identity = run_identity(config, reference, code, spec)
            if reusable_run(run_dir, identity, spec, reference.standpoints):
                print(f"[reuse] {spec.name}", flush=True)
                continue
            print(f"[trace] {spec.name}", flush=True)
            prepared = _prepare_trace(spec, shared)
            _trace_one(config, reference, code, spec, prepared, coupler, run_dir, identity)

    aggregate = aggregate_runs(config, reference, code, specs, coupler, analysis_dir=analysis_dir)
    path = analysis_dir / "aggregate.json"
    _write_json_atomic(path, aggregate)
    return path


def _prepare_shared_scene(
    config: AngularConvergenceConfig,
    reference: ReferenceIdentity,
) -> tuple[Any, Any, Any, Any]:
    """Build and verify the production geometry and materials once."""
    from semantic_twin.exposure import study
    from semantic_twin.exposure.execution import (
        LegacyReplay,
        _array_sha256,
        _bind_materials,
        _prepare_scene,
    )
    from semantic_twin.runconfig import RunConfig

    base = RunConfig.from_dict(reference.manifest["run"])
    evidence_paths: dict[str, str | None] = {}
    for name in ("walk_npz", "atlas_npz"):
        value = getattr(base, name)
        if value:
            path = pathlib.Path(value)
            evidence_paths[name] = str(path if path.is_absolute() else config.root / path)
    base = dataclasses.replace(
        base,
        models=("rooftop",),
        variant="cuda_ad_rgb",
        transport_kernel="drjit",
        **evidence_paths,
    )
    environment = study._execution_environment()
    scene = _prepare_scene(
        base,
        LegacyReplay(ground_datum_m=float(reference.manifest["ground_datum_m"])),
        environment,
    )
    if scene.mesh.resolve() != pathlib.Path(reference.manifest["mesh"]).resolve():
        raise RuntimeError("mesh resolver selected a different file from the v2 production run")
    if file_sha256(scene.mesh) != reference.mesh_sha256:
        raise RuntimeError("prepared mesh bytes differ from the v2 production run")
    material = _bind_materials(base, scene, environment)
    expected_face_hash = reference.manifest["semantic_binding"]["face_class_sha256"]
    if _array_sha256(material.face_class) != expected_face_hash:
        raise RuntimeError("prepared material face classes differ from the v2 production run")
    if canonical_sha256(material.table.as_dict()) != reference.surface_binding_sha256:
        raise RuntimeError("prepared surface material table differs from the v2 production run")
    return scene, material, base, environment


def _prepare_trace(
    spec: AngularRunSpec,
    shared: tuple[Any, Any, Any, Any],
) -> tuple[Any, Any, Any, Any]:
    """Create one device tracer while reusing the verified scene."""
    from semantic_twin.exposure.execution import _trace_config
    from semantic_twin.transport.device_tracer import DeviceEscapeTracer

    scene, material, base, environment = shared
    run = dataclasses.replace(
        base,
        rays=spec.rays,
        local_cells=spec.cells,
        seed=spec.seed,
        tag=f"angular_convergence_{spec.name}",
    )
    trace_config = _trace_config(run, environment)
    tracer_options = {} if material.atlas_material is None else {"atlas_material": material.atlas_material}
    tracer = DeviceEscapeTracer(
        scene.geometry,
        material.face_class,
        material.table.permittivity,
        material.table.rms_height_m,
        trace_config,
        **tracer_options,
    )
    return scene, material, tracer, run


def _trace_one(
    config: AngularConvergenceConfig,
    reference: ReferenceIdentity,
    code: dict[str, Any],
    spec: AngularRunSpec,
    prepared: tuple[Any, Any, Any, Any],
    coupler: Any,
    run_dir: pathlib.Path,
    identity: str,
) -> None:
    """Trace all frozen standpoints, then couple their spectra in chunks."""
    from semantic_twin.exposure.execution import _array_sha256, _transport_provenance

    scene, material, tracer, run = prepared
    run_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    standpoints = reference.standpoints
    local_grid = np.asarray(tracer.local_grid, dtype=np.float64)
    solid_angle = 4.0 * np.pi / spec.cells
    completed, saved_rho, scalar_rows = _load_trace_checkpoint(
        run_dir,
        identity,
        spec,
        standpoints,
        local_grid,
        solid_angle,
    )
    manifest = {
        "schema": "angular-convergence-run-v2",
        "complete": False,
        "identity_sha256": identity,
        "spec": dataclasses.asdict(spec),
        "reference": reference.as_dict(),
        "code": code,
        "trace_config": tracer.config.as_dict(),
        "transport": _transport_provenance(run),
        "illumination_model": "rooftop",
        "mesh": str(scene.mesh),
        "mesh_sha256": file_sha256(scene.mesh),
        "face_class_sha256": _array_sha256(material.face_class),
        "surface_binding_sha256": canonical_sha256(material.table.as_dict()),
        "body_sha256": reference.body_sha256,
        "standpoint_array_sha256": reference.standpoints.sha256,
        "seed_rule": "run seed + 1000 * frozen production standpoint index",
        "storage": "raw rooftop rho retained for every frozen standpoint",
        "aggregation": "linear-power rho; no smoothing",
        "checkpoint_interval": "after every standpoint",
        "resumed_locations": completed,
    }
    _write_json_atomic(run_dir / "manifest.json", manifest)

    rho = np.zeros((standpoints.index.size, spec.cells), dtype=np.float64)
    rho[:completed] = saved_rho
    for row in range(completed, standpoints.index.size):
        index = standpoints.index[row]
        result = tracer.trace(
            standpoints.points[row],
            {"rooftop": ROOFTOP},
            ground_z_m=float(standpoints.ground_z_m[row]),
            seed=spec.seed + 1000 * int(index),
        )
        rho[row] = result.rho["rooftop"]
        if not np.array_equal(local_grid, result.local_grid) or solid_angle != result.local_solid_angle:
            raise RuntimeError("angular grid changed between standpoints in one run")
        scalar_rows.append(
            {
                "index": int(index),
                "seconds": float(result.seconds),
                **result.scalars(),
            }
        )
        spectra_path = run_dir / "spectra.npz"
        _write_spectra(
            spectra_path,
            standpoints,
            rho[: row + 1],
            local_grid,
            solid_angle,
        )
        _write_json_atomic(
            run_dir / "checkpoint.json",
            {
                "schema": "angular-convergence-checkpoint-v2",
                "identity_sha256": identity,
                "complete_locations": row + 1,
                "standpoint_index": [int(value) for value in standpoints.index[: row + 1]],
                "scalar_rows": scalar_rows,
                "spectra_file_sha256": file_sha256(spectra_path),
                "rho_prefix_sha256": _joined_array_sha256(rho[: row + 1]),
                "local_grid_sha256": _joined_array_sha256(local_grid),
            },
        )
        print(
            f"  [{row + 1}/{standpoints.index.size}] index={index} "
            f"chi={result.susceptibility['rooftop']:.6g} ({result.seconds:.1f} s)",
            flush=True,
        )
    body = coupler.couple_many(
        local_grid,
        rho,
        solid_angle,
        float(reference.manifest["reference_s0_w_m2"]),
        chunk_cells=config.body_chunk_cells,
    )
    metrics = []
    for row, index in enumerate(standpoints.index):
        angular = spectrum_metrics(local_grid, rho[row], solid_angle, config.fixed_sectors)
        metrics.append(
            {
                "index": int(index),
                "point_kind": standpoints.point_kind[row],
                **angular,
                "body": body[row].as_dict(),
                "trace": scalar_rows[row],
            }
        )
    metrics_document = {
        "schema": "angular-convergence-metrics-v2",
        "identity_sha256": identity,
        "rows": metrics,
    }
    metrics_path = run_dir / "metrics.json"
    spectra_path = run_dir / "spectra.npz"
    _write_json_atomic(metrics_path, metrics_document)
    manifest.update(
        {
            "complete": True,
            "wall_seconds": time.perf_counter() - started,
            "local_grid_sha256": _array_sha256(local_grid),
            "rho_sha256": _array_sha256(rho),
            "spectra_file_sha256": file_sha256(spectra_path),
            "metrics_file_sha256": file_sha256(metrics_path),
            "solid_angle_sr": solid_angle,
            "locations_traced": int(standpoints.index.size),
            "raw_seed_preserved": True,
        }
    )
    _write_json_atomic(run_dir / "manifest.json", manifest)
    _write_json_atomic(
        run_dir / "checkpoint.json",
        {
            "schema": "angular-convergence-checkpoint-v2",
            "identity_sha256": identity,
            "complete_locations": int(standpoints.index.size),
            "standpoint_index": [int(value) for value in standpoints.index],
            "scalar_rows": scalar_rows,
            "spectra_file_sha256": file_sha256(spectra_path),
            "rho_prefix_sha256": _joined_array_sha256(rho),
            "local_grid_sha256": _joined_array_sha256(local_grid),
            "run_complete": True,
        },
    )


def _load_trace_checkpoint(
    run_dir: pathlib.Path,
    identity: str,
    spec: AngularRunSpec,
    standpoints: FrozenStandpoints,
    local_grid: np.ndarray,
    solid_angle: float,
) -> tuple[int, np.ndarray, list[dict[str, Any]]]:
    """Load a proven standpoint prefix, or return an empty checkpoint."""
    manifest_path = run_dir / "manifest.json"
    checkpoint_path = run_dir / "checkpoint.json"
    spectra_path = run_dir / "spectra.npz"
    empty = np.empty((0, spec.cells), dtype=np.float64)
    if not all(path.is_file() for path in (manifest_path, checkpoint_path, spectra_path)):
        return 0, empty, []
    try:
        manifest = json.loads(manifest_path.read_text())
        checkpoint = json.loads(checkpoint_path.read_text())
        with np.load(spectra_path) as spectra:
            index = np.asarray(spectra["index"], dtype=np.int64)
            points = np.asarray(spectra["point"], dtype=np.float64)
            ground = np.asarray(spectra["ground_z_m"], dtype=np.float64)
            rho = np.asarray(spectra["rho_rooftop"], dtype=np.float64)
            grid = np.asarray(spectra["local_grid"], dtype=np.float64)
            saved_solid_angle = float(spectra["solid_angle"])
        completed = int(checkpoint["complete_locations"])
        scalar_rows = list(checkpoint["scalar_rows"])
    except (KeyError, OSError, TypeError, ValueError):
        return 0, empty, []
    saved_file_hash = checkpoint.get("spectra_file_sha256")
    saved_prefix_hash = checkpoint.get("rho_prefix_sha256")
    saved_grid_hash = checkpoint.get("local_grid_sha256")
    current_file_hash = file_sha256(spectra_path)
    checkpoint_hashes_present = all(
        value is not None for value in (saved_file_hash, saved_prefix_hash, saved_grid_hash)
    )
    checkpoint_hashes_valid = saved_file_hash == current_file_hash or (
        index.size > completed
        and saved_prefix_hash == _joined_array_sha256(rho[:completed])
        and saved_grid_hash == _joined_array_sha256(grid)
    )
    scalar_indices = (
        [row.get("index") for row in scalar_rows] if all(isinstance(row, dict) for row in scalar_rows) else None
    )
    valid = all(
        (
            manifest.get("schema") == "angular-convergence-run-v2",
            checkpoint.get("schema") == "angular-convergence-checkpoint-v2",
            manifest.get("identity_sha256") == identity,
            checkpoint.get("identity_sha256") == identity,
            0 <= completed <= standpoints.index.size,
            completed <= index.size <= standpoints.index.size,
            points.shape == (index.size, 3),
            ground.shape == (index.size,),
            rho.shape == (index.size, spec.cells),
            len(scalar_rows) == completed,
            np.array_equal(index, standpoints.index[: index.size]),
            np.array_equal(points, standpoints.points[: index.size]),
            np.array_equal(ground, standpoints.ground_z_m[: index.size]),
            np.array_equal(grid, local_grid),
            saved_solid_angle == solid_angle,
            np.all(np.isfinite(rho)),
            np.all(rho >= 0.0),
            scalar_indices == [int(value) for value in standpoints.index[:completed]],
            checkpoint.get(
                "standpoint_index",
                [int(value) for value in standpoints.index[:completed]],
            )
            == [int(value) for value in standpoints.index[:completed]],
            saved_prefix_hash == _joined_array_sha256(rho[:completed]),
            saved_grid_hash == _joined_array_sha256(grid),
            checkpoint_hashes_present,
            checkpoint_hashes_valid,
        )
    )
    return (completed, rho[:completed], scalar_rows) if valid else (0, empty, [])


def run_identity(
    config: AngularConvergenceConfig,
    reference: ReferenceIdentity,
    code: dict[str, Any],
    spec: AngularRunSpec,
) -> str:
    """Hash everything allowed to decide one run's numbers."""
    return canonical_sha256(
        {
            "contract": config.contract,
            "scientific_config": config.scientific_config(),
            "spec": dataclasses.asdict(spec),
            "reference": reference.as_dict(),
            "code": {
                "git_sha": code["git_sha"],
                "source_tree_sha256": code["source_tree_sha256"],
                "runtime_versions": code["runtime_versions"],
            },
            "fixed_sectors": [dataclasses.asdict(sector) for sector in config.fixed_sectors],
            "body_chunk_cells": config.body_chunk_cells,
            "variant": "cuda_ad_rgb",
            "transport_kernel": "drjit",
            "models": ["rooftop"],
        }
    )


def reusable_run(
    run_dir: pathlib.Path,
    identity: str,
    spec: AngularRunSpec,
    standpoints: FrozenStandpoints,
) -> bool:
    """Prove a completed run has matched spectra, metrics, and identities."""
    manifest_path = run_dir / "manifest.json"
    spectra_path = run_dir / "spectra.npz"
    metrics_path = run_dir / "metrics.json"
    if not manifest_path.is_file() or not spectra_path.is_file() or not metrics_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text())
        metrics = json.loads(metrics_path.read_text())
        with np.load(spectra_path) as spectra:
            index = np.asarray(spectra["index"], dtype=np.int64)
            points = np.asarray(spectra["point"], dtype=np.float64)
            ground = np.asarray(spectra["ground_z_m"], dtype=np.float64)
            rho = np.asarray(spectra["rho_rooftop"], dtype=np.float64)
            grid = np.asarray(spectra["local_grid"], dtype=np.float64)
            solid_angle = float(spectra["solid_angle"])
    except (KeyError, OSError, TypeError, ValueError):
        return False
    rows = metrics.get("rows")
    if not isinstance(rows, list) or not rows:
        return False
    expected_index = standpoints.index
    row_index = [row.get("index") for row in rows if isinstance(row, dict)]
    row_kind = [row.get("point_kind") for row in rows if isinstance(row, dict)]
    trace_index = [
        row.get("trace", {}).get("index")
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("trace"), dict)
    ]
    try:
        flattened = [_flatten_metrics(row) for row in rows]
        metric_values = np.asarray(
            [[value for _, value in sorted(row.items())] for row in flattened],
            dtype=np.float64,
        )
        metric_names = [tuple(sorted(row)) for row in flattened]
        peak_cells = np.asarray([row["peak_direction"]["cell"] for row in rows], dtype=np.int64)
        peak_vectors = np.asarray(
            [row["peak_direction"]["unit_vector"] for row in rows],
            dtype=np.float64,
        )
    except (KeyError, TypeError, ValueError):
        return False
    file_hashes_present = all(name in manifest for name in ("spectra_file_sha256", "metrics_file_sha256"))
    file_hashes_valid = all(
        (
            "spectra_file_sha256" not in manifest or manifest["spectra_file_sha256"] == file_sha256(spectra_path),
            "metrics_file_sha256" not in manifest or manifest["metrics_file_sha256"] == file_sha256(metrics_path),
        )
    )
    return all(
        (
            manifest.get("complete") is True,
            manifest.get("schema") == "angular-convergence-run-v2",
            manifest.get("identity_sha256") == identity,
            metrics.get("identity_sha256") == identity,
            metrics.get("schema") == "angular-convergence-metrics-v2",
            manifest.get("spec") == dataclasses.asdict(spec),
            manifest.get("locations_traced") == expected_index.size,
            manifest.get("standpoint_array_sha256") == standpoints.sha256,
            np.array_equal(index, expected_index),
            np.array_equal(points, standpoints.points),
            np.array_equal(ground, standpoints.ground_z_m),
            rho.shape == (expected_index.size, spec.cells),
            grid.shape == (spec.cells, 3),
            _valid_spectrum_arrays(rho, grid, solid_angle, spec.cells),
            manifest.get("local_grid_sha256") == _joined_array_sha256(grid),
            manifest.get("rho_sha256") == _joined_array_sha256(rho),
            manifest.get("solid_angle_sr") == solid_angle,
            len(rows) == expected_index.size,
            row_index == [int(value) for value in expected_index],
            row_kind == list(standpoints.point_kind),
            trace_index == [int(value) for value in expected_index],
            metric_values.ndim == 2,
            metric_values.shape[0] == expected_index.size,
            np.all(np.isfinite(metric_values)),
            all(names == metric_names[0] for names in metric_names),
            peak_cells.shape == (expected_index.size,),
            np.all((peak_cells >= 0) & (peak_cells < spec.cells)),
            peak_vectors.shape == (expected_index.size, 3),
            np.all(np.isfinite(peak_vectors)),
            np.allclose(np.linalg.norm(peak_vectors, axis=1), 1.0, rtol=0.0, atol=1e-12),
            file_hashes_present,
            file_hashes_valid,
        )
    )


def aggregate_runs(
    config: AngularConvergenceConfig,
    reference: ReferenceIdentity,
    code: dict[str, Any],
    specs: tuple[AngularRunSpec, ...],
    coupler: Any,
    *,
    analysis_dir: pathlib.Path,
) -> dict[str, Any]:
    """Average raw linear-power spectra, then compare every configuration."""
    raw_rows: dict[AngularRunSpec, list[dict[str, Any]]] = {}
    flat_rows: dict[AngularRunSpec, list[dict[str, float]]] = {}
    raw_spectra: dict[AngularRunSpec, tuple[np.ndarray, np.ndarray, float]] = {}
    identities: dict[str, str] = {}
    for spec in specs:
        run_dir = config.output_dir / "runs" / spec.name
        identity = run_identity(config, reference, code, spec)
        if not reusable_run(run_dir, identity, spec, reference.standpoints):
            raise RuntimeError(f"cannot aggregate incomplete or stale run {spec.name}")
        metrics = json.loads((run_dir / "metrics.json").read_text())
        raw_rows[spec] = list(metrics["rows"])
        flat_rows[spec] = [_flatten_metrics(row) for row in raw_rows[spec]]
        with np.load(run_dir / "spectra.npz") as artifact:
            raw_spectra[spec] = (
                np.asarray(artifact["local_grid"], dtype=np.float64),
                np.asarray(artifact["rho_rooftop"], dtype=np.float64),
                float(artifact["solid_angle"]),
            )
        identities[spec.name] = identity

    grid_by_cells: dict[int, tuple[np.ndarray, float]] = {}
    for spec, (grid, _rho, solid_angle) in raw_spectra.items():
        previous = grid_by_cells.get(spec.cells)
        if previous is None:
            grid_by_cells[spec.cells] = (grid, solid_angle)
        elif not np.array_equal(previous[0], grid) or previous[1] != solid_angle:
            raise RuntimeError(f"runs with {spec.cells} cells use different angular grids")

    reference_cells, reference_rays = config.reference_spec
    target_by_seed = {
        spec.seed: spec for spec in specs if spec.cells == reference_cells and spec.rays == reference_rays
    }
    per_run: dict[str, Any] = {}
    for spec, rows in flat_rows.items():
        summary = {name: _summary([float(row[name]) for row in rows]) for name in sorted(rows[0])}
        target = target_by_seed.get(spec.seed)
        if target is None:
            raise RuntimeError(f"seed {spec.seed} has no shared reference run")
        target_rows = flat_rows[target]
        paired = {
            name: _paired_delta(
                np.asarray([row[name] for row in rows], dtype=np.float64),
                np.asarray([row[name] for row in target_rows], dtype=np.float64),
            )
            for name in sorted(rows[0])
        }
        per_run[spec.name] = {
            "spec": dataclasses.asdict(spec),
            "metrics": summary,
            "paired_delta_to_reference_same_seed": paired,
            "peak_direction_delta_deg_to_reference_same_seed": _summary(
                _peak_direction_delta(raw_rows[spec], raw_rows[target])
            ),
        }

    ensemble_rows: dict[tuple[int, int], list[dict[str, Any]]] = {}
    ensemble_flat: dict[tuple[int, int], list[dict[str, float]]] = {}
    configurations: dict[str, dict[str, Any]] = {}
    for cells, rays in sorted({(spec.cells, spec.rays) for spec in specs}):
        members = sorted(
            (spec for spec in specs if spec.cells == cells and spec.rays == rays),
            key=lambda spec: spec.seed,
        )
        grid, mean_rho, solid_angle = mean_seed_spectra([raw_spectra[spec] for spec in members])
        body = coupler.couple_many(
            grid,
            mean_rho,
            solid_angle,
            float(reference.manifest["reference_s0_w_m2"]),
            chunk_cells=config.body_chunk_cells,
        )
        mean_rows = [
            {
                "index": int(index),
                "point_kind": reference.standpoints.point_kind[row],
                **spectrum_metrics(grid, mean_rho[row], solid_angle, config.fixed_sectors),
                "body": body[row].as_dict(),
            }
            for row, index in enumerate(reference.standpoints.index)
        ]
        key = (cells, rays)
        ensemble_rows[key] = mean_rows
        ensemble_flat[key] = [_flatten_metrics(row) for row in mean_rows]
        label = f"cells{cells}_rays{rays}"
        ensemble_dir = analysis_dir / "ensembles" / label
        ensemble_dir.mkdir(parents=True, exist_ok=True)
        member_seeds = [spec.seed for spec in members]
        ensemble_identity = canonical_sha256(
            {
                "cells": cells,
                "rays": rays,
                "seeds": member_seeds,
                "raw_run_identities": [identities[spec.name] for spec in members],
                "standpoint_array_sha256": reference.standpoints.sha256,
                "mean_rho_sha256": _joined_array_sha256(mean_rho),
                "local_grid_sha256": _joined_array_sha256(grid),
                "solid_angle_sr": solid_angle,
                "aggregation": "arithmetic_mean_linear_power",
                "smoothing": "none",
            }
        )
        mean_spectrum_path = ensemble_dir / "mean_spectrum.npz"
        _write_ensemble_spectra(
            mean_spectrum_path,
            reference.standpoints,
            mean_rho,
            grid,
            solid_angle,
            member_seeds,
            ensemble_identity,
        )
        member_rows = [row for spec in members for row in flat_rows[spec]]
        metric_names = sorted(member_rows[0])
        configurations[label] = {
            "schema": "angular-convergence-ensemble-v2",
            "cells": cells,
            "rays": rays,
            "seeds": member_seeds,
            "raw_run_identities": [identities[spec.name] for spec in members],
            "aggregation": "arithmetic mean of raw rho in linear power units",
            "smoothing": "none",
            "mean_rho_sha256": _joined_array_sha256(mean_rho),
            "local_grid_sha256": _joined_array_sha256(grid),
            "standpoint_array_sha256": reference.standpoints.sha256,
            "solid_angle_sr": solid_angle,
            "ensemble_identity_sha256": ensemble_identity,
            "mean_spectrum_file_sha256": file_sha256(mean_spectrum_path),
            "rows": mean_rows,
            "metrics_over_seeds_and_standpoints": {
                name: _summary([float(row[name]) for row in member_rows]) for name in metric_names
            },
            "seed_mean_spread": {
                name: _summary([float(np.mean([row[name] for row in flat_rows[spec]])) for spec in members])
                for name in metric_names
            },
        }
        _write_json_atomic(ensemble_dir / "metrics.json", configurations[label])

    reference_key = config.reference_spec
    if reference_key not in ensemble_flat:
        raise RuntimeError("shared reference configuration is absent from the ensemble")
    target_flat = ensemble_flat[reference_key]
    target_rows = ensemble_rows[reference_key]
    for key, rows in ensemble_flat.items():
        label = f"cells{key[0]}_rays{key[1]}"
        configurations[label]["mean_spectrum_convergence_to_reference"] = {
            name: _paired_delta(
                np.asarray([row[name] for row in rows], dtype=np.float64),
                np.asarray([row[name] for row in target_flat], dtype=np.float64),
            )
            for name in sorted(rows[0])
        }
        configurations[label]["peak_direction_delta_deg_to_reference"] = _summary(
            _peak_direction_delta(ensemble_rows[key], target_rows)
        )
        _write_json_atomic(analysis_dir / "ensembles" / label / "metrics.json", configurations[label])
    return {
        "schema": "angular-convergence-aggregate-v2",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "contract": config.contract,
        "seed_mode": analysis_dir.name,
        "reference": reference.as_dict(),
        "reference_configuration": {"cells": reference_cells, "rays": reference_rays},
        "code": code,
        "aggregation": "arithmetic mean of raw rho in linear power units",
        "smoothing": "none",
        "run_identities": identities,
        "per_run_summaries": per_run,
        "configuration_summaries": configurations,
    }


def mean_seed_spectra(
    spectra: list[tuple[np.ndarray, np.ndarray, float]],
) -> tuple[np.ndarray, np.ndarray, float]:
    """Return the arithmetic mean of matched raw spectra in linear power."""
    if not spectra:
        raise ValueError("at least one seed spectrum is required")
    reference_grid, reference_rho, reference_solid_angle = spectra[0]
    grid = np.asarray(reference_grid, dtype=np.float64)
    first = np.asarray(reference_rho, dtype=np.float64)
    if first.ndim != 2 or grid.shape != (first.shape[1], 3):
        raise ValueError("seed spectrum shapes disagree")
    values: list[np.ndarray] = []
    for candidate_grid, candidate_rho, candidate_solid_angle in spectra:
        rho = np.asarray(candidate_rho, dtype=np.float64)
        if not np.array_equal(np.asarray(candidate_grid, dtype=np.float64), grid):
            raise ValueError("seed spectra use different angular grids")
        if rho.shape != first.shape:
            raise ValueError("seed spectra use different array shapes")
        if float(candidate_solid_angle) != float(reference_solid_angle):
            raise ValueError("seed spectra use different solid angles")
        if not np.all(np.isfinite(rho)) or np.any(rho < 0.0):
            raise ValueError("seed spectra must be finite and nonnegative")
        values.append(rho)
    mean = np.mean(np.stack(values, axis=0), axis=0, dtype=np.float64)
    return grid, mean, float(reference_solid_angle)


def _valid_spectrum_arrays(
    rho: np.ndarray,
    grid: np.ndarray,
    solid_angle: float,
    cells: int,
) -> bool:
    """Check the numerical and geometric contract of one raw spectrum."""
    expected_solid_angle = 4.0 * np.pi / cells
    norms = np.linalg.norm(grid, axis=1) if grid.shape == (cells, 3) else np.asarray([])
    return all(
        (
            rho.ndim == 2,
            rho.shape[1:] == (cells,),
            grid.shape == (cells, 3),
            np.array_equal(grid, fibonacci_sphere(cells)),
            np.all(np.isfinite(rho)),
            np.all(rho >= 0.0),
            np.all(np.isfinite(grid)),
            norms.shape == (cells,),
            np.allclose(norms, 1.0, rtol=0.0, atol=1e-12),
            np.isfinite(solid_angle),
            solid_angle == expected_solid_angle,
        )
    )


def _flatten_metrics(row: dict[str, Any]) -> dict[str, float]:
    out = {
        "chi": float(row["chi"]),
        "peak_rho_per_sr": float(row["peak_rho_per_sr"]),
        "peak_cell_mass": float(row["peak_cell_mass"]),
        "peak_cell_share": float(row["peak_cell_share"]),
        "top_1_percent_mass": float(row["top_1_percent_mass"]),
        "top_1_percent_share": float(row["top_1_percent_share"]),
    }
    out.update({f"fixed_sector_mass.{name}": float(value) for name, value in row["fixed_sector_mass"].items()})
    out.update({f"body.{name}": float(value) for name, value in row["body"].items()})
    return out


def _summary(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "sample_std": float(np.std(array, ddof=1)) if array.size > 1 else 0.0,
        "min": float(np.min(array)),
        "max": float(np.max(array)),
    }


def _peak_direction_delta(actual: list[dict[str, Any]], reference: list[dict[str, Any]]) -> list[float]:
    if len(actual) != len(reference):
        raise ValueError("peak-direction rows are not paired")
    return [
        angular_distance_deg(
            np.asarray(row["peak_direction"]["unit_vector"], dtype=np.float64),
            np.asarray(target["peak_direction"]["unit_vector"], dtype=np.float64),
        )
        for row, target in zip(actual, reference, strict=True)
    ]


def _paired_delta(actual: np.ndarray, reference: np.ndarray) -> dict[str, Any]:
    if actual.shape != reference.shape:
        raise ValueError("paired metric arrays use different shapes")
    if not np.all(np.isfinite(actual)) or not np.all(np.isfinite(reference)):
        raise ValueError("paired metric arrays must be finite")
    if np.any(actual < 0.0) or np.any(reference < 0.0):
        raise ValueError("paired metric arrays must be nonnegative")
    difference = actual - reference
    difference_scale = float(np.max(np.abs(difference)))
    mean_absolute = (
        difference_scale * float(np.mean(np.abs(difference / difference_scale))) if difference_scale > 0.0 else 0.0
    )
    relative_rms, relative_rms_overflow = _scaled_rms_ratio(difference, reference)
    positive = (actual > 0.0) & (reference > 0.0)
    actual_positive_reference_zero = (actual > 0.0) & (reference == 0.0)
    actual_zero_reference_positive = (actual == 0.0) & (reference > 0.0)
    both_zero = (actual == 0.0) & (reference == 0.0)
    finite_db = 10.0 * (np.log10(actual[positive]) - np.log10(reference[positive]))
    return {
        "mean_absolute": mean_absolute,
        "root_mean_square_relative": relative_rms,
        "root_mean_square_relative_unrepresentable": relative_rms_overflow,
        "median_db": float(np.median(finite_db)) if np.any(positive) else None,
        "max_absolute_db": (float(np.max(np.abs(finite_db))) if np.any(positive) else None),
        "db_population": {
            "total_pairs": int(actual.size),
            "finite_positive_pairs": int(np.count_nonzero(positive)),
            "actual_positive_reference_zero": int(np.count_nonzero(actual_positive_reference_zero)),
            "actual_zero_reference_positive": int(np.count_nonzero(actual_zero_reference_positive)),
            "both_zero": int(np.count_nonzero(both_zero)),
            "finite_db_statistics_use_positive_pairs_only": True,
        },
    }


def _scaled_rms_ratio(actual: np.ndarray, reference: np.ndarray) -> tuple[float | None, bool]:
    """Return RMS(actual) / RMS(reference) without squaring raw magnitudes."""

    def scaled_rms(value: np.ndarray) -> tuple[float, float]:
        scale = float(np.max(np.abs(value)))
        if scale == 0.0:
            return 0.0, 0.0
        unit_rms = float(np.sqrt(np.mean((value / scale) ** 2)))
        return scale, unit_rms

    actual_scale, actual_unit_rms = scaled_rms(actual)
    reference_scale, reference_unit_rms = scaled_rms(reference)
    if reference_scale == 0.0:
        return (0.0, False) if actual_scale == 0.0 else (None, False)
    if actual_scale == 0.0:
        return 0.0, False
    log_ratio = (
        math.log(actual_scale) + math.log(actual_unit_rms) - math.log(reference_scale) - math.log(reference_unit_rms)
    )
    if log_ratio > math.log(np.finfo(np.float64).max):
        return None, True
    return float(math.exp(log_ratio)), False


def code_provenance(root: pathlib.Path) -> dict[str, Any]:
    """Record Git state and a hash of the exact Python source used."""
    repository = root.parents[2]

    def git(*args: str) -> str:
        result = subprocess.run(
            ("git", *args),
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    try:
        status = git("status", "--porcelain=v1")
        git_sha = git("rev-parse", "HEAD")
        git_branch = git("branch", "--show-current")
        git_available = True
    except (OSError, subprocess.CalledProcessError):
        # Rented workers receive an rsync snapshot without `.git`. The source
        # tree digest below still identifies every Python byte used there.
        status = ""
        git_sha = "unavailable-rsync-snapshot"
        git_branch = "unavailable-rsync-snapshot"
        git_available = False
    source_files = sorted((root / "semantic_twin").rglob("*.py"))
    source_files.append(root / "run_angular_convergence.py")
    source_files.extend(sorted((repository / "src" / "aegis").rglob("*.py")))
    digest = hashlib.sha256()
    for path in source_files:
        if not path.is_file():
            continue
        digest.update(str(path.relative_to(repository)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {
        "git_available": git_available,
        "git_sha": git_sha,
        "git_branch": git_branch,
        "git_dirty": bool(status) if git_available else None,
        "git_status_sha256": hashlib.sha256(status.encode()).hexdigest(),
        "source_tree_sha256": digest.hexdigest(),
        "runtime_versions": {
            "python": platform.python_version(),
            **{name: _distribution_version(name) for name in ("numpy", "aegis", "mitsuba", "drjit")},
        },
    }


def _distribution_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "unavailable"


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _joined_array_sha256(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        value = np.ascontiguousarray(array)
        digest.update(value.dtype.str.encode())
        digest.update(str(value.shape).encode())
        digest.update(value.tobytes())
    return digest.hexdigest()


def _write_spectra(
    path: pathlib.Path,
    standpoints: FrozenStandpoints,
    rho: np.ndarray,
    local_grid: np.ndarray,
    solid_angle: float,
) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        np.savez_compressed(
            stream,
            index=standpoints.index[: rho.shape[0]],
            point=standpoints.points[: rho.shape[0]],
            ground_z_m=standpoints.ground_z_m[: rho.shape[0]],
            rho_rooftop=rho,
            local_grid=local_grid,
            solid_angle=np.asarray(solid_angle, dtype=np.float64),
        )
    temporary.replace(path)


def _write_ensemble_spectra(
    path: pathlib.Path,
    standpoints: FrozenStandpoints,
    rho: np.ndarray,
    local_grid: np.ndarray,
    solid_angle: float,
    seeds: list[int],
    identity: str,
) -> None:
    """Store one unsmoothed seed mean with the exact member seeds."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        np.savez_compressed(
            stream,
            index=standpoints.index,
            point=standpoints.points,
            ground_z_m=standpoints.ground_z_m,
            rho_rooftop_mean=np.asarray(rho, dtype=np.float64),
            local_grid=np.asarray(local_grid, dtype=np.float64),
            solid_angle=np.asarray(solid_angle, dtype=np.float64),
            seeds=np.asarray(seeds, dtype=np.int64),
            identity_sha256=np.asarray(identity),
            aggregation=np.asarray("arithmetic_mean_linear_power"),
            smoothing=np.asarray("none"),
        )
    temporary.replace(path)


def _write_json_atomic(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)
