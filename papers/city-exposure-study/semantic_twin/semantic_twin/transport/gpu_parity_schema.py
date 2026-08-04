"""Validation for isolated GPU parity worker results."""

from __future__ import annotations

import pathlib
from collections.abc import Mapping
from typing import AbstractSet, Any

import numpy as np


MODELS = ("isotropic", "rooftop", "street_small_cell")
PROVENANCE_FIELDS = frozenset(
    {
        "git",
        "host",
        "platform",
        "python",
        "executable",
        "numpy",
        "mitsuba",
        "drjit",
        "runtime",
        "gpus",
        "variant",
        "mesh",
        "face_class",
        "source_sha256",
        "config",
    }
)
RUNTIME_FIELDS = frozenset(
    {
        "cpu_model",
        "logical_cpus",
        "affinity_cpus",
        "drjit_thread_count",
        "drjit_backend",
        "drjit_jit_flags",
        "cuda_runtime_visible_to_driver",
        "mitsuba_variant",
        "mitsuba_available_variants",
        "environment",
    }
)
DEVICE_FIELDS = frozenset(
    {
        "status",
        "rng",
        "ray_start",
        "rays",
        "escaped",
        "truncated",
        "truncated_throughput",
        "roulette_killed",
        "timing",
        "array_sha256",
    }
)


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _keys(value: Mapping[str, Any], required: AbstractSet[str], name: str) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise ValueError(f"{name} is missing {', '.join(missing)}")


def _timing(value: Any, repeats: int, name: str) -> None:
    timing = _mapping(value, name)
    _keys(timing, {"first_seconds", "first_label", "warm_seconds", "warm_median_seconds"}, name)
    if not isinstance(timing["first_label"], str) or not timing["first_label"]:
        raise ValueError(f"{name}.first_label must be a nonempty string")
    warm = timing["warm_seconds"]
    if not isinstance(warm, list) or len(warm) != repeats:
        raise ValueError(f"{name}.warm_seconds must contain {repeats} values")
    values = [timing["first_seconds"], timing["warm_median_seconds"], *warm]
    if any(not isinstance(item, int | float) or not np.isfinite(item) or item < 0.0 for item in values):
        raise ValueError(f"{name} contains an invalid duration")


def _array(array: np.ndarray, shape: tuple[int, ...], dtype: np.dtype[Any], name: str) -> None:
    if array.shape != shape:
        raise ValueError(f"artifact {name} has shape {array.shape}, expected {shape}")
    if array.dtype != dtype:
        raise ValueError(f"artifact {name} has dtype {array.dtype}, expected {dtype}")


def _validate_legacy_arrays(artifact: Any, rays: int, local_cells: int, exit_bands: int) -> None:
    _array(artifact["hit"], (rays,), np.dtype(bool), "hit")
    _array(artifact["face"], (rays,), np.dtype(np.int64), "face")
    _array(artifact["material"], (rays,), np.dtype(np.int64), "material")
    _array(artifact["distance"], (rays,), np.dtype(np.float64), "distance")
    _array(artifact["normal"], (rays, 3), np.dtype(np.float64), "normal")
    _array(artifact["local_grid"], (local_cells, 3), np.dtype(np.float64), "local_grid")
    _array(artifact["exit_profile"], (exit_bands,), np.dtype(np.float64), "exit_profile")
    for model in MODELS:
        _array(artifact[f"rho__{model}"], (local_cells,), np.dtype(np.float64), f"rho__{model}")
        _array(artifact[f"chi__{model}"], (), np.dtype(np.float64), f"chi__{model}")
        _array(artifact[f"chi_direct__{model}"], (), np.dtype(np.float64), f"chi_direct__{model}")
    scalar_names = [name for name in artifact.files if name.startswith("scalar__")]
    if not scalar_names:
        raise ValueError("artifact contains no PointResult scalars")
    for name in scalar_names:
        _array(artifact[name], (), np.dtype(np.float64), name)


def _validate_device_arrays(artifact: Any, rays: int, escaped: int, truncated: int, ray_start: int) -> None:
    _array(artifact["device__all_launch_direction"], (rays, 3), np.dtype(np.float32), "device all launch")
    _array(artifact["device__ray_index"], (escaped,), np.dtype(np.uint32), "device ray index")
    _array(
        artifact["device__escaped_launch_direction"],
        (escaped, 3),
        np.dtype(np.float32),
        "device escaped launch",
    )
    for name in ("exit_direction", "last_vertex"):
        _array(artifact[f"device__{name}"], (escaped, 3), np.dtype(np.float32), f"device {name}")
    for name in ("throughput", "path_length"):
        _array(artifact[f"device__{name}"], (escaped,), np.dtype(np.float32), f"device {name}")
    _array(artifact["device__bounces"], (escaped,), np.dtype(np.uint32), "device bounces")
    _array(
        artifact["device__truncated_throughput_terms"],
        (truncated,),
        np.dtype(np.float32),
        "device truncated throughput terms",
    )
    indices = artifact["device__ray_index"]
    if indices.size and (int(indices.min()) < ray_start or int(indices.max()) >= ray_start + rays):
        raise ValueError("device ray indices fall outside the declared ray range")


def _validate_provenance(value: Any, variant: str, config: dict[str, Any]) -> None:
    provenance = _mapping(value, "provenance")
    _keys(provenance, PROVENANCE_FIELDS, "provenance")
    _keys(_mapping(provenance["git"], "provenance.git"), {"commit", "dirty", "status_sha256"}, "provenance.git")
    _keys(_mapping(provenance["mesh"], "provenance.mesh"), {"path", "sha256"}, "provenance.mesh")
    runtime = _mapping(provenance["runtime"], "provenance.runtime")
    _keys(runtime, RUNTIME_FIELDS, "provenance.runtime")
    if provenance["variant"] != variant or runtime["mitsuba_variant"] != variant:
        raise ValueError("worker provenance records the wrong variant")
    if provenance["config"] != config:
        raise ValueError("worker provenance records a different configuration")


def validate_worker_result(
    value: Any,
    *,
    variant: str,
    config: dict[str, Any],
    expected_ray_hashes: dict[str, str],
    artifact_path: pathlib.Path,
    artifact_sha256: str,
) -> dict[str, Any]:
    """Return a validated worker result or raise a plain ``ValueError``."""
    row = dict(_mapping(value, "worker result"))
    _keys(
        row,
        {
            "provenance",
            "artifact",
            "artifact_sha256",
            "fixed_ray_sha256",
            "intersection",
            "legacy_hybrid_sbr",
            "device_sbr",
        },
        "worker result",
    )
    _validate_provenance(row["provenance"], variant, config)
    if row["fixed_ray_sha256"] != expected_ray_hashes:
        raise ValueError("worker result records different fixed-ray hashes")
    if pathlib.Path(row["artifact"]).resolve() != artifact_path.resolve() or row["artifact_sha256"] != artifact_sha256:
        raise ValueError("worker result records the wrong artifact")
    intersection = _mapping(row["intersection"], "intersection")
    _keys(intersection, {"hits", "timing"}, "intersection")
    _timing(intersection["timing"], int(config["repeats"]), "intersection.timing")
    legacy = _mapping(row["legacy_hybrid_sbr"], "legacy_hybrid_sbr")
    _keys(
        legacy,
        {"status", "launch_rng", "timing", "susceptibility", "susceptibility_direct", "scalars", "array_sha256"},
        "legacy_hybrid_sbr",
    )
    _timing(legacy["timing"], int(config["repeats"]), "legacy_hybrid_sbr.timing")
    with np.load(artifact_path) as artifact:
        _validate_legacy_arrays(artifact, int(config["rays"]), int(config["local_cells"]), int(config["exit_bands"]))
        device_value = row["device_sbr"]
        if device_value is not None:
            device = _mapping(device_value, "device_sbr")
            _keys(device, DEVICE_FIELDS, "device_sbr")
            if device["ray_start"] != 0 or device["rays"] != config["rays"]:
                raise ValueError("device result records the wrong ray range")
            rng = _mapping(device["rng"], "device_sbr.rng")
            if rng.get("ray_start") != device["ray_start"] or rng.get("seed") != config["seed"]:
                raise ValueError("device RNG identity records the wrong seed or ray start")
            _timing(device["timing"], int(config["repeats"]), "device_sbr.timing")
            _validate_device_arrays(
                artifact,
                int(device["rays"]),
                int(device["escaped"]),
                int(device["truncated"]),
                int(device["ray_start"]),
            )
    return row
