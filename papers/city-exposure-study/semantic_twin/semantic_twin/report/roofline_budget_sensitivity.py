"""Authenticated report for paired roofline ray and cell budget campaigns."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from semantic_twin.exposure.roofline_budget_sensitivity import (
    CAPTURE_SCHEMA,
    MEXICO_SHADOW_POINTS,
    RooflineBudgetSchedule,
)
from semantic_twin.exposure.roofline_campaign import BODY_METRICS, TIMING_FIELDS
from semantic_twin.illumination.sphere import fibonacci_sphere
from semantic_twin.report.roofline_campaign_comparison import CampaignComparisonError, _Campaign, _load_campaign

REPORT_SCHEMA = "aegis.roofline-budget-sensitivity-report.v1"
ARTIFACT_SCHEMA = "aegis.roofline-budget-sensitivity-artifacts.v1"
QUANTILES = (("q10", 0.1), ("q50", 0.5), ("q90", 0.9))


@dataclass(frozen=True)
class BudgetSensitivityArtifacts:
    """Files written by :func:`write_budget_sensitivity`."""

    json: Path
    csv: Path
    pdf: Path
    png: Path
    manifest: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity_differences(left: Any, right: Any, prefix: str = "") -> list[str]:
    if isinstance(left, dict) and isinstance(right, dict):
        result: list[str] = []
        for key in sorted(set(left) | set(right)):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in left or key not in right:
                result.append(path)
            else:
                result.extend(_identity_differences(left[key], right[key], path))
        return result
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return [prefix]
        result = []
        for index, (lhs, rhs) in enumerate(zip(left, right, strict=True)):
            result.extend(_identity_differences(lhs, rhs, f"{prefix}[{index}]"))
        return result
    return [] if left == right else [prefix]


def _is_run_config(record: Any) -> bool:
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        return False
    path = Path(record["path"])
    name = path.name
    return (name.startswith("roofline_campaign_") and name.endswith(".json")) or (
        "generated_configs" in path.parts and name.startswith("rays_") and "_cells_" in name and name.endswith(".json")
    )


def _normalise_run_config_input(data: dict[str, Any]) -> None:
    inputs = data.get("inputs")
    if not isinstance(inputs, dict) or not isinstance(inputs.get("files"), list):
        raise CampaignComparisonError("campaign identity must seal inputs.files for replay authentication")
    selected = [record for record in inputs["files"] if _is_run_config(record)]
    if len(selected) != 1:
        raise CampaignComparisonError("campaign identity must seal exactly one source or generated run config")
    inputs["files"] = [record for record in inputs["files"] if record is not selected[0]]
    inputs["file_count"] = len(inputs["files"])
    inputs["bytes"] = sum(int(record["bytes"]) for record in inputs["files"])


def _normalised_identity(campaign: _Campaign) -> dict[str, Any]:
    data = copy.deepcopy(campaign.identity_data)
    configuration = data.get("configuration")
    transport = data.get("transport")
    tracer = transport.get("tracer") if isinstance(transport, dict) else None
    tracer_config = tracer.get("configuration") if isinstance(tracer, dict) else None
    if not isinstance(configuration, dict) or not isinstance(tracer_config, dict):
        raise CampaignComparisonError("budget campaign does not seal campaign and tracer configuration")
    local_grid_sha256 = tracer.get("local_grid_sha256")
    if (
        not isinstance(local_grid_sha256, str)
        or len(local_grid_sha256) != 64
        or any(character not in "0123456789abcdef" for character in local_grid_sha256)
    ):
        raise CampaignComparisonError("budget campaign tracer local_grid_sha256 must be a lowercase SHA-256 digest")
    configuration.pop("convergence_looks", None)
    tracer_config.pop("rays", None)
    tracer_config.pop("local_cells", None)
    tracer.pop("local_grid_sha256")
    _normalise_run_config_input(data)
    return data


def _normalised_replay_identity(campaign: _Campaign) -> dict[str, Any]:
    data = copy.deepcopy(campaign.identity_data)
    _normalise_run_config_input(data)
    return data


def _checkpoint_path(campaign: _Campaign, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative:
        raise CampaignComparisonError("checkpoint entry has no relative path")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise CampaignComparisonError(f"checkpoint entry escapes its campaign: {relative!r}")
    return campaign.root / "checkpoint" / candidate


def _strip_timing(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_timing(item)
            for key, item in value.items()
            if key != "timing_availability" and "seconds" not in key
        }
    if isinstance(value, (list, tuple)):
        return [_strip_timing(item) for item in value]
    return value


def _normalised_locations(campaign: _Campaign) -> list[dict[str, Any]]:
    rows = copy.deepcopy(list(campaign.locations))
    for row in rows:
        row.pop("timing_seconds_per_replica_mean", None)
        row.pop("specular_diagnostic_variants", None)
    return rows


def _non_timing_shard_parity(replay: _Campaign, sealed: _Campaign) -> dict[str, Any]:
    replay_entries = {int(entry["seed"]): entry for entry in replay.checkpoint["committed"]}
    sealed_entries = {int(entry["seed"]): entry for entry in sealed.checkpoint["committed"]}
    mismatches: list[str] = []
    array_names: set[str] = set()
    if replay_entries.keys() != sealed_entries.keys():
        mismatches.append("committed_seed_set")
    for seed in sorted(set(replay_entries).intersection(sealed_entries)):
        with np.load(_checkpoint_path(replay, replay_entries[seed]["path"]), allow_pickle=False) as replay_payload:
            replay_arrays = {
                name: np.asarray(replay_payload[name]) for name in replay_payload.files if name != "timings"
            }
        with np.load(_checkpoint_path(sealed, sealed_entries[seed]["path"]), allow_pickle=False) as sealed_payload:
            sealed_arrays = {
                name: np.asarray(sealed_payload[name]) for name in sealed_payload.files if name != "timings"
            }
        array_names.update(replay_arrays)
        array_names.update(sealed_arrays)
        if replay_arrays.keys() != sealed_arrays.keys():
            mismatches.append(f"seed_{seed}:array_set")
            continue
        for name in replay_arrays:
            if not np.array_equal(replay_arrays[name], sealed_arrays[name]):
                mismatches.append(f"seed_{seed}:{name}")
    return {
        "status": "pass" if not mismatches else "fail",
        "excluded_array": "timings",
        "compared_arrays": sorted(array_names),
        "compared_seeds": sorted(set(replay_entries).intersection(sealed_entries)),
        "mismatches": mismatches,
    }


def _diagnostic_parity(replay: _Campaign, sealed: _Campaign) -> dict[str, Any]:
    replay_value = _strip_timing(list(replay.diagnostics))
    sealed_value = _strip_timing(list(sealed.diagnostics))
    passed = replay_value == sealed_value
    return {
        "status": "pass" if passed else "fail",
        "excluded_keys": "timing_availability and every key containing 'seconds'",
        "replicas": len(replay.diagnostics),
    }


def _cumulative_arrays(campaign: _Campaign) -> dict[int, np.ndarray]:
    entries = list(campaign.checkpoint.get("look_sab", ()))
    final = campaign.checkpoint.get("cumulative_sab")
    if final is not None:
        entries.append(final)
    arrays: dict[int, np.ndarray] = {}
    for entry in entries:
        replicas = int(entry["replicas"])
        with np.load(_checkpoint_path(campaign, entry["path"]), allow_pickle=False) as payload:
            value = np.asarray(payload["sab_sum"])
        previous = arrays.get(replicas)
        if previous is not None and not np.array_equal(previous, value):
            raise CampaignComparisonError(f"campaign has conflicting cumulative Sab arrays at {replicas} replicas")
        arrays[replicas] = value
    return arrays


def _cumulative_parity(replay: _Campaign, sealed: _Campaign) -> dict[str, Any]:
    replay_arrays = _cumulative_arrays(replay)
    sealed_arrays = _cumulative_arrays(sealed)
    mismatches: list[str] = []
    required = {4, 8, 12, 16}
    if set(replay_arrays) != required:
        mismatches.append("replay_replica_look_set")
    if set(sealed_arrays) != required:
        mismatches.append("sealed_replica_look_set")
    if replay_arrays.keys() != sealed_arrays.keys():
        mismatches.append("replica_look_set")
    for replicas in sorted(set(replay_arrays).intersection(sealed_arrays)):
        if not np.array_equal(replay_arrays[replicas], sealed_arrays[replicas]):
            mismatches.append(f"replicas_{replicas}")
    return {
        "status": "pass" if not mismatches else "fail",
        "replica_looks": sorted(set(replay_arrays).intersection(sealed_arrays)),
        "mismatches": mismatches,
    }


def _baseline_replay_parity(replay: _Campaign, sealed: _Campaign) -> dict[str, Any]:
    shard = _non_timing_shard_parity(replay, sealed)
    diagnostics = _diagnostic_parity(replay, sealed)
    cumulative = _cumulative_parity(replay, sealed)
    replay_identity = _normalised_replay_identity(replay)
    sealed_identity = _normalised_replay_identity(sealed)
    identity_differences = _identity_differences(replay_identity, sealed_identity)
    checks = {
        "current_budget": _budget(replay) == _budget(sealed) == (200_000, 4_096),
        "components": replay.components == sealed.components,
        "seeds": replay.seeds == sealed.seeds == tuple(range(7, 23)),
        "route_identity": replay.identity_data.get("walk") == sealed.identity_data.get("walk"),
        "locations_without_timing_and_diagnostics": _normalised_locations(replay) == _normalised_locations(sealed),
        "non_timing_shard_arrays": shard["status"] == "pass",
        "diagnostics_without_timing": diagnostics["status"] == "pass",
        "cumulative_sab": cumulative["status"] == "pass",
        "common_input_identity": not identity_differences,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "status": "pass" if not failed else "fail",
        "sealed_source_directory": str(sealed.root),
        "sealed_source_identity_sha256": sealed.identity["sha256"],
        "sealed_source_manifest_sha256": _sha256(sealed.root / "manifest.json"),
        "replay_identity_sha256": replay.identity["sha256"],
        "replay_manifest_sha256": _sha256(replay.root / "manifest.json"),
        "checks": checks,
        "failed_checks": failed,
        "non_timing_shard_arrays": shard,
        "diagnostics_without_timing": diagnostics,
        "cumulative_sab": cumulative,
        "common_input_identity": {
            "status": "pass" if not identity_differences else "fail",
            "excluded_metadata": "the single sealed source/generated roofline run-config input record",
            "difference_paths": identity_differences,
        },
    }
    if failed:
        raise CampaignComparisonError("sealed baseline replay parity failed: " + ", ".join(failed))
    return result


def _budget(campaign: _Campaign) -> tuple[int, int]:
    configuration = campaign.identity_data["transport"]["tracer"]["configuration"]
    try:
        return int(configuration["rays"]), int(configuration["local_cells"])
    except KeyError as exc:
        raise CampaignComparisonError("budget campaign does not seal rays and local_cells") from exc


def _validate_route(left: _Campaign, right: _Campaign) -> None:
    if left.points != right.points:
        raise CampaignComparisonError("budget campaigns have different standpoint counts")
    for point, (lhs, rhs) in enumerate(zip(left.locations, right.locations, strict=True)):
        for field in ("standpoint", "position_m", "body_yaw_deg", "ground_z_m"):
            if lhs.get(field) != rhs.get(field):
                raise CampaignComparisonError(f"budget route field {field!r} differs at standpoint {point}")


def _validate_arm(campaign: _Campaign, baseline: _Campaign, expected: tuple[int, int]) -> None:
    if campaign.transport_topology != "first_material_interaction_v1":
        raise CampaignComparisonError("budget arm is not first_material_interaction_v1")
    if campaign.components != ("direct", "all_specular", "first_diffuse", "total"):
        raise CampaignComparisonError("budget arm does not expose the closed current-contract components")
    if _budget(campaign) != expected:
        raise CampaignComparisonError(f"campaign budget {_budget(campaign)} does not match scheduled budget {expected}")
    if campaign.seeds != baseline.seeds or campaign.seeds != tuple(range(7, 23)):
        raise CampaignComparisonError("budget campaigns must share exact seeds 7 through 22")
    _validate_route(campaign, baseline)
    lhs = _normalised_identity(campaign)
    rhs = _normalised_identity(baseline)
    if lhs != rhs:
        differences = _identity_differences(lhs, rhs)
        raise CampaignComparisonError("undeclared budget identity drift: " + ", ".join(differences[:12]))


def _load_capture(campaign: _Campaign, expected_cells: int, schedule_sha256: str) -> np.ndarray:
    root = campaign.root / "first_diffuse_common_support"
    path = root / "manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise CampaignComparisonError(f"budget campaign has no valid first-diffuse capture manifest: {path}") from exc
    if manifest.get("schema") != CAPTURE_SCHEMA:
        raise CampaignComparisonError("first-diffuse capture has the wrong schema")
    if manifest.get("campaign_identity_sha256") != campaign.identity["sha256"]:
        raise CampaignComparisonError("first-diffuse capture is not bound to the campaign identity")
    if manifest.get("schedule_sha256") != schedule_sha256:
        raise CampaignComparisonError("first-diffuse capture is not bound to the active budget schedule")
    if int(manifest.get("common_support_cells", -1)) != expected_cells:
        raise CampaignComparisonError("first-diffuse capture uses the wrong common support")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or tuple(int(item.get("seed", -1)) for item in entries) != campaign.seeds:
        raise CampaignComparisonError("first-diffuse capture entries do not match the committed seed prefix")
    fields: list[np.ndarray] = []
    for item in entries:
        candidate = Path(str(item.get("path", "")))
        if candidate.is_absolute() or ".." in candidate.parts:
            raise CampaignComparisonError("first-diffuse capture path escapes its directory")
        capture = root / candidate
        if not capture.is_file() or _sha256(capture) != item.get("sha256"):
            raise CampaignComparisonError(f"first-diffuse capture hash failed: {capture}")
        with np.load(capture, allow_pickle=False) as payload:
            grid = np.asarray(payload["common_grid"])
            mass = np.asarray(payload["first_diffuse_mass"])
            raw = np.asarray(payload["raw_first_diffuse_m_inv2"])
            reference = np.asarray(payload["reference_transfer_m_inv2"])
        if grid.dtype != np.float64 or not np.array_equal(grid, fibonacci_sphere(expected_cells)):
            raise CampaignComparisonError("captured common grid is not the exact fixed Fibonacci support")
        if mass.dtype != np.float64 or mass.shape != (campaign.points, expected_cells) or np.any(mass < 0.0):
            raise CampaignComparisonError("captured first-diffuse field has the wrong shape, dtype, or sign")
        if not np.allclose(np.sum(mass, axis=1) * reference, raw, rtol=2.0e-12, atol=1.0e-15):
            raise CampaignComparisonError("captured first-diffuse field fails raw-transfer closure")
        fields.append(mass)
    return np.stack(fields)


def _db_ratio(candidate: np.ndarray, baseline: np.ndarray) -> np.ndarray:
    result = np.full(np.broadcast_shapes(candidate.shape, baseline.shape), np.nan, dtype=np.float64)
    np.log10(
        np.divide(candidate, baseline, out=np.ones_like(result), where=baseline > 0.0), out=result, where=baseline > 0.0
    )
    result *= 10.0
    return result


def _route_quantiles(values: np.ndarray) -> dict[str, float]:
    return {name: float(np.quantile(values, quantile)) for name, quantile in QUANTILES}


def _route_metric(candidate: np.ndarray, baseline: np.ndarray) -> dict[str, Any]:
    candidate_mean = np.mean(candidate, axis=0, dtype=np.float64)
    baseline_mean = np.mean(baseline, axis=0, dtype=np.float64)
    change = _db_ratio(candidate_mean, baseline_mean)
    finite = change[np.isfinite(change)]
    candidate_quantiles = _route_quantiles(candidate_mean)
    baseline_quantiles = _route_quantiles(baseline_mean)
    return {
        "candidate": candidate_quantiles,
        "baseline": baseline_quantiles,
        "route_quantile_difference_db": {
            name: float(_db_ratio(np.asarray(candidate_quantiles[name]), np.asarray(baseline_quantiles[name])))
            if baseline_quantiles[name] > 0.0
            else None
            for name, _quantile in QUANTILES
        },
        "candidate_minus_baseline_db": {
            name: float(np.quantile(finite, quantile)) if finite.size else None for name, quantile in QUANTILES
        },
        "maximum_absolute_db": float(np.max(np.abs(finite))) if finite.size else None,
    }


def _bootstrap_metric(
    candidate: np.ndarray,
    baseline: np.ndarray,
    *,
    indices: np.ndarray,
    confidence: float,
) -> dict[str, Any]:
    alpha = 0.5 * (1.0 - confidence)
    candidate_boot = np.mean(candidate[indices], axis=1, dtype=np.float64)
    baseline_boot = np.mean(baseline[indices], axis=1, dtype=np.float64)
    result: dict[str, Any] = {}
    for name, quantile in QUANTILES:
        paired = _db_ratio(
            np.quantile(candidate_boot, quantile, axis=1),
            np.quantile(baseline_boot, quantile, axis=1),
        )
        finite = paired[np.isfinite(paired)]
        result[name] = {
            "lower_db": float(np.quantile(finite, alpha)) if finite.size else None,
            "upper_db": float(np.quantile(finite, 1.0 - alpha)) if finite.size else None,
        }
    return result


def _directional_error(candidate: np.ndarray, baseline: np.ndarray) -> dict[str, Any]:
    if candidate.shape != baseline.shape or candidate.ndim != 3:
        raise CampaignComparisonError("paired directional captures must have identical (seed, point, cell) shape")
    seed_point_difference = candidate - baseline
    absolute_l1 = np.sum(np.abs(seed_point_difference), axis=2, dtype=np.float64)
    baseline_mass = np.sum(baseline, axis=2, dtype=np.float64)
    normalized_l1 = np.divide(
        absolute_l1,
        baseline_mass,
        out=np.zeros_like(absolute_l1),
        where=baseline_mass > 0.0,
    )
    zero_baseline_nonzero_candidate = (baseline_mass == 0.0) & (np.sum(candidate, axis=2) > 0.0)
    normalized_l1[zero_baseline_nonzero_candidate] = np.inf
    finite_normalized_l1 = normalized_l1[np.isfinite(normalized_l1)]
    absolute_l1_quantiles = _route_quantiles(absolute_l1.reshape(-1))
    normalized_l1_quantiles = (
        _route_quantiles(finite_normalized_l1) if finite_normalized_l1.size else {name: None for name, _ in QUANTILES}
    )
    candidate_mean = np.mean(candidate, axis=0, dtype=np.float64)
    baseline_mean = np.mean(baseline, axis=0, dtype=np.float64)
    difference = candidate_mean - baseline_mean
    denominator = np.linalg.norm(baseline_mean, axis=1)
    relative_l2 = np.divide(
        np.linalg.norm(difference, axis=1),
        denominator,
        out=np.zeros_like(denominator),
        where=denominator > 0.0,
    )
    candidate_norm = np.linalg.norm(candidate_mean, axis=1)
    cosine_denominator = candidate_norm * denominator
    cosine = np.divide(
        np.sum(candidate_mean * baseline_mean, axis=1),
        cosine_denominator,
        out=np.ones_like(denominator),
        where=cosine_denominator > 0.0,
    )
    return {
        "definition": (
            "Absolute and baseline-mass-normalized L1 compare every paired seed and standpoint. Relative L2 and "
            "cosine compare each standpoint's ensemble-mean first-diffuse mass spectrum. All metrics use exact "
            "nearest-cell projection onto the authenticated 512-cell Fibonacci support."
        ),
        "paired_seed_point_shape": [int(candidate.shape[0]), int(candidate.shape[1])],
        "absolute_l1_by_seed_and_standpoint": absolute_l1.tolist(),
        "absolute_l1_quantiles": absolute_l1_quantiles,
        "normalized_l1_by_seed_and_standpoint": [
            [float(value) if np.isfinite(value) else None for value in row] for row in normalized_l1
        ],
        "normalized_l1_quantiles": normalized_l1_quantiles,
        "normalized_l1_excluded_zero_baseline_nonzero_candidate": int(np.count_nonzero(~np.isfinite(normalized_l1))),
        "mass_closure": {
            "candidate_total_by_seed_and_standpoint": np.sum(candidate, axis=2, dtype=np.float64).tolist(),
            "baseline_total_by_seed_and_standpoint": baseline_mass.tolist(),
            "absolute_l1_upper_bounded_by_total_mass": bool(
                np.all(absolute_l1 <= np.sum(candidate, axis=2, dtype=np.float64) + baseline_mass + 1.0e-15)
            ),
        },
        "relative_l2_by_standpoint": relative_l2.tolist(),
        "cosine_similarity_by_standpoint": cosine.tolist(),
        "relative_l2_q50": float(np.quantile(relative_l2, 0.5)),
        "relative_l2_q90": float(np.quantile(relative_l2, 0.9)),
        "maximum_relative_l2": float(np.max(relative_l2)),
        "minimum_cosine_similarity": float(np.min(cosine)),
    }


def _component_invariance(candidate: _Campaign, baseline: _Campaign) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for component in ("direct", "all_specular"):
        index = candidate.components.index(component)
        raw_equal = np.array_equal(candidate.raw_transfer[:, :, index], baseline.raw_transfer[:, :, index])
        body_equal = np.array_equal(candidate.body_metrics[:, :, index], baseline.body_metrics[:, :, index])
        result[component] = {"raw_byte_exact": raw_equal, "body_metrics_byte_exact": body_equal}
    result["status"] = (
        "pass" if all(all(value.values()) for key, value in result.items() if key != "status") else "fail"
    )
    return result


def _timing(campaign: _Campaign, baseline: _Campaign) -> dict[str, Any]:
    observed = np.where(np.isfinite(campaign.timings), campaign.timings, 0.0)
    base = np.where(np.isfinite(baseline.timings), baseline.timings, 0.0)
    totals = np.sum(observed, axis=(0, 1), dtype=np.float64)
    base_totals = np.sum(base, axis=(0, 1), dtype=np.float64)
    return {
        name: {
            "seconds": float(totals[index]),
            "baseline_seconds": float(base_totals[index]),
            "ratio": float(totals[index] / base_totals[index]) if base_totals[index] > 0.0 else None,
        }
        for index, name in enumerate(TIMING_FIELDS)
    }


def _variance_time(candidate: _Campaign, baseline: _Campaign) -> dict[str, Any]:
    component = candidate.components.index("first_diffuse")
    candidate_variance = np.var(candidate.raw_transfer[:, :, component], axis=0, ddof=1)
    baseline_variance = np.var(baseline.raw_transfer[:, :, component], axis=0, ddof=1)
    candidate_time = np.sum(np.where(np.isfinite(candidate.timings), candidate.timings, 0.0), axis=0)
    baseline_time = np.sum(np.where(np.isfinite(baseline.timings), baseline.timings, 0.0), axis=0)
    trace = TIMING_FIELDS.index("stochastic_trace_seconds")
    candidate_product = candidate_variance * candidate_time[:, trace]
    baseline_product = baseline_variance * baseline_time[:, trace]
    ratio = np.divide(
        candidate_product, baseline_product, out=np.full_like(candidate_product, np.nan), where=baseline_product > 0.0
    )
    finite = ratio[np.isfinite(ratio)]
    return {
        "definition": "sample variance of first-diffuse raw transfer times observed stochastic trace seconds",
        "ratio_by_standpoint": [float(value) if np.isfinite(value) else None for value in ratio],
        "q50_ratio": float(np.quantile(finite, 0.5)) if finite.size else None,
        "q90_ratio": float(np.quantile(finite, 0.9)) if finite.size else None,
    }


def _recommendation(site_reports: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    failures: list[str] = []
    for site, report in site_reports.items():
        invariance = report["deterministic_invariance"]
        if invariance["status"] != "pass":
            failures.append(f"{site}: direct or exact order-1 invariance failed")
        if report["directional_first_diffuse"]["normalized_l1_quantiles"]["q90"] > 0.1:
            failures.append(f"{site}: paired q90 directional normalized L1 exceeds 0.1")
        if (
            report["normalized_wbSAR"]["maximum_absolute_db"] not in (None,)
            and report["normalized_wbSAR"]["maximum_absolute_db"] > 0.1
        ):
            failures.append(f"{site}: maximum standpoint wbSAR change exceeds 0.1 dB")
        shadow = report.get("mexico_shadow_points", {})
        if shadow.get("maximum_absolute_wbSAR_db") not in (None,) and shadow["maximum_absolute_wbSAR_db"] > 0.1:
            failures.append(f"{site}: shadow-point wbSAR change exceeds 0.1 dB")
    return {
        "migration_recommended": not failures,
        "decision": "eligible for author review"
        if not failures
        else "retain the 200000-ray, 4096-cell production baseline",
        "diagnostic_gates": {
            "deterministic_components_byte_exact": True,
            "directional_first_diffuse_paired_q90_normalized_l1_max": 0.1,
            "maximum_standpoint_wbSAR_change_db": 0.1,
            "maximum_mexico_shadow_wbSAR_change_db": 0.1,
        },
        "failed_gates": failures,
        "caveat": "This is a diagnostic recommendation and never mutates the production baseline.",
    }


def compare_budget_schedule(schedule: RooflineBudgetSchedule) -> dict[str, Any]:
    """Authenticate all 18 arms and compute paired scalar, body, directional, and timing metrics."""
    campaigns: dict[tuple[str, str], _Campaign] = {}
    captures: dict[tuple[str, str], np.ndarray] = {}
    sealed = {site: _load_campaign(schedule.sealed_baselines[site]) for site in schedule.sites}
    for site in schedule.sites:
        for arm in schedule.arms:
            campaign = _load_campaign(schedule.campaign_dir(site, arm))
            campaigns[(site, arm.key)] = campaign
            captures[(site, arm.key)] = _load_capture(campaign, schedule.common_support_cells, schedule.sha256)
    parity = {
        site: _baseline_replay_parity(campaigns[(site, schedule.baseline.key)], sealed[site]) for site in schedule.sites
    }
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schedule_sha256": schedule.sha256,
        "seeds": list(schedule.seeds),
        "common_random_numbers": {
            "contract": schedule.common_random_numbers,
            "pairing": "campaign seed and standpoint use the sealed point-seed derivation",
            "prefix": "counter draws are keyed by ray index, so every smaller IID run is an exact ray prefix",
        },
        "common_directional_support_cells": schedule.common_support_cells,
        "baseline": {"rays": schedule.baseline.rays, "cells": schedule.baseline.cells},
        "sealed_baseline_replay_parity": parity,
        "budgets": [],
    }
    for arm in schedule.arms:
        arm_report: dict[str, Any] = {"rays": arm.rays, "cells": arm.cells, "sites": {}}
        for site in schedule.sites:
            campaign = campaigns[(site, arm.key)]
            baseline = campaigns[(site, schedule.baseline.key)]
            _validate_arm(campaign, baseline, (arm.rays, arm.cells))
            indices = np.random.default_rng(
                np.random.SeedSequence([schedule.bootstrap_seed, arm.rays, arm.cells, sum(site.encode())])
            ).integers(0, len(schedule.seeds), size=(schedule.bootstrap_replicates, len(schedule.seeds)))
            total = campaign.components.index("total")
            first = campaign.components.index("first_diffuse")
            absorbed = BODY_METRICS.index("absorbed_power_w")
            sar = BODY_METRICS.index("sar_wb_w_kg")
            site_report: dict[str, Any] = {
                "campaign_identity_sha256": campaign.identity["sha256"],
                "manifest_sha256": _sha256(campaign.root / "manifest.json"),
                "directional_capture_manifest_sha256": _sha256(
                    campaign.root / "first_diffuse_common_support" / "manifest.json"
                ),
                "deterministic_invariance": _component_invariance(campaign, baseline),
                "total_transfer": _route_metric(campaign.raw_transfer[:, :, total], baseline.raw_transfer[:, :, total]),
                "first_diffuse_transfer": _route_metric(
                    campaign.raw_transfer[:, :, first], baseline.raw_transfer[:, :, first]
                ),
                "first_diffuse_absorbed_power": _route_metric(
                    campaign.body_metrics[:, :, first, absorbed], baseline.body_metrics[:, :, first, absorbed]
                ),
                "first_diffuse_normalized_wbSAR": _route_metric(
                    campaign.body_metrics[:, :, first, sar], baseline.body_metrics[:, :, first, sar]
                ),
                "absorbed_power": _route_metric(
                    campaign.body_metrics[:, :, total, absorbed], baseline.body_metrics[:, :, total, absorbed]
                ),
                "normalized_wbSAR": _route_metric(
                    campaign.body_metrics[:, :, total, sar], baseline.body_metrics[:, :, total, sar]
                ),
                "bootstrap_route_wbSAR_change": _bootstrap_metric(
                    campaign.body_metrics[:, :, total, sar],
                    baseline.body_metrics[:, :, total, sar],
                    indices=indices,
                    confidence=schedule.confidence,
                ),
                "directional_first_diffuse": _directional_error(
                    captures[(site, arm.key)], captures[(site, schedule.baseline.key)]
                ),
                "timing": _timing(campaign, baseline),
                "variance_time_efficiency": _variance_time(campaign, baseline),
            }
            if site == "mexico_zocalo":
                points = np.asarray(MEXICO_SHADOW_POINTS, dtype=np.int64)
                change = _db_ratio(
                    np.mean(campaign.body_metrics[:, points, total, sar], axis=0),
                    np.mean(baseline.body_metrics[:, points, total, sar], axis=0),
                )
                site_report["mexico_shadow_points"] = {
                    "standpoints": list(MEXICO_SHADOW_POINTS),
                    "normalized_wbSAR_candidate": np.mean(
                        campaign.body_metrics[:, points, total, sar], axis=0
                    ).tolist(),
                    "normalized_wbSAR_baseline": np.mean(baseline.body_metrics[:, points, total, sar], axis=0).tolist(),
                    "wbSAR_change_db": [float(value) if np.isfinite(value) else None for value in change],
                    "maximum_absolute_wbSAR_db": float(np.max(np.abs(change[np.isfinite(change)])))
                    if np.any(np.isfinite(change))
                    else None,
                    "first_diffuse_transfer_candidate": np.mean(
                        campaign.raw_transfer[:, points, first], axis=0
                    ).tolist(),
                    "first_diffuse_transfer_baseline": np.mean(
                        baseline.raw_transfer[:, points, first], axis=0
                    ).tolist(),
                    "absorbed_power_candidate": np.mean(
                        campaign.body_metrics[:, points, total, absorbed], axis=0
                    ).tolist(),
                    "absorbed_power_baseline": np.mean(
                        baseline.body_metrics[:, points, total, absorbed], axis=0
                    ).tolist(),
                }
            arm_report["sites"][site] = site_report
        arm_report["recommendation"] = _recommendation(arm_report["sites"])
        report["budgets"].append(arm_report)
    return report


def _write_csv(path: Path, report: Mapping[str, Any]) -> None:
    fields = (
        "rays",
        "cells",
        "site",
        "wbSAR_q10_change_db",
        "wbSAR_q50_change_db",
        "wbSAR_q90_change_db",
        "wbSAR_max_abs_db",
        "directional_absolute_l1_q10",
        "directional_absolute_l1_q50",
        "directional_absolute_l1_q90",
        "directional_normalized_l1_q10",
        "directional_normalized_l1_q50",
        "directional_normalized_l1_q90",
        "directional_relative_l2_q90",
        "directional_min_cosine",
        "variance_time_q50_ratio",
        "deterministic_invariance",
        "sealed_baseline_replay_parity",
        "migration_recommended",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for budget in report["budgets"]:
            for site, values in budget["sites"].items():
                writer.writerow(
                    {
                        "rays": budget["rays"],
                        "cells": budget["cells"],
                        "site": site,
                        **{
                            f"wbSAR_{name}_change_db": values["normalized_wbSAR"]["route_quantile_difference_db"][name]
                            for name, _quantile in QUANTILES
                        },
                        "wbSAR_max_abs_db": values["normalized_wbSAR"]["maximum_absolute_db"],
                        **{
                            f"directional_absolute_l1_{name}": values["directional_first_diffuse"][
                                "absolute_l1_quantiles"
                            ][name]
                            for name, _quantile in QUANTILES
                        },
                        **{
                            f"directional_normalized_l1_{name}": values["directional_first_diffuse"][
                                "normalized_l1_quantiles"
                            ][name]
                            for name, _quantile in QUANTILES
                        },
                        "directional_relative_l2_q90": values["directional_first_diffuse"]["relative_l2_q90"],
                        "directional_min_cosine": values["directional_first_diffuse"]["minimum_cosine_similarity"],
                        "variance_time_q50_ratio": values["variance_time_efficiency"]["q50_ratio"],
                        "deterministic_invariance": values["deterministic_invariance"]["status"],
                        "sealed_baseline_replay_parity": report["sealed_baseline_replay_parity"][site]["status"],
                        "migration_recommended": budget["recommendation"]["migration_recommended"],
                    }
                )


def _plot(report: Mapping[str, Any], pdf: Path, png: Path) -> None:
    import matplotlib.pyplot as plt

    budgets = [f"{item['rays'] // 1000}k/{item['cells'] // 1024}k" for item in report["budgets"]]
    sites = sorted(report["budgets"][0]["sites"])
    city_labels = {
        "madrid_plazamayor": "Madrid",
        "mexico_zocalo": "Mexico City",
        "prague_staromestske": "Prague",
    }
    colors = dict(zip(sites, plt.get_cmap("tab10").colors, strict=False))
    figure, axes = plt.subplots(2, 2, figsize=(7.2, 5.0), sharex=True)
    x = np.arange(len(budgets))
    city_lines = []
    for site in sites:
        (line,) = axes[0, 0].plot(
            x,
            [
                item["sites"][site]["normalized_wbSAR"]["route_quantile_difference_db"]["q50"]
                for item in report["budgets"]
            ],
            marker="o",
            markersize=4,
            linewidth=1.4,
            color=colors[site],
            label=city_labels.get(site, site.replace("_", " ")),
        )
        city_lines.append(line)
        axes[1, 0].plot(
            x,
            [
                item["sites"][site]["directional_first_diffuse"]["normalized_l1_quantiles"]["q90"]
                for item in report["budgets"]
            ],
            marker="o",
            markersize=4,
            linewidth=1.4,
            color=colors[site],
        )
        axes[1, 1].plot(
            x,
            [item["sites"][site]["timing"]["estimator_wall_seconds"]["ratio"] for item in report["budgets"]],
            marker="o",
            markersize=4,
            linewidth=1.4,
            color=colors[site],
        )

    mexico = "mexico_zocalo"
    axes[0, 1].plot(
        x,
        [item["sites"][mexico]["mexico_shadow_points"]["maximum_absolute_wbSAR_db"] for item in report["budgets"]],
        marker="o",
        markersize=4,
        linewidth=1.4,
        color=colors[mexico],
    )

    axes[0, 0].axhline(0.0, color="black", lw=0.7)
    axes[0, 0].set_title("(a) Route median", fontsize=9.5)
    axes[0, 0].set_ylabel("q50 wbSAR change (dB)", fontsize=8.5)
    axes[0, 1].set_title("(b) Mexico shadow points", fontsize=9.5)
    axes[0, 1].set_ylabel("Max |wbSAR change| (dB)", fontsize=8.5)
    axes[0, 1].set_ylim(bottom=0.0)
    axes[1, 0].set_title("(c) First-diffuse directionality", fontsize=9.5)
    axes[1, 0].set_ylabel("Paired q90 normalized L1", fontsize=8.5)
    axes[1, 0].set_ylim(bottom=0.0)
    axes[1, 1].axhline(1.0, color="black", lw=0.7)
    axes[1, 1].set_title("(d) Observed timing", fontsize=9.5)
    axes[1, 1].set_ylabel("Estimator wall time / baseline", fontsize=8.5)
    for axis in axes.flat:
        axis.grid(alpha=0.25)
        axis.tick_params(axis="both", labelsize=7.5)
    for axis in axes[1]:
        axis.set_xticks(x, budgets, rotation=25, ha="right")
    figure.suptitle("Ray and angular-cell budget sensitivity", y=0.98, fontsize=11)
    figure.legend(
        city_lines,
        [line.get_label() for line in city_lines],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.93),
        ncol=3,
        frameon=False,
        fontsize=8,
    )
    figure.supxlabel("Primary rays / first-diffuse cells", y=0.015, fontsize=9)
    figure.subplots_adjust(left=0.11, right=0.98, bottom=0.15, top=0.82, wspace=0.34, hspace=0.42)
    figure.savefig(pdf, bbox_inches="tight")
    figure.savefig(png, dpi=220, bbox_inches="tight")
    plt.close(figure)


def _manifest(
    path: Path, report: Mapping[str, Any], artifacts: Iterable[Path], schedule: RooflineBudgetSchedule
) -> None:
    sources = {"schedule": {"path": str(schedule.path), "sha256": _sha256(schedule.path)}}
    for site, config in sorted(schedule.sites.items()):
        sources[f"base_config:{site}"] = {"path": str(config), "sha256": _sha256(config)}
        parity = report["sealed_baseline_replay_parity"][site]
        sources[f"sealed_baseline:{site}"] = {
            "path": str(schedule.sealed_baselines[site]),
            "campaign_identity_sha256": parity["sealed_source_identity_sha256"],
            "manifest_sha256": parity["sealed_source_manifest_sha256"],
        }
    for budget in report["budgets"]:
        for site, values in budget["sites"].items():
            key = f"campaign:{site}:rays_{budget['rays']}:cells_{budget['cells']}"
            sources[key] = {
                "campaign_identity_sha256": values["campaign_identity_sha256"],
                "manifest_sha256": values["manifest_sha256"],
                "directional_capture_manifest_sha256": values["directional_capture_manifest_sha256"],
            }
    value = {
        "schema": ARTIFACT_SCHEMA,
        "report_schema": REPORT_SCHEMA,
        "schedule_identity_sha256": report["schedule_sha256"],
        "sources": sources,
        "artifacts": {
            artifact.name: {"sha256": _sha256(artifact), "bytes": artifact.stat().st_size} for artifact in artifacts
        },
    }
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_budget_sensitivity(schedule: RooflineBudgetSchedule, output_prefix: str | Path) -> BudgetSensitivityArtifacts:
    """Write authenticated JSON, CSV, PDF, PNG, and manifest artifacts."""
    report = compare_budget_schedule(schedule)
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    artifacts = BudgetSensitivityArtifacts(
        json=prefix.with_suffix(".json"),
        csv=prefix.with_suffix(".csv"),
        pdf=prefix.with_suffix(".pdf"),
        png=prefix.with_suffix(".png"),
        manifest=prefix.with_name(prefix.name + "_manifest.json"),
    )
    artifacts.json.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    _write_csv(artifacts.csv, report)
    _plot(report, artifacts.pdf, artifacts.png)
    _manifest(artifacts.manifest, report, (artifacts.json, artifacts.csv, artifacts.pdf, artifacts.png), schedule)
    return artifacts


__all__ = [
    "BudgetSensitivityArtifacts",
    "compare_budget_schedule",
    "write_budget_sensitivity",
]
