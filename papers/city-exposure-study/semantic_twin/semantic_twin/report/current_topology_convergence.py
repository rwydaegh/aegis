"""Authenticate and report current-topology convergence through 64 replicas."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from semantic_twin.exposure.roofline_campaign import BODY_METRICS, TIMING_FIELDS
from semantic_twin.report.roofline_campaign_comparison import (
    CampaignComparisonError,
    _Campaign,
    _checkpoint_artifact,
    _load_campaign,
    _sha256,
)

REPORT_SCHEMA = "current_topology_convergence_v1"
ARTIFACT_SCHEMA = "current_topology_convergence_artifacts_v1"
EXPECTED_SITES = (
    "korenmarkt",
    "prague_staromestske",
    "madrid_plazamayor",
    "mexico_zocalo",
    "tokyo_hachiko",
)
EXPECTED_LOOKS = (16, 24, 32, 48, 64)
SEALED_SEEDS = tuple(range(7, 23))
EXTENDED_SEEDS = tuple(range(7, 71))
QUANTILES = (0.1, 0.5, 0.9)
QUANTILE_NAMES = ("q10", "q50", "q90")
SHADOW_STANDPOINTS = {"mexico_zocalo": (0, 1, 3), "tokyo_hachiko": (13, 14, 15)}
IDENTITY_PLAN_ALLOWLIST = (
    "/configuration/planned_seeds",
    "/configuration/convergence_looks",
    "/inputs/files[run_config]",
    "/inputs/file_count",
    "/inputs/bytes",
)
TAIL_THRESHOLDS = {
    "q10_48_to_64_abs_db": 0.1,
    "shadow_point_48_to_64_max_abs_db": 0.25,
    "q10_bootstrap_95_width_db": 0.5,
    "rare_event_max_to_median_replica_ratio": 10.0,
}
ADDITIVE_BODY_METRICS = tuple(name for name in BODY_METRICS if name != "peak_sab_w_m2")


class CurrentTopologyConvergenceError(CampaignComparisonError):
    """The supplied campaigns cannot support the current-topology report."""


@dataclass(frozen=True)
class CurrentTopologyConvergenceArtifacts:
    """Paths written by :func:`write_current_topology_convergence`."""

    json: Path
    csv: Path
    pdf: Path
    png: Path
    manifest: Path


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _configuration(campaign: _Campaign) -> dict[str, Any]:
    value = campaign.identity_data.get("configuration")
    if not isinstance(value, dict):
        raise CurrentTopologyConvergenceError(f"campaign identity has no configuration object: {campaign.root}")
    return value


def _site(campaign: _Campaign) -> str:
    value = _configuration(campaign).get("site")
    if not isinstance(value, str):
        raise CurrentTopologyConvergenceError(f"campaign identity has no site: {campaign.root}")
    return value


def _validate_current_contract(campaign: _Campaign) -> None:
    site = _site(campaign)
    configuration = _configuration(campaign)
    required_configuration = {
        "material_mode": "atlas",
        "reference_mode": "per_density_eirp",
        "route_contract": "provider_corridor_v1",
        "minimum_completed_specular_order": 1,
        "specular_acceptance": "first_material_interaction_exact_order_1",
        "transport_topology": "first_material_interaction_v1",
    }
    for name, expected in required_configuration.items():
        if configuration.get(name) != expected:
            raise CurrentTopologyConvergenceError(f"current contract field {name} is invalid for {site}")
    tracer = campaign.identity_data.get("transport", {}).get("tracer", {}).get("configuration", {})
    required_tracer = {
        "rays": 200_000,
        "local_cells": 4096,
        "frequency_hz": 15_000_000_000,
        "max_bounces": 1,
    }
    for name, expected in required_tracer.items():
        if tracer.get(name) != expected:
            raise CurrentTopologyConvergenceError(f"current tracer field {name} is invalid for {site}")
    body = campaign.identity_data.get("body", {})
    required_body = {"phantom": "duke", "surface_elements": 56_024, "frequency_hz": 15_000_000_000.0}
    for name, expected in required_body.items():
        if body.get(name) != expected:
            raise CurrentTopologyConvergenceError(f"current body field {name} is invalid for {site}")


def _run_config_record(path: str) -> bool:
    name = Path(path).name
    return name.startswith("roofline_campaign_") and name.endswith(".json")


def _normalise_identity(campaign: _Campaign) -> tuple[dict[str, Any], dict[str, Any]]:
    data = copy.deepcopy(campaign.identity_data)
    configuration = data.get("configuration")
    if not isinstance(configuration, dict):
        raise CurrentTopologyConvergenceError(f"campaign identity has no configuration object: {campaign.root}")
    removed: dict[str, Any] = {
        "/configuration/planned_seeds": configuration.pop("planned_seeds", None),
        "/configuration/convergence_looks": configuration.pop("convergence_looks", None),
    }
    inputs = data.get("inputs")
    if not isinstance(inputs, dict) or not isinstance(inputs.get("files"), list):
        raise CurrentTopologyConvergenceError(f"campaign identity has no sealed input list: {campaign.root}")
    retained: list[dict[str, Any]] = []
    run_configs: list[dict[str, Any]] = []
    for record in inputs["files"]:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise CurrentTopologyConvergenceError(f"campaign identity has an invalid input record: {campaign.root}")
        if _run_config_record(record["path"]):
            run_configs.append(record)
        else:
            retained.append(record)
    if len(run_configs) != 1:
        raise CurrentTopologyConvergenceError(
            f"campaign identity must seal exactly one roofline run config: {campaign.root}"
        )
    removed["/inputs/files[run_config]"] = run_configs[0]
    removed["/inputs/file_count"] = inputs.pop("file_count", None)
    removed["/inputs/bytes"] = inputs.pop("bytes", None)
    inputs["files"] = retained
    return data, removed


def _without_timing(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if "timing" in lowered or lowered.endswith("_seconds") or lowered == "seconds":
                continue
            result[key] = _without_timing(item)
        return result
    if isinstance(value, list):
        return [_without_timing(item) for item in value]
    return value


def _load_diagnostics(campaign: _Campaign, count: int) -> list[Any]:
    result: list[Any] = []
    for entry in campaign.checkpoint["committed"][:count]:
        path = _checkpoint_artifact(campaign.root, entry.get("diagnostics_path"))
        result.append(_without_timing(json.loads(path.read_text(encoding="utf-8"))))
    return result


def _scientific_shard_arrays(campaign: _Campaign, count: int) -> list[dict[str, np.ndarray]]:
    result: list[dict[str, np.ndarray]] = []
    for entry in campaign.checkpoint["committed"][:count]:
        path = _checkpoint_artifact(campaign.root, entry.get("path"))
        with np.load(path, allow_pickle=False) as payload:
            result.append({name: np.array(payload[name]) for name in payload.files if name != "timings"})
    return result


def _prefix_parity(extended: _Campaign, sealed: _Campaign) -> dict[str, Any]:
    count = len(sealed.seeds)
    if extended.seeds[:count] != sealed.seeds:
        raise CurrentTopologyConvergenceError(
            f"extended campaign does not preserve the sealed seed prefix: {_site(sealed)}"
        )
    extended_arrays = _scientific_shard_arrays(extended, count)
    sealed_arrays = _scientific_shard_arrays(sealed, count)
    for replica, (left, right) in enumerate(zip(extended_arrays, sealed_arrays, strict=True)):
        if set(left) != set(right):
            raise CurrentTopologyConvergenceError(
                f"scientific shard array names differ at sealed-prefix replica {replica}: {_site(sealed)}"
            )
        for name in left:
            same_bytes = (
                left[name].dtype.str == right[name].dtype.str
                and left[name].shape == right[name].shape
                and left[name].tobytes(order="C") == right[name].tobytes(order="C")
            )
            if not same_bytes:
                raise CurrentTopologyConvergenceError(
                    f"scientific sealed-prefix parity failed for {_site(sealed)} replica {replica} array {name}"
                )
    if _canonical(_load_diagnostics(extended, count)) != _canonical(_load_diagnostics(sealed, count)):
        raise CurrentTopologyConvergenceError(
            f"diagnostic sealed-prefix parity failed after timing removal: {_site(sealed)}"
        )
    return {
        "status": "pass",
        "replicas": count,
        "seeds": list(sealed.seeds),
        "rule": "every persisted shard array except timings is byte-value exact. Diagnostics are exact after timing removal",
    }


def _route_rows(campaign: _Campaign) -> list[dict[str, Any]]:
    fields = ("standpoint", "position_m", "ground_z_m", "body_yaw_deg", "point_kind", "route_distance_m")
    return [{name: row.get(name) for name in fields} for row in campaign.locations]


def _validate_pair(extended: _Campaign, sealed: _Campaign, expected_site: str) -> dict[str, Any]:
    if _site(extended) != expected_site or _site(sealed) != expected_site:
        raise CurrentTopologyConvergenceError(f"campaign site does not match mapping key {expected_site!r}")
    if extended.root == sealed.root:
        raise CurrentTopologyConvergenceError(
            f"extended and sealed campaigns must use different directories: {expected_site}"
        )
    _validate_current_contract(extended)
    _validate_current_contract(sealed)
    if extended.sampling != "iid" or sealed.sampling != "iid":
        raise CurrentTopologyConvergenceError(f"current-topology convergence requires IID campaigns: {expected_site}")
    if (
        extended.transport_topology != "first_material_interaction_v1"
        or sealed.transport_topology != extended.transport_topology
    ):
        raise CurrentTopologyConvergenceError(
            f"campaign topology is not current first-material interaction: {expected_site}"
        )
    if extended.components != sealed.components or extended.components != (
        "direct",
        "all_specular",
        "first_diffuse",
        "total",
    ):
        raise CurrentTopologyConvergenceError(f"campaign components differ from the current contract: {expected_site}")
    if extended.seeds != EXTENDED_SEEDS or extended.planned_seeds != EXTENDED_SEEDS:
        raise CurrentTopologyConvergenceError(f"extended campaign is not the complete seed 7..70 plan: {expected_site}")
    if sealed.seeds != SEALED_SEEDS or sealed.planned_seeds != SEALED_SEEDS:
        raise CurrentTopologyConvergenceError(
            f"sealed campaign is not the complete seed 7..22 package: {expected_site}"
        )
    if extended.convergence_looks != EXPECTED_LOOKS:
        raise CurrentTopologyConvergenceError(f"extended campaign has the wrong convergence looks: {expected_site}")
    if 16 not in sealed.convergence_looks:
        raise CurrentTopologyConvergenceError(f"sealed campaign does not contain look 16: {expected_site}")
    if extended.points != sealed.points or _canonical(_route_rows(extended)) != _canonical(_route_rows(sealed)):
        raise CurrentTopologyConvergenceError(f"route, standpoint order, or body yaw differs: {expected_site}")
    left, left_removed = _normalise_identity(extended)
    right, right_removed = _normalise_identity(sealed)
    if _canonical(left) != _canonical(right):
        raise CurrentTopologyConvergenceError(
            f"campaign common inputs or identity differ outside the plan allowlist: {expected_site}"
        )
    prefix = _prefix_parity(extended, sealed)
    return {
        "status": "pass",
        "identity_rule": "all identity and common-input fields are exact after removing only the declared plan fields",
        "identity_plan_allowlist": list(IDENTITY_PLAN_ALLOWLIST),
        "normalised_identity_sha256": hashlib.sha256(_canonical(left).encode()).hexdigest(),
        "removed_plan_fields": {"extended": left_removed, "sealed": right_removed},
        "sealed_prefix": prefix,
    }


def _db_change(current: np.ndarray | float, baseline: np.ndarray | float) -> np.ndarray:
    current_array, baseline_array = np.broadcast_arrays(
        np.asarray(current, dtype=np.float64), np.asarray(baseline, dtype=np.float64)
    )
    result = np.full(current_array.shape, np.nan, dtype=np.float64)
    positive = (current_array > 0.0) & (baseline_array > 0.0)
    result[positive] = 10.0 * np.log10(current_array[positive] / baseline_array[positive])
    return result


def _plain(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_plain(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _quantiles(values: np.ndarray) -> dict[str, float]:
    result = np.quantile(np.asarray(values, dtype=np.float64), QUANTILES)
    return {name: float(value) for name, value in zip(QUANTILE_NAMES, result, strict=True)}


def _bootstrap_indices(look: int, replicates: int, seed: int, label: str) -> np.ndarray:
    digest = hashlib.blake2b(label.encode(), digest_size=8, person=b"AEGIS_BOOT_v1").digest()
    label_seed = int.from_bytes(digest, "little")
    rng = np.random.default_rng(np.random.SeedSequence([seed, label_seed]))
    return rng.integers(0, look, size=(replicates, look))


def _bootstrap_quantiles(values: np.ndarray, indices: np.ndarray) -> dict[str, Any]:
    values = np.asarray(values, dtype=np.float64)
    samples = np.empty((indices.shape[0], len(QUANTILES)), dtype=np.float64)
    for start in range(0, indices.shape[0], 128):
        selected = indices[start : start + 128]
        means = np.mean(values[selected], axis=1)
        samples[start : start + len(selected)] = np.quantile(means, QUANTILES, axis=1).T
    estimate = _quantiles(np.mean(values, axis=0))
    result: dict[str, Any] = {}
    for index, name in enumerate(QUANTILE_NAMES):
        interval = np.quantile(samples[:, index], (0.025, 0.975))
        db_interval = _db_change(interval, estimate[name])
        result[name] = {
            "estimate": estimate[name],
            "percentile_interval_95": [float(value) for value in interval],
            "interval_relative_to_estimate_db": _plain(db_interval),
        }
    return result


def _metric_at_look(
    values: np.ndarray,
    look: int,
    baseline_values: np.ndarray,
    bootstrap_indices: np.ndarray,
) -> dict[str, Any]:
    mean = np.mean(values[:look], axis=0)
    baseline = np.mean(baseline_values[:16], axis=0)
    estimates = _quantiles(mean)
    baseline_quantiles = _quantiles(baseline)
    return {
        "route_quantiles": estimates,
        "change_from_sealed_16_db": {
            name: _plain(_db_change(estimates[name], baseline_quantiles[name]).item()) for name in QUANTILE_NAMES
        },
        "whole_replica_bootstrap": {
            "method": "percentile bootstrap resampling complete seed replicas across all standpoints together",
            "replicates": int(bootstrap_indices.shape[0]),
            "quantiles": _bootstrap_quantiles(values[:look], bootstrap_indices),
        },
    }


def _pointwise(values: np.ndarray, baseline_values: np.ndarray, look: int) -> dict[str, Any]:
    current = np.mean(values[:look], axis=0)
    baseline = np.mean(baseline_values[:16], axis=0)
    change = _db_change(current, baseline)
    finite = np.abs(change[np.isfinite(change)])
    return {
        "estimate": _plain(current),
        "sealed_16_estimate": _plain(baseline),
        "change_from_sealed_16_db": _plain(change),
        "p90_abs_change_db": None if finite.size == 0 else float(np.quantile(finite, 0.9)),
        "maximum_abs_change_db": None if finite.size == 0 else float(np.max(finite)),
        "zero_state_counts": {
            "both_zero": int(np.count_nonzero((current == 0.0) & (baseline == 0.0))),
            "current_only_positive": int(np.count_nonzero((current > 0.0) & (baseline == 0.0))),
            "sealed_only_positive": int(np.count_nonzero((current == 0.0) & (baseline > 0.0))),
        },
    }


def _timing(campaign: _Campaign) -> dict[str, Any]:
    looks: dict[str, Any] = {}
    for look in EXPECTED_LOOKS:
        fields: dict[str, Any] = {}
        for index, name in enumerate(TIMING_FIELDS):
            values = campaign.timings[:look, :, index]
            finite = values[np.isfinite(values)]
            fields[name] = {"observations": int(finite.size), "observed_total_seconds": float(np.sum(finite))}
        looks[str(look)] = {
            "fields": fields,
            "nonoverlapping_observed_compute_seconds": float(
                fields["estimator_wall_seconds"]["observed_total_seconds"]
                + fields["body_coupling_seconds"]["observed_total_seconds"]
            ),
        }
    return {
        "scope": "sum of persisted point-replica estimator wall time and body coupling time. Scene preparation excluded",
        "looks": looks,
    }


def _closure(campaign: _Campaign) -> dict[str, Any]:
    raw_total = campaign.raw_transfer[:, :, -1]
    raw_component_sum = np.sum(campaign.raw_transfer[:, :, :-1], axis=2)
    raw_residual = raw_total - raw_component_sum
    additive_indices = [BODY_METRICS.index(name) for name in ADDITIVE_BODY_METRICS]
    body_total = campaign.body_metrics[:, :, -1, additive_indices]
    body_component_sum = np.sum(campaign.body_metrics[:, :, :-1, :][:, :, :, additive_indices], axis=2)
    body_residual = body_total - body_component_sum
    raw_pass = bool(np.allclose(raw_total, raw_component_sum, rtol=2.0e-10, atol=1.0e-14))
    body_pass = bool(np.allclose(body_total, body_component_sum, rtol=2.0e-10, atol=1.0e-14))
    return {
        "status": "pass" if raw_pass and body_pass else "fail",
        "raw_transfer_max_abs_residual": float(np.max(np.abs(raw_residual))),
        "body_metric_max_abs_residual": float(np.max(np.abs(body_residual))),
        "raw_transfer_pass": raw_pass,
        "body_metrics_pass": body_pass,
        "additive_body_metrics_checked": list(ADDITIVE_BODY_METRICS),
        "nonadditive_body_metrics_excluded": {
            "peak_sab_w_m2": "the peak of a summed body field is not the sum of component-field peaks"
        },
    }


def _site_report(
    extended: _Campaign,
    sealed: _Campaign,
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    total_index = extended.components.index("total")
    direct_index = extended.components.index("direct")
    specular_index = extended.components.index("all_specular")
    wbsar_index = BODY_METRICS.index("sar_wb_w_kg")
    site = _site(extended)
    expected_shadow = SHADOW_STANDPOINTS.get(site, ())
    direct = extended.raw_transfer[:, :, direct_index]
    specular = extended.raw_transfer[:, :, specular_index]
    observed_shadow = tuple(
        index
        for index in range(extended.points)
        if np.all(direct[:, index] == 0.0) and np.all(specular[:, index] == 0.0)
    )
    if observed_shadow != expected_shadow:
        raise CurrentTopologyConvergenceError(
            f"shadow stratum differs from the declared six-point contract for {site}: {observed_shadow}"
        )
    looks: dict[str, Any] = {}
    for look in EXPECTED_LOOKS:
        indices = _bootstrap_indices(look, bootstrap_replicates, bootstrap_seed, f"{site}:{look}")
        components: dict[str, Any] = {}
        for component_index, component in enumerate(extended.components):
            components[component] = {
                "total_transfer_m_inv2": _metric_at_look(
                    extended.raw_transfer[:, :, component_index],
                    look,
                    sealed.raw_transfer[:, :, component_index],
                    indices,
                ),
                "wbsar_m2_per_kg": _metric_at_look(
                    extended.body_metrics[:, :, component_index, wbsar_index],
                    look,
                    sealed.body_metrics[:, :, component_index, wbsar_index],
                    indices,
                ),
            }
        looks[str(look)] = {
            "replicas": look,
            "seeds": list(extended.seeds[:look]),
            "components": components,
            "pointwise": {
                "total_transfer_m_inv2": _pointwise(
                    extended.raw_transfer[:, :, total_index], sealed.raw_transfer[:, :, total_index], look
                ),
                "wbsar_m2_per_kg": _pointwise(
                    extended.body_metrics[:, :, total_index, wbsar_index],
                    sealed.body_metrics[:, :, total_index, wbsar_index],
                    look,
                ),
            },
        }
    return {
        "campaigns": {
            "extended": {"directory": str(extended.root), "identity_sha256": extended.identity["sha256"]},
            "sealed_16": {"directory": str(sealed.root), "identity_sha256": sealed.identity["sha256"]},
        },
        "compatibility": _validate_pair(extended, sealed, site),
        "standpoints": extended.points,
        "shadow_standpoints": list(observed_shadow),
        "components": list(extended.components),
        "looks": looks,
        "timing": _timing(extended),
        "closure": {"extended": _closure(extended), "sealed_16": _closure(sealed)},
    }


def _pooled_stratum(
    campaigns: Mapping[str, _Campaign],
    sealed: Mapping[str, _Campaign],
    shadow: bool,
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    raw_values: list[np.ndarray] = []
    raw_baseline: list[np.ndarray] = []
    body_values: list[np.ndarray] = []
    body_baseline: list[np.ndarray] = []
    points: list[dict[str, Any]] = []
    wbsar_index = BODY_METRICS.index("sar_wb_w_kg")
    for site in EXPECTED_SITES:
        campaign = campaigns[site]
        baseline = sealed[site]
        selected_shadow = set(SHADOW_STANDPOINTS.get(site, ()))
        indices = [index for index in range(campaign.points) if (index in selected_shadow) == shadow]
        if not indices:
            continue
        total_index = campaign.components.index("total")
        raw_values.append(campaign.raw_transfer[:, indices, total_index])
        raw_baseline.append(baseline.raw_transfer[:, indices, total_index])
        body_values.append(campaign.body_metrics[:, indices, total_index, wbsar_index])
        body_baseline.append(baseline.body_metrics[:, indices, total_index, wbsar_index])
        points.extend({"site": site, "standpoint": index} for index in indices)
    raw = np.concatenate(raw_values, axis=1)
    raw_16 = np.concatenate(raw_baseline, axis=1)
    body = np.concatenate(body_values, axis=1)
    body_16 = np.concatenate(body_baseline, axis=1)
    looks: dict[str, Any] = {}
    for look in EXPECTED_LOOKS:
        indices = _bootstrap_indices(
            look,
            bootstrap_replicates,
            bootstrap_seed,
            f"pooled:{'shadow' if shadow else 'nonshadowed'}:{look}",
        )
        looks[str(look)] = {
            "total_transfer_m_inv2": _metric_at_look(raw, look, raw_16, indices),
            "wbsar_m2_per_kg": _metric_at_look(body, look, body_16, indices),
            "pointwise": {
                "total_transfer_m_inv2": _pointwise(raw, raw_16, look),
                "wbsar_m2_per_kg": _pointwise(body, body_16, look),
            },
        }
    return {"standpoints": len(points), "points": points, "looks": looks}


def _tail_status(criteria: Mapping[str, bool], rare: bool) -> str:
    if all(criteria.values()):
        return "stabilized_with_rare_event_behavior" if rare else "stabilized"
    return "rare_event_behavior" if rare else "remains_uncertain"


def _tail_assessment(site: str, campaign: _Campaign, site_report: dict[str, Any]) -> dict[str, Any]:
    shadow = SHADOW_STANDPOINTS.get(site, ())
    if not shadow:
        return {"status": "not_applicable", "reason": "the declared route has no fully shadowed standpoint"}
    total = site_report["looks"]
    q10_changes = {
        metric: abs(float(total["64"]["components"]["total"][metric]["change_from_sealed_16_db"]["q10"]))
        for metric in ("total_transfer_m_inv2", "wbsar_m2_per_kg")
    }
    q10_48 = {metric: total["48"]["components"]["total"][metric]["route_quantiles"]["q10"] for metric in q10_changes}
    q10_64 = {metric: total["64"]["components"]["total"][metric]["route_quantiles"]["q10"] for metric in q10_changes}
    movement = {metric: abs(float(_db_change(q10_64[metric], q10_48[metric]).item())) for metric in q10_changes}
    point_change = total["64"]["pointwise"]["wbsar_m2_per_kg"]["change_from_sealed_16_db"]
    look48 = np.mean(
        campaign.body_metrics[:48, list(shadow), campaign.components.index("total"), BODY_METRICS.index("sar_wb_w_kg")],
        axis=0,
    )
    look64 = np.mean(
        campaign.body_metrics[:64, list(shadow), campaign.components.index("total"), BODY_METRICS.index("sar_wb_w_kg")],
        axis=0,
    )
    shadow_movement = np.abs(_db_change(look64, look48))
    finite_shadow = shadow_movement[np.isfinite(shadow_movement)]
    interval = total["64"]["components"]["total"]["wbsar_m2_per_kg"]["whole_replica_bootstrap"]["quantiles"]["q10"][
        "percentile_interval_95"
    ]
    estimate = total["64"]["components"]["total"]["wbsar_m2_per_kg"]["route_quantiles"]["q10"]
    interval_db = _db_change(np.asarray(interval), estimate)
    interval_width = float(np.max(interval_db) - np.min(interval_db))
    diffuse = campaign.raw_transfer[:, list(shadow), campaign.components.index("first_diffuse")]
    positive = diffuse[diffuse > 0.0]
    rare_ratio = float(np.max(positive) / np.median(positive)) if positive.size else None
    criteria = {
        "q10_48_to_64": max(movement.values()) <= TAIL_THRESHOLDS["q10_48_to_64_abs_db"],
        "shadow_point_48_to_64": bool(finite_shadow.size)
        and float(np.max(finite_shadow)) <= TAIL_THRESHOLDS["shadow_point_48_to_64_max_abs_db"],
        "q10_bootstrap_width": interval_width <= TAIL_THRESHOLDS["q10_bootstrap_95_width_db"],
    }
    rare = rare_ratio is not None and rare_ratio >= TAIL_THRESHOLDS["rare_event_max_to_median_replica_ratio"]
    status = _tail_status(criteria, rare)
    return {
        "status": status,
        "rare_event_behavior": rare,
        "criteria_pass": criteria,
        "thresholds": TAIL_THRESHOLDS,
        "q10_change_from_sealed_16_abs_db": q10_changes,
        "q10_48_to_64_abs_db": movement,
        "shadow_point_48_to_64_max_abs_db": None if not finite_shadow.size else float(np.max(finite_shadow)),
        "q10_bootstrap_95_width_db": interval_width,
        "first_diffuse_replica_max_to_median_ratio": rare_ratio,
        "shadow_point_change_from_sealed_16_db": [point_change[index] for index in shadow],
    }


def compare_current_topology_campaigns(
    extended_directories: Mapping[str, str | Path],
    sealed_directories: Mapping[str, str | Path],
    *,
    bootstrap_replicates: int = 2000,
    bootstrap_seed: int = 20260814,
) -> dict[str, Any]:
    """Authenticate five extended campaigns and compare them with sealed look 16."""
    if tuple(sorted(extended_directories)) != tuple(sorted(EXPECTED_SITES)) or tuple(
        sorted(sealed_directories)
    ) != tuple(sorted(EXPECTED_SITES)):
        raise CurrentTopologyConvergenceError(
            f"both campaign mappings must contain exactly: {', '.join(EXPECTED_SITES)}"
        )
    if bootstrap_replicates < 100:
        raise CurrentTopologyConvergenceError("bootstrap_replicates must be at least 100")
    extended = {site: _load_campaign(extended_directories[site]) for site in EXPECTED_SITES}
    sealed = {site: _load_campaign(sealed_directories[site]) for site in EXPECTED_SITES}
    reports = {
        site: _site_report(extended[site], sealed[site], bootstrap_replicates, bootstrap_seed)
        for site in EXPECTED_SITES
    }
    closure_pass = all(
        campaign_report["closure"][kind]["status"] == "pass"
        for campaign_report in reports.values()
        for kind in ("extended", "sealed_16")
    )
    compatibility_pass = all(report["compatibility"]["status"] == "pass" for report in reports.values())
    tails = {site: _tail_assessment(site, extended[site], reports[site]) for site in SHADOW_STANDPOINTS}
    return {
        "schema": REPORT_SCHEMA,
        "contract": {
            "transport_topology": "first_material_interaction_v1",
            "route_contract": "provider_corridor_v1",
            "material_mode": "atlas",
            "reference_mode": "per_density_eirp",
            "frequency_hz": 15_000_000_000,
            "primary_rays": 200_000,
            "first_diffuse_output_cells": 4096,
            "body": {"phantom": "duke", "surface_elements": 56_024},
            "seeds": list(EXTENDED_SEEDS),
            "looks": list(EXPECTED_LOOKS),
            "shadow_stratum": {site: list(points) for site, points in SHADOW_STANDPOINTS.items()},
            "identity_plan_allowlist": list(IDENTITY_PLAN_ALLOWLIST),
            "tail_classification_thresholds": TAIL_THRESHOLDS,
            "bootstrap": {
                "method": "whole-replica percentile bootstrap",
                "replicates": bootstrap_replicates,
                "seed": bootstrap_seed,
            },
        },
        "authentication": {
            "status": "pass",
            "campaigns_authenticated": 10,
            "method": "identity wrapper, manifest, checkpoint, shard hash, schema, route, and seed checks",
        },
        "sites": reports,
        "strata": {
            "six_shadowed_points": _pooled_stratum(extended, sealed, True, bootstrap_replicates, bootstrap_seed),
            "67_nonshadowed_points": _pooled_stratum(extended, sealed, False, bootstrap_replicates, bootstrap_seed),
        },
        "lower_tail_assessment": tails,
        "promotion_gates": {
            "all_manifests_and_identities_pass": "pass",
            "common_inputs_and_sealed_prefix_exact": "pass" if compatibility_pass else "fail",
            "component_closure_pass": "pass" if closure_pass else "fail",
            "interpretation_clearly_stronger": "requires_author_judgment",
            "manuscript_update_without_added_complexity": "requires_author_judgment",
            "decision": "not_promoted_pending_author_judgment",
        },
    }


def _write_csv(path: Path, report: dict[str, Any]) -> None:
    fields = (
        "record_type",
        "site",
        "look",
        "component",
        "metric",
        "quantile",
        "standpoint",
        "stratum",
        "estimate",
        "sealed_16_estimate",
        "change_from_sealed_16_db",
        "bootstrap_95_low",
        "bootstrap_95_high",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for site, site_report in report["sites"].items():
            shadow = set(site_report["shadow_standpoints"])
            for look, look_report in site_report["looks"].items():
                for component, component_report in look_report["components"].items():
                    for metric, metric_report in component_report.items():
                        for quantile in QUANTILE_NAMES:
                            boot = metric_report["whole_replica_bootstrap"]["quantiles"][quantile]
                            writer.writerow(
                                {
                                    "record_type": "route_quantile",
                                    "site": site,
                                    "look": look,
                                    "component": component,
                                    "metric": metric,
                                    "quantile": quantile,
                                    "estimate": metric_report["route_quantiles"][quantile],
                                    "change_from_sealed_16_db": metric_report["change_from_sealed_16_db"][quantile],
                                    "bootstrap_95_low": boot["percentile_interval_95"][0],
                                    "bootstrap_95_high": boot["percentile_interval_95"][1],
                                }
                            )
                for metric, point_report in look_report["pointwise"].items():
                    for standpoint, estimate in enumerate(point_report["estimate"]):
                        writer.writerow(
                            {
                                "record_type": "pointwise",
                                "site": site,
                                "look": look,
                                "component": "total",
                                "metric": metric,
                                "standpoint": standpoint,
                                "stratum": "shadow" if standpoint in shadow else "nonshadowed",
                                "estimate": estimate,
                                "sealed_16_estimate": point_report["sealed_16_estimate"][standpoint],
                                "change_from_sealed_16_db": point_report["change_from_sealed_16_db"][standpoint],
                            }
                        )


def _plot(report: dict[str, Any], pdf: Path, png: Path) -> None:
    import matplotlib.pyplot as plt

    display_names = {
        "korenmarkt": "Korenmarkt",
        "prague_staromestske": "Prague",
        "madrid_plazamayor": "Madrid",
        "mexico_zocalo": "Mexico City",
        "tokyo_hachiko": "Tokyo Hachiko",
    }
    colors = ("#0072B2", "#009E73", "#CC79A7", "#D55E00", "#E69F00")
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.9), constrained_layout=True)
    looks = np.asarray(EXPECTED_LOOKS)
    for color, site in zip(colors, EXPECTED_SITES, strict=True):
        changes = [
            report["sites"][site]["looks"][str(look)]["components"]["total"]["wbsar_m2_per_kg"][
                "change_from_sealed_16_db"
            ]["q10"]
            for look in looks
        ]
        axes[0].plot(looks, changes, marker="o", markersize=3, color=color, label=display_names[site])
    axes[0].axhline(0.0, color="0.65", linewidth=0.8)
    axes[0].set(xlabel="Replica look", ylabel="wbSAR q10 change from sealed 16 (dB)")
    axes[0].set_title("(a) Route lower-tail movement", loc="left", fontsize=9)
    axes[0].legend(frameon=False, fontsize=6.6, ncol=2)

    for color, site in zip(("#D55E00", "#E69F00"), SHADOW_STANDPOINTS, strict=True):
        indices = SHADOW_STANDPOINTS[site]
        maxima = [0.0]
        for previous, look in zip(looks[:-1], looks[1:], strict=True):
            before = report["sites"][site]["looks"][str(previous)]["pointwise"]["wbsar_m2_per_kg"]["estimate"]
            after = report["sites"][site]["looks"][str(look)]["pointwise"]["wbsar_m2_per_kg"]["estimate"]
            changes = [abs(10.0 * np.log10(after[index] / before[index])) for index in indices]
            maxima.append(max(changes))
        axes[1].plot(looks, maxima, marker="s", markersize=3, color=color, label=display_names[site])
    axes[1].axhline(0.0, color="0.65", linewidth=0.8)
    axes[1].set(xlabel="Replica look", ylabel="Maximum stepwise shadow-point wbSAR change (dB)")
    axes[1].set_title("(b) Explicit six-point stratum", loc="left", fontsize=9)
    axes[1].legend(frameon=False, fontsize=7)
    for axis in axes:
        axis.set_xticks(looks)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color="0.9", linewidth=0.6)
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _artifact_record(path: Path) -> dict[str, Any]:
    return {"path": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}


def write_current_topology_convergence(
    extended_directories: Mapping[str, str | Path],
    sealed_directories: Mapping[str, str | Path],
    output_directory: str | Path,
    *,
    bootstrap_replicates: int = 2000,
    bootstrap_seed: int = 20260814,
) -> CurrentTopologyConvergenceArtifacts:
    """Write authenticated JSON, CSV, PDF, PNG, and manifest artifacts."""
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    artifacts = CurrentTopologyConvergenceArtifacts(
        json=output / "current_topology_convergence.json",
        csv=output / "current_topology_convergence.csv",
        pdf=output / "current_topology_convergence.pdf",
        png=output / "current_topology_convergence.png",
        manifest=output / "current_topology_convergence_manifest.json",
    )
    report = compare_current_topology_campaigns(
        extended_directories,
        sealed_directories,
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
    )
    artifacts.json.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    _write_csv(artifacts.csv, report)
    _plot(report, artifacts.pdf, artifacts.png)
    sources = []
    for kind, directories in (("extended", extended_directories), ("sealed_16", sealed_directories)):
        for site in EXPECTED_SITES:
            root = Path(directories[site]).resolve()
            identity = json.loads((root / "campaign_identity.json").read_text(encoding="utf-8"))
            sources.append(
                {
                    "kind": kind,
                    "site": site,
                    "directory": str(root),
                    "identity_sha256": identity["sha256"],
                    "manifest_sha256": _sha256(root / "manifest.json"),
                }
            )
    manifest = {
        "schema": ARTIFACT_SCHEMA,
        "configuration": report["contract"],
        "source_campaigns": sources,
        "reporter": {"path": Path(__file__).name, "sha256": _sha256(Path(__file__))},
        "files": [_artifact_record(path) for path in (artifacts.json, artifacts.csv, artifacts.pdf, artifacts.png)],
    }
    artifacts.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return artifacts


__all__ = [
    "EXPECTED_LOOKS",
    "EXPECTED_SITES",
    "EXTENDED_SEEDS",
    "IDENTITY_PLAN_ALLOWLIST",
    "SHADOW_STANDPOINTS",
    "CurrentTopologyConvergenceArtifacts",
    "CurrentTopologyConvergenceError",
    "compare_current_topology_campaigns",
    "write_current_topology_convergence",
]
