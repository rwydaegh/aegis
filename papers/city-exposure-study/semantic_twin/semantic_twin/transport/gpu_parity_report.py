"""Artifact comparison, timing ratios, and acceptance for GPU parity runs."""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

import numpy as np


def sha256_array(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(value.dtype.str.encode())
    digest.update(str(value.shape).encode())
    digest.update(value.tobytes())
    return digest.hexdigest()


def _difference(reference: np.ndarray, candidate: np.ndarray, epsilon: float) -> dict[str, Any]:
    finite = np.isfinite(reference) & np.isfinite(candidate)
    special_equal = (~finite) & (reference == candidate)
    difference = np.zeros(reference.shape, dtype=np.float64)
    difference[finite] = np.abs(reference[finite] - candidate[finite])
    mismatch = ~(special_equal | (finite & (difference <= epsilon)))
    return {
        "compared": int(reference.size),
        "mismatch_count": int(np.count_nonzero(mismatch)),
        "mismatch_flat_indices": np.flatnonzero(mismatch)[:20].tolist(),
        "max_abs": float(difference[finite].max(initial=0.0)),
        "mean_abs": float(difference[finite].mean()) if np.any(finite) else None,
    }


def _db_difference(reference: np.ndarray, candidate: np.ndarray, epsilon: float) -> dict[str, Any]:
    positive = (reference > 0.0) & (candidate > 0.0) & np.isfinite(reference) & np.isfinite(candidate)
    delta = 10.0 * np.log10(candidate[positive] / reference[positive])
    invalid = reference.size - int(np.count_nonzero(positive))
    finite_pair = np.isfinite(reference) & np.isfinite(candidate)
    other_equal = (reference == candidate) | (finite_pair & (np.abs(reference - candidate) <= epsilon))
    other_mismatch = (~positive) & ~other_equal
    return {
        "positive_pairs": int(delta.size),
        "non_positive_or_non_finite_pairs": invalid,
        "max_abs_db": float(np.abs(delta).max(initial=0.0)),
        "mean_db": float(delta.mean()) if delta.size else None,
        "over_epsilon_count": int(np.count_nonzero(np.abs(delta) > epsilon)),
        "non_positive_mismatch_count": int(np.count_nonzero(other_mismatch)),
    }


def _guard_artifacts(reference: Any, candidate: Any, names: set[str]) -> None:
    candidate_names = {name for name in candidate.files if not name.startswith("device__")}
    if names != candidate_names:
        raise ValueError("variant artifacts contain different arrays")
    for name in names:
        if reference[name].shape != candidate[name].shape:
            raise ValueError(
                f"array {name!r} has shape {reference[name].shape} in the reference and "
                f"{candidate[name].shape} in the candidate"
            )
        if reference[name].dtype != candidate[name].dtype:
            raise ValueError(
                f"array {name!r} has dtype {reference[name].dtype} in the reference and "
                f"{candidate[name].dtype} in the candidate"
            )


def compare_artifacts(reference_path: pathlib.Path, candidate_path: pathlib.Path, epsilon: float) -> dict[str, Any]:
    """Compare raw geometry and scientific outputs from two variants."""
    reference = np.load(reference_path)
    candidate = np.load(candidate_path)
    names = {name for name in reference.files if not name.startswith("device__")}
    _guard_artifacts(reference, candidate, names)
    hit_ref = reference["hit"]
    hit_new = candidate["hit"]
    both_hit = hit_ref & hit_new
    both_hit_indices = np.flatnonzero(both_hit)
    normals_ref = reference["normal"][both_hit]
    normals_new = candidate["normal"][both_hit]
    normal_dot = np.einsum("ij,ij->i", normals_ref, normals_new)
    normal_lengths = np.linalg.norm(normals_ref, axis=1) * np.linalg.norm(normals_new, axis=1)
    normal_dot = np.divide(normal_dot, normal_lengths, out=np.ones_like(normal_dot), where=normal_lengths > 0.0)
    normal_angle = np.degrees(np.arccos(np.clip(normal_dot, -1.0, 1.0)))
    normal_ray_mismatch = np.any(np.abs(normals_ref - normals_new) > epsilon, axis=1)
    hit_mismatch = hit_ref != hit_new
    face_mismatch = reference["face"][both_hit] != candidate["face"][both_hit]
    material_mismatch = reference["material"][both_hit] != candidate["material"][both_hit]
    scientific = {}
    for name in sorted(reference.files):
        if name.startswith(("chi__", "chi_direct__", "rho__", "scalar__")) or name == "exit_profile":
            scientific[name] = {
                "absolute": _difference(reference[name], candidate[name], epsilon),
                "db": _db_difference(reference[name], candidate[name], epsilon),
            }
    return {
        "hit": {
            "mismatch_count": int(np.count_nonzero(hit_mismatch)),
            "mismatch_ray_indices": np.flatnonzero(hit_mismatch)[:20].tolist(),
            "total": int(hit_ref.size),
        },
        "face": {
            "mismatch_count": int(np.count_nonzero(face_mismatch)),
            "mismatch_ray_indices": both_hit_indices[face_mismatch][:20].tolist(),
            "both_hit": int(np.count_nonzero(both_hit)),
        },
        "material": {
            "mismatch_count": int(np.count_nonzero(material_mismatch)),
            "mismatch_ray_indices": both_hit_indices[material_mismatch][:20].tolist(),
            "both_hit": int(np.count_nonzero(both_hit)),
        },
        "distance": _difference(reference["distance"], candidate["distance"], epsilon),
        "normal": {
            **_difference(normals_ref, normals_new, epsilon),
            "mismatch_ray_count": int(np.count_nonzero(normal_ray_mismatch)),
            "mismatch_ray_indices": both_hit_indices[normal_ray_mismatch][:20].tolist(),
            "max_angle_degrees": float(normal_angle.max(initial=0.0)),
            "mean_angle_degrees": float(normal_angle.mean()) if normal_angle.size else None,
        },
        "local_grid": _difference(reference["local_grid"], candidate["local_grid"], epsilon),
        "scientific": scientific,
    }


def compare_device_artifacts(
    reference_path: pathlib.Path, candidate_path: pathlib.Path, epsilon: float
) -> dict[str, Any]:
    """Compare prototype device records, which share the counter-based RNG."""
    with np.load(reference_path) as reference, np.load(candidate_path) as candidate:
        reference_names = sorted(name for name in reference.files if name.startswith("device__"))
        candidate_names = sorted(name for name in candidate.files if name.startswith("device__"))
        if not reference_names or not candidate_names:
            return {
                "available": False,
                "reference_available": bool(reference_names),
                "candidate_available": bool(candidate_names),
            }
        if reference_names != candidate_names:
            raise ValueError("variant artifacts contain different device arrays")
        for name in reference_names:
            if reference[name].shape != candidate[name].shape or reference[name].dtype != candidate[name].dtype:
                raise ValueError(f"device array {name!r} differs in shape or dtype")
        exact = {
            name: {
                "equal": bool(np.array_equal(reference[name], candidate[name])),
                "sha256_reference": sha256_array(reference[name]),
                "sha256_candidate": sha256_array(candidate[name]),
            }
            for name in ("device__ray_index", "device__bounces")
        }
        all_launch = {
            "equal": bool(
                np.array_equal(reference["device__all_launch_direction"], candidate["device__all_launch_direction"])
            ),
            "sha256_reference": sha256_array(reference["device__all_launch_direction"]),
            "sha256_candidate": sha256_array(candidate["device__all_launch_direction"]),
            "numeric": _difference(
                reference["device__all_launch_direction"], candidate["device__all_launch_direction"], epsilon
            ),
        }
        numeric = {
            name: _difference(reference[name], candidate[name], epsilon)
            for name in reference_names
            if name not in exact and name != "device__all_launch_direction"
        }
    return {"available": True, "identity": exact, "all_launch_direction": all_launch, "numeric": numeric}


def speedup(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, float]:
    return {
        "first": reference["first_seconds"] / candidate["first_seconds"],
        "warm_median": reference["warm_median_seconds"] / candidate["warm_median_seconds"],
    }


def cross_worker_consistency(variants: dict[str, Any], expected_rays: dict[str, str]) -> dict[str, Any]:
    fields = {
        "git_commit": lambda row: row["provenance"]["git"]["commit"],
        "git_status": lambda row: row["provenance"]["git"]["status_sha256"],
        "mesh": lambda row: row["provenance"]["mesh"]["sha256"],
        "face_class": lambda row: row["provenance"]["face_class"],
        "source": lambda row: row["provenance"]["source_sha256"],
        "python": lambda row: row["provenance"]["python"],
        "numpy": lambda row: row["provenance"]["numpy"],
        "mitsuba": lambda row: row["provenance"]["mitsuba"],
        "drjit": lambda row: row["provenance"]["drjit"],
        "config": lambda row: row["provenance"]["config"],
        "cpu_model": lambda row: row["provenance"]["runtime"]["cpu_model"],
        "logical_cpus": lambda row: row["provenance"]["runtime"]["logical_cpus"],
        "affinity_cpus": lambda row: row["provenance"]["runtime"]["affinity_cpus"],
        "drjit_thread_count": lambda row: row["provenance"]["runtime"]["drjit_thread_count"],
        "drjit_jit_flags": lambda row: row["provenance"]["runtime"]["drjit_jit_flags"],
        "fixed_rays": lambda row: row["fixed_ray_sha256"],
    }
    checks: dict[str, Any] = {}
    for name, getter in fields.items():
        values = {variant: getter(row) for variant, row in variants.items()}
        encoded = {json.dumps(value, sort_keys=True) for value in values.values()}
        expected = expected_rays if name == "fixed_rays" else None
        checks[name] = {
            "consistent": bool(values)
            and len(encoded) == 1
            and (expected is None or next(iter(values.values())) == expected),
            "values": values,
        }
    return checks


def _legacy_failures(config: Any, candidate: str, legacy: dict[str, Any]) -> list[str]:
    failures = []
    hit_fraction = legacy["hit"]["mismatch_count"] / max(legacy["hit"]["total"], 1)
    material_fraction = legacy["material"]["mismatch_count"] / max(legacy["material"]["both_hit"], 1)
    if hit_fraction > config.max_hit_mismatch_fraction:
        failures.append(f"{candidate}: hit mismatch fraction {hit_fraction:.6g}")
    if material_fraction > config.max_material_mismatch_fraction:
        failures.append(f"{candidate}: material mismatch fraction {material_fraction:.6g}")
    if legacy["distance"]["max_abs"] > config.max_distance_error_m:
        failures.append(f"{candidate}: distance error {legacy['distance']['max_abs']:.6g} m")
    if legacy["local_grid"]["max_abs"] > config.epsilon:
        failures.append(f"{candidate}: local-grid error {legacy['local_grid']['max_abs']:.6g}")
    for output, difference in legacy["scientific"].items():
        if difference["db"]["max_abs_db"] > config.max_scientific_error_db:
            failures.append(f"{candidate}: {output} error {difference['db']['max_abs_db']:.6g} dB")
        if difference["db"]["non_positive_mismatch_count"]:
            failures.append(f"{candidate}: {output} differs where a dB ratio is undefined")
    return failures


def _device_failures(config: Any, candidate: str, comparison: dict[str, Any]) -> list[str]:
    device = comparison.get("device_sbr")
    if device is None or not device.get("available", False):
        return [f"{candidate}: resident-device comparison is unavailable"] if config.require_device_sbr else []
    failures = [
        f"{candidate}: device {output} identity differs"
        for output, identity in device["identity"].items()
        if not identity["equal"]
    ]
    launch_error = device["all_launch_direction"]["numeric"]["max_abs"]
    if launch_error > config.max_device_error:
        failures.append(f"{candidate}: device launch-direction error {launch_error:.6g}")
    failures.extend(
        f"{candidate}: {output} error {difference['max_abs']:.6g}"
        for output, difference in device["numeric"].items()
        if difference["max_abs"] > config.max_device_error
    )
    failures.extend(
        f"{candidate}: device {key} differs"
        for key, values in comparison["device_status"].items()
        if key != "truncated_throughput" and values["reference"] != values["candidate"]
    )
    energy = comparison["device_status"]["truncated_throughput"]
    energy_error = abs(energy["reference"] - energy["candidate"])
    if energy_error > config.max_device_error:
        failures.append(f"{candidate}: device truncated-throughput error {energy_error:.6g}")
    return failures


def acceptance(
    config: Any, comparisons: dict[str, Any], consistency: dict[str, Any], errors: dict[str, str]
) -> dict[str, Any]:
    failures = [f"worker {name}: {error}" for name, error in errors.items()]
    failures.extend(f"cross-worker {name} differs" for name, check in consistency.items() if not check["consistent"])
    for candidate, comparison in comparisons.items():
        failures.extend(_legacy_failures(config, candidate, comparison["legacy_hybrid"]))
        failures.extend(_device_failures(config, candidate, comparison))
    return {
        "passed": not failures,
        "failures": failures,
        "thresholds": {
            "max_hit_mismatch_fraction": config.max_hit_mismatch_fraction,
            "max_material_mismatch_fraction": config.max_material_mismatch_fraction,
            "max_distance_error_m": config.max_distance_error_m,
            "max_scientific_error_db": config.max_scientific_error_db,
            "max_device_error": config.max_device_error,
            "absolute_epsilon": config.epsilon,
            "face_identity_required": False,
            "normal_identity_required": False,
        },
        "edge_tie_policy": (
            "Face and raw normal identity are diagnostic. Shared-edge and duplicate-face ties may select a different "
            "face. Acceptance instead checks hits, mapped materials, distance, and scientific outputs."
        ),
    }
