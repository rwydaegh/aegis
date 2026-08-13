"""Report a paired atlas evidence layer versus geometric fallback campaign.

The reporter accepts completed roofline campaigns only. It authenticates every
campaign artifact through the production campaign loader, then applies a
closed identity allowlist. Geometry, route, source measure, random seeds,
transport topology, body model, and numerical budgets must remain identical.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from semantic_twin.exposure.roofline_campaign import BODY_METRICS, TIMING_FIELDS
from semantic_twin.report.roofline_campaign_comparison import (
    CampaignComparisonError,
    _OPTIONAL_ALL_SPECULAR_KEYS,
    _OPTIONAL_SUFFIX_KEYS,
    _Campaign,
    _check_manifest_completeness,
    _check_manifest_files,
    _document_components,
    _identity_wrapper_hash,
    _is_sha256,
    _json_read,
    _load_optional_from_diagnostics,
    _load_shard,
    _required_path,
    _validate_campaign_metadata,
)

REPORT_SCHEMA = "material_evidence_ablation_v1"
ABLATION_LABEL = "atlas evidence layer versus geometric fallback"
QUANTILES = (0.1, 0.5, 0.9)
QUANTILE_NAMES = ("q10", "q50", "q90")

# These are the only identity locations that may differ. ``/materials`` and
# ``/transport/tracer/atlas_material`` are explicit sealed subtrees because
# their leaf schemas depend on the material binding implementation.
IDENTITY_ALLOWLIST = (
    "/configuration/material_mode",
    "/materials",
    "/transport/tracer/atlas_material",
    "/transport/tracer/face_class_sha256",
    "/transport/tracer/permittivity_sha256",
    "/transport/tracer/rms_height_sha256",
    "/transport/estimator/configuration/specular_transport/material_class_sha256",
    "/inputs/bytes",
    "/inputs/file_count",
    "/inputs/files[run_config]",
    "/inputs/files[atlas_npz]",
    "/inputs/files[atlas_json]",
)


class MaterialEvidenceAblationError(CampaignComparisonError):
    """The two campaigns do not form the declared material ablation."""


@dataclass(frozen=True)
class MaterialAblationArtifacts:
    """Paths written by :func:`write_material_evidence_ablation`."""

    json: Path
    csv: Path
    pdf: Path
    png: Path
    manifest: Path


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _configuration(campaign: _Campaign) -> dict[str, Any]:
    value = campaign.identity_data.get("configuration")
    if not isinstance(value, dict):
        raise MaterialEvidenceAblationError("campaign identity has no configuration object")
    return value


def _sampling_mode(identity_data: dict[str, Any]) -> str:
    transport = identity_data.get("transport")
    tracer = transport.get("tracer") if isinstance(transport, dict) else None
    configuration = tracer.get("configuration") if isinstance(tracer, dict) else None
    if not isinstance(configuration, dict):
        raise MaterialEvidenceAblationError("campaign identity does not seal tracer configuration")
    mode = configuration.get("launch_sampling", "iid")
    if mode not in ("iid", "rotated_fibonacci"):
        raise MaterialEvidenceAblationError(f"unknown launch sampling mode: {mode!r}")
    return str(mode)


def _load_material_campaign(path: str | Path) -> _Campaign:
    """Load one campaign without applying the sampler-pair filename rule.

    The shared report loader authenticates a legacy IID versus Fibonacci pair
    by finding a config filename for each launch mode. A material control uses
    an IID geometric-control filename instead. This loader retains every
    artifact, schema, shard, seed, and route check from that implementation and
    leaves run-config comparison to this module's closed material allowlist.
    """
    root = Path(path).resolve()
    if not root.is_dir():
        raise MaterialEvidenceAblationError(f"campaign output directory does not exist: {root}")
    identity = _json_read(_required_path(root, "campaign_identity.json"))
    identity_data = identity.get("data")
    if not isinstance(identity_data, dict):
        raise MaterialEvidenceAblationError(f"campaign identity has no data object: {root}")
    identity_hash = identity.get("sha256")
    if not _is_sha256(identity_hash) or identity_hash != _identity_wrapper_hash(identity_data):
        raise MaterialEvidenceAblationError(f"campaign identity SHA-256 wrapper is invalid: {root}")
    sampling = _sampling_mode(identity_data)
    manifest = _json_read(_required_path(root, "manifest.json"))
    if manifest.get("identity_sha256") != identity_hash:
        raise MaterialEvidenceAblationError(f"manifest and campaign identity disagree in {root}")
    _check_manifest_files(root, manifest)
    summary = _json_read(_required_path(root, "summary.json"))
    checkpoint = _json_read(_required_path(root / "checkpoint", "index.json"))
    if checkpoint.get("identity_sha256") != identity_hash:
        raise MaterialEvidenceAblationError(f"checkpoint and campaign identity disagree in {root}")
    components = _document_components(root, identity_data, manifest, summary, checkpoint)
    _check_manifest_completeness(root, manifest, checkpoint)
    seeds, points, locations, committed = _validate_campaign_metadata(
        root, identity_data, checkpoint, summary, components
    )

    shards = [_load_shard(root, entry, points, len(components)) for entry in committed]
    raw_parts = [shard.raw for shard in shards]
    body_parts = [shard.body for shard in shards]
    timing_parts = [shard.timing for shard in shards]
    diagnostic_parts = [shard.diagnostics for shard in shards]
    all_optional = [shard.all_specular for shard in shards]
    suffix_optional = [shard.suffix for shard in shards]
    all_specular = None if any(item is None for item in all_optional) else np.stack(all_optional)
    suffix_transfer = None if any(item is None for item in suffix_optional) else np.stack(suffix_optional)
    if all_specular is None and "all_specular" in components:
        all_specular = np.asarray(raw_parts, dtype=np.float64)[:, :, components.index("all_specular")]
    elif all_specular is None:
        suffix_enabled = any(
            bool(item.get("sampled_specular_suffix", {}).get("enabled", False))
            for replica in diagnostic_parts
            for item in replica
            if isinstance(item.get("sampled_specular_suffix"), dict)
        )
        estimator = identity_data.get("transport", {}).get("estimator", {}).get("configuration", {})
        if not suffix_enabled and estimator.get("specular_suffix_mode", "exact") == "disabled":
            all_specular = np.asarray(raw_parts, dtype=np.float64)[:, :, components.index("specular")]
        else:
            all_specular = _load_optional_from_diagnostics(
                [list(replica) for replica in diagnostic_parts],
                _OPTIONAL_ALL_SPECULAR_KEYS,
                points,
            )
    if suffix_transfer is None:
        suffix_transfer = _load_optional_from_diagnostics(
            [list(replica) for replica in diagnostic_parts],
            _OPTIONAL_SUFFIX_KEYS,
            points,
        )
    return _Campaign(
        root,
        identity,
        identity_data,
        sampling,
        manifest,
        checkpoint,
        seeds,
        points,
        tuple(locations),
        np.stack(raw_parts),
        np.stack(body_parts),
        np.stack(timing_parts),
        tuple(diagnostic_parts),
        all_specular,
        suffix_transfer,
    )


# Kept as the narrow injection boundary used by focused tests. It deliberately
# points to the material-specific loader, not the legacy sampler-pair loader.
_load_campaign = _load_material_campaign


def _input_records(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    inputs = data.get("inputs")
    if not isinstance(inputs, dict) or not isinstance(inputs.get("files"), list):
        raise MaterialEvidenceAblationError("campaign identity inputs.files must be a list")
    records = inputs["files"]
    if not all(isinstance(record, dict) and isinstance(record.get("path"), str) for record in records):
        raise MaterialEvidenceAblationError("campaign identity contains an invalid input record")
    return inputs, records


def _run_config_record(path: str, site: str, mode: str) -> bool:
    name = Path(path).name
    prefix = f"roofline_campaign_{site}_"
    if not path.startswith("config/") or not name.startswith(prefix):
        return False
    if mode == "atlas":
        return name.endswith("_iid.json") and "geometric_control" not in name
    return name.endswith("_iid_geometric_control.json")


def _atlas_input_kind(path: str, site: str) -> str | None:
    prefix = f"outputs/site_semantics/{site}/joint_atlas_"
    if not path.startswith(prefix):
        return None
    if path.endswith(".npz"):
        return "atlas_npz"
    if path.endswith(".json"):
        return "atlas_json"
    return None


def _normalise_identity(campaign: _Campaign, expected_mode: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = copy.deepcopy(campaign.identity_data)
    configuration = data.get("configuration")
    if not isinstance(configuration, dict) or configuration.get("material_mode") != expected_mode:
        raise MaterialEvidenceAblationError(f"expected {expected_mode!r} material_mode in {campaign.root}")
    site = configuration.get("site")
    if not isinstance(site, str) or not site:
        raise MaterialEvidenceAblationError("campaign identity has no site")
    configuration.pop("material_mode")
    data.pop("materials", None)

    transport = data.get("transport")
    tracer = transport.get("tracer") if isinstance(transport, dict) else None
    estimator = transport.get("estimator") if isinstance(transport, dict) else None
    if not isinstance(tracer, dict) or not isinstance(estimator, dict):
        raise MaterialEvidenceAblationError("campaign identity has no sealed tracer and estimator")
    for key in ("atlas_material", "face_class_sha256", "permittivity_sha256", "rms_height_sha256"):
        tracer.pop(key, None)
    specular = estimator.get("configuration", {}).get("specular_transport")
    if not isinstance(specular, dict):
        raise MaterialEvidenceAblationError("campaign identity has no sealed specular transport")
    specular.pop("material_class_sha256", None)

    inputs, records = _input_records(data)
    retained: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    run_configs = 0
    atlas_kinds: list[str] = []
    for record in records:
        path = str(record["path"])
        if _run_config_record(path, site, expected_mode):
            run_configs += 1
            removed.append({"allowlist_path": "/inputs/files[run_config]", **record})
            continue
        atlas_kind = _atlas_input_kind(path, site)
        if expected_mode == "atlas" and atlas_kind is not None:
            atlas_kinds.append(atlas_kind)
            removed.append({"allowlist_path": f"/inputs/files[{atlas_kind}]", **record})
            continue
        retained.append(record)
    if run_configs != 1:
        raise MaterialEvidenceAblationError(f"{campaign.root} must seal exactly one mode-specific roofline run config")
    expected_atlas = ["atlas_json", "atlas_npz"] if expected_mode == "atlas" else []
    if sorted(atlas_kinds) != expected_atlas:
        raise MaterialEvidenceAblationError(
            f"atlas campaign must seal one atlas JSON and one atlas NPZ input: {campaign.root}"
        )
    inputs["files"] = sorted(retained, key=lambda item: str(item["path"]))
    inputs.pop("bytes", None)
    inputs.pop("file_count", None)
    return data, removed


def _different_paths(left: Any, right: Any, path: str = "") -> list[str]:
    if type(left) is not type(right):
        return [path or "/"]
    if isinstance(left, dict):
        result: list[str] = []
        for key in sorted(set(left) | set(right)):
            child = f"{path}/{key}"
            if key not in left or key not in right:
                result.append(child)
            else:
                result.extend(_different_paths(left[key], right[key], child))
        return result
    if isinstance(left, list):
        if len(left) != len(right):
            return [path]
        result = []
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            result.extend(_different_paths(a, b, f"{path}/{index}"))
        return result
    return [] if left == right else [path or "/"]


def _route_rows(campaign: _Campaign) -> list[dict[str, Any]]:
    """Return only persisted route identity, excluding campaign results."""
    fields = (
        "standpoint",
        "position_m",
        "ground_z_m",
        "body_yaw_deg",
        "point_kind",
        "route_distance_m",
    )
    return [{name: row.get(name) for name in fields} for row in campaign.locations]


def _validate_pair(atlas: _Campaign, geometric: _Campaign) -> dict[str, Any]:
    if atlas.sampling != "iid" or geometric.sampling != "iid":
        raise MaterialEvidenceAblationError("material ablation requires IID campaigns")
    if atlas.seeds != geometric.seeds or atlas.planned_seeds != geometric.planned_seeds:
        raise MaterialEvidenceAblationError("campaign seeds are not paired exactly")
    if atlas.components != geometric.components or atlas.transport_topology != geometric.transport_topology:
        raise MaterialEvidenceAblationError("campaign component or transport topology differs")
    if atlas.points != geometric.points:
        raise MaterialEvidenceAblationError("campaign route lengths differ")
    if _canonical(_route_rows(atlas)) != _canonical(_route_rows(geometric)):
        raise MaterialEvidenceAblationError("campaign route position, ground, yaw, or order differs")

    atlas_normal, atlas_removed = _normalise_identity(atlas, "atlas")
    geometric_normal, geometric_removed = _normalise_identity(geometric, "geometric")
    differences = _different_paths(atlas_normal, geometric_normal)
    if differences:
        preview = ", ".join(differences[:12])
        raise MaterialEvidenceAblationError(f"campaign identity differs outside the material allowlist: {preview}")
    canonical = _canonical(atlas_normal).encode("utf-8")
    return {
        "status": "pass",
        "rule": "all identity fields are exact after removing only the listed material paths",
        "allowlist": list(IDENTITY_ALLOWLIST),
        "observed_allowlisted_input_records": {
            "atlas": atlas_removed,
            "geometric": geometric_removed,
        },
        "shared_identity_sha256": _sha256_bytes(canonical),
    }


def _quantiles(values: np.ndarray) -> dict[str, float] | None:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return None
    result = np.quantile(finite, QUANTILES)
    return {name: float(value) for name, value in zip(QUANTILE_NAMES, result, strict=True)}


def _db_change(atlas: np.ndarray, geometric: np.ndarray) -> np.ndarray:
    atlas = np.asarray(atlas, dtype=np.float64)
    geometric = np.asarray(geometric, dtype=np.float64)
    result = np.full(np.broadcast_shapes(atlas.shape, geometric.shape), np.nan, dtype=np.float64)
    positive = (atlas > 0.0) & (geometric > 0.0)
    result[positive] = 10.0 * np.log10(atlas[positive] / geometric[positive])
    return result


def _metric_summary(atlas: np.ndarray, geometric: np.ndarray) -> dict[str, Any]:
    atlas = np.asarray(atlas, dtype=np.float64)
    geometric = np.asarray(geometric, dtype=np.float64)
    atlas_q = _quantiles(atlas)
    geometric_q = _quantiles(geometric)
    if atlas_q is None or geometric_q is None:
        raise MaterialEvidenceAblationError("metric has no finite route values")
    quantile_change = {
        name: (
            float(10.0 * np.log10(atlas_q[name] / geometric_q[name]))
            if atlas_q[name] > 0.0 and geometric_q[name] > 0.0
            else None
        )
        for name in QUANTILE_NAMES
    }
    delta = _db_change(atlas, geometric)
    return {
        "route_quantiles": {"atlas": atlas_q, "geometric": geometric_q},
        "route_quantile_change_db": quantile_change,
        "pointwise_change_db_quantiles": _quantiles(delta),
        "pointwise_finite_db_count": int(np.count_nonzero(np.isfinite(delta))),
        "pointwise_zero_states": {
            "both_zero": int(np.count_nonzero((atlas == 0.0) & (geometric == 0.0))),
            "atlas_only_positive": int(np.count_nonzero((atlas > 0.0) & (geometric == 0.0))),
            "geometric_only_positive": int(np.count_nonzero((atlas == 0.0) & (geometric > 0.0))),
        },
    }


def _seed_uncertainty(atlas: np.ndarray, geometric: np.ndarray) -> dict[str, Any]:
    replicas = atlas.shape[0]
    if replicas < 2 or atlas.shape != geometric.shape:
        return {"status": "unavailable", "reason": "at least two exactly paired replica shards are required"}
    quantile_changes: dict[str, Any] = {}
    for quantile, name in zip(QUANTILES, QUANTILE_NAMES, strict=True):
        atlas_values = np.quantile(atlas, quantile, axis=1)
        geometric_values = np.quantile(geometric, quantile, axis=1)
        changes = _db_change(atlas_values, geometric_values)
        finite = changes[np.isfinite(changes)]
        if finite.size < 2:
            quantile_changes[name] = {"status": "unavailable", "finite_pairs": int(finite.size)}
            continue
        quantile_changes[name] = {
            "status": "available",
            "paired_seed_mean_db": float(np.mean(finite)),
            "paired_seed_standard_error_db": float(np.std(finite, ddof=1) / np.sqrt(finite.size)),
            "paired_seed_percentile_interval_95_db": [float(value) for value in np.quantile(finite, (0.025, 0.975))],
            "finite_pairs": int(finite.size),
        }
    return {
        "status": "available",
        "method": "paired complete-route replica shards with common seed identifiers",
        "replicas": replicas,
        "route_quantile_change": quantile_changes,
    }


def _strata(direct_atlas: np.ndarray, direct_geometric: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "direct_visible_in_both": (direct_atlas > 0.0) & (direct_geometric > 0.0),
        "zero_direct_in_both": (direct_atlas == 0.0) & (direct_geometric == 0.0),
        "atlas_only_direct_visible": (direct_atlas > 0.0) & (direct_geometric == 0.0),
        "geometric_only_direct_visible": (direct_atlas == 0.0) & (direct_geometric > 0.0),
    }


def _timing_summary(campaign: _Campaign) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for index, name in enumerate(TIMING_FIELDS):
        values = campaign.timings[:, :, index]
        finite = values[np.isfinite(values)]
        fields[name] = {
            "observations": int(finite.size),
            "observed_total_seconds": float(np.sum(finite)),
        }
    estimator = fields["estimator_wall_seconds"]["observed_total_seconds"]
    body = fields["body_coupling_seconds"]["observed_total_seconds"]
    return {
        "fields": fields,
        "nonoverlapping_observed_compute_seconds": float(estimator + body),
        "scope": "sum of estimator wall time and body coupling over persisted point-replica shards",
    }


def compare_material_campaigns(atlas_directory: str | Path, geometric_directory: str | Path) -> dict[str, Any]:
    """Authenticate and compare one atlas and one geometric campaign."""
    atlas = _load_campaign(atlas_directory)
    geometric = _load_campaign(geometric_directory)
    compatibility = _validate_pair(atlas, geometric)

    total_index = atlas.components.index("total")
    direct_index = atlas.components.index("direct")
    wbsar_index = BODY_METRICS.index("sar_wb_w_kg")
    raw_mean_atlas = np.mean(atlas.raw_transfer, axis=0)
    raw_mean_geometric = np.mean(geometric.raw_transfer, axis=0)
    body_mean_atlas = np.mean(atlas.body_metrics, axis=0)
    body_mean_geometric = np.mean(geometric.body_metrics, axis=0)
    total_atlas = raw_mean_atlas[:, total_index]
    total_geometric = raw_mean_geometric[:, total_index]
    wbsar_atlas = body_mean_atlas[:, total_index, wbsar_index]
    wbsar_geometric = body_mean_geometric[:, total_index, wbsar_index]

    components: dict[str, Any] = {}
    for index, component in enumerate(atlas.components):
        components[component] = {
            "total_transfer_m_inv2": _metric_summary(raw_mean_atlas[:, index], raw_mean_geometric[:, index]),
            "wbsar_m2_per_kg": _metric_summary(
                body_mean_atlas[:, index, wbsar_index], body_mean_geometric[:, index, wbsar_index]
            ),
        }

    direct_atlas = raw_mean_atlas[:, direct_index]
    direct_geometric = raw_mean_geometric[:, direct_index]
    strata: dict[str, Any] = {}
    masks = _strata(direct_atlas, direct_geometric)
    for name, mask in masks.items():
        strata[name] = {
            "standpoints": int(np.count_nonzero(mask)),
            "indices": np.flatnonzero(mask).astype(int).tolist(),
            "total_transfer_m_inv2": _metric_summary(total_atlas[mask], total_geometric[mask])
            if np.any(mask)
            else None,
            "wbsar_m2_per_kg": _metric_summary(wbsar_atlas[mask], wbsar_geometric[mask]) if np.any(mask) else None,
        }

    atlas_timing = _timing_summary(atlas)
    geometric_timing = _timing_summary(geometric)
    denominator = geometric_timing["nonoverlapping_observed_compute_seconds"]
    timing = {
        "atlas": atlas_timing,
        "geometric": geometric_timing,
        "atlas_to_geometric_compute_ratio": (
            atlas_timing["nonoverlapping_observed_compute_seconds"] / denominator if denominator > 0.0 else None
        ),
    }

    distances = np.zeros(atlas.points, dtype=np.float64)
    positions = np.asarray([row["position_m"] for row in atlas.locations], dtype=np.float64)
    if atlas.points > 1:
        distances[1:] = np.cumsum(np.linalg.norm(np.diff(positions, axis=0), axis=1))
    point_records = []
    total_delta = _db_change(total_atlas, total_geometric)
    wbsar_delta = _db_change(wbsar_atlas, wbsar_geometric)
    for point in range(atlas.points):
        stratum = next(name for name, mask in masks.items() if mask[point])
        point_records.append(
            {
                "standpoint": point,
                "route_distance_m": float(distances[point]),
                "direct_stratum": stratum,
                "total_transfer_m_inv2": {
                    "atlas": float(total_atlas[point]),
                    "geometric": float(total_geometric[point]),
                    "change_db": float(total_delta[point]) if np.isfinite(total_delta[point]) else None,
                },
                "wbsar_m2_per_kg": {
                    "atlas": float(wbsar_atlas[point]),
                    "geometric": float(wbsar_geometric[point]),
                    "change_db": float(wbsar_delta[point]) if np.isfinite(wbsar_delta[point]) else None,
                },
            }
        )

    return {
        "schema": REPORT_SCHEMA,
        "ablation": ABLATION_LABEL,
        "interpretation": (
            "This is a paired model-layer sensitivity. It is not a reflectance-only test and does not measure accuracy."
        ),
        "site": _configuration(atlas)["site"],
        "campaigns": {
            "atlas": {"directory": str(atlas.root), "identity_sha256": atlas.identity["sha256"]},
            "geometric": {"directory": str(geometric.root), "identity_sha256": geometric.identity["sha256"]},
        },
        "compatibility": compatibility,
        "standpoints": atlas.points,
        "seeds": list(atlas.seeds),
        "components": list(atlas.components),
        "metrics": {
            "total_transfer_m_inv2": _metric_summary(total_atlas, total_geometric),
            "wbsar_m2_per_kg": _metric_summary(wbsar_atlas, wbsar_geometric),
        },
        "component_decomposition": components,
        "direct_strata": strata,
        "paired_seed_uncertainty": {
            "total_transfer_m_inv2": _seed_uncertainty(
                atlas.raw_transfer[:, :, total_index], geometric.raw_transfer[:, :, total_index]
            ),
            "wbsar_m2_per_kg": _seed_uncertainty(
                atlas.body_metrics[:, :, total_index, wbsar_index],
                geometric.body_metrics[:, :, total_index, wbsar_index],
            ),
        },
        "timing": timing,
        "points": point_records,
    }


def _write_csv(path: Path, report: dict[str, Any]) -> None:
    fields = (
        "site",
        "standpoint",
        "route_distance_m",
        "direct_stratum",
        "atlas_total_transfer_m_inv2",
        "geometric_total_transfer_m_inv2",
        "total_transfer_change_db",
        "atlas_wbsar_m2_per_kg",
        "geometric_wbsar_m2_per_kg",
        "wbsar_change_db",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for point in report["points"]:
            transfer = point["total_transfer_m_inv2"]
            wbsar = point["wbsar_m2_per_kg"]
            writer.writerow(
                {
                    "site": report["site"],
                    "standpoint": point["standpoint"],
                    "route_distance_m": point["route_distance_m"],
                    "direct_stratum": point["direct_stratum"],
                    "atlas_total_transfer_m_inv2": transfer["atlas"],
                    "geometric_total_transfer_m_inv2": transfer["geometric"],
                    "total_transfer_change_db": transfer["change_db"],
                    "atlas_wbsar_m2_per_kg": wbsar["atlas"],
                    "geometric_wbsar_m2_per_kg": wbsar["geometric"],
                    "wbsar_change_db": wbsar["change_db"],
                }
            )


def _plot(report: dict[str, Any], pdf: Path, png: Path) -> None:
    import matplotlib.pyplot as plt

    points = report["points"]
    distance = np.asarray([point["route_distance_m"] for point in points])
    transfer = np.asarray(
        [
            np.nan
            if point["total_transfer_m_inv2"]["change_db"] is None
            else point["total_transfer_m_inv2"]["change_db"]
            for point in points
        ]
    )
    wbsar = np.asarray(
        [
            np.nan if point["wbsar_m2_per_kg"]["change_db"] is None else point["wbsar_m2_per_kg"]["change_db"]
            for point in points
        ]
    )
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.85), constrained_layout=True)
    axes[0].axhline(0.0, color="0.65", linewidth=0.8)
    axes[0].plot(distance, transfer, color="#0072B2", marker="o", markersize=3.3, label="Transfer")
    axes[0].plot(distance, wbsar, color="#D55E00", marker="s", markersize=3.0, label="Whole-body SAR")
    axes[0].set(xlabel="Route distance (m)", ylabel="Atlas / geometric change (dB)")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].set_title("(a) Pointwise paired change", loc="left", fontsize=9)

    components = report["components"]
    x = np.arange(len(components))
    transfer_median = [
        report["component_decomposition"][name]["total_transfer_m_inv2"]["pointwise_change_db_quantiles"]
        for name in components
    ]
    wbsar_median = [
        report["component_decomposition"][name]["wbsar_m2_per_kg"]["pointwise_change_db_quantiles"]
        for name in components
    ]
    transfer_median = [np.nan if value is None else value["q50"] for value in transfer_median]
    wbsar_median = [np.nan if value is None else value["q50"] for value in wbsar_median]
    width = 0.36
    axes[1].axhline(0.0, color="0.65", linewidth=0.8)
    axes[1].bar(x - width / 2, transfer_median, width, color="#0072B2", label="Transfer")
    axes[1].bar(x + width / 2, wbsar_median, width, color="#D55E00", label="Whole-body SAR")
    axes[1].set_xticks(
        x,
        [name.replace("all_specular", "specular").replace("first_diffuse", "diffuse") for name in components],
        rotation=24,
        ha="right",
    )
    axes[1].set_ylabel("Median paired change (dB)")
    axes[1].set_title("(b) Transport components", loc="left", fontsize=9)
    axes[1].legend(frameon=False, fontsize=8)
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color="0.9", linewidth=0.6)
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _artifact_record(path: Path) -> dict[str, Any]:
    return {"path": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}


def write_material_evidence_ablation(
    atlas_directory: str | Path,
    geometric_directory: str | Path,
    output_directory: str | Path,
) -> MaterialAblationArtifacts:
    """Write authenticated JSON, CSV, PDF, PNG, and manifest artifacts."""
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    artifacts = MaterialAblationArtifacts(
        json=output / "material_evidence_ablation.json",
        csv=output / "material_evidence_ablation.csv",
        pdf=output / "material_evidence_ablation.pdf",
        png=output / "material_evidence_ablation.png",
        manifest=output / "material_evidence_ablation_manifest.json",
    )
    report = compare_material_campaigns(atlas_directory, geometric_directory)
    artifacts.json.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    _write_csv(artifacts.csv, report)
    _plot(report, artifacts.pdf, artifacts.png)
    manifest = {
        "schema": "material_evidence_ablation_artifacts_v1",
        "ablation": ABLATION_LABEL,
        "inputs": report["campaigns"],
        "files": [_artifact_record(path) for path in (artifacts.json, artifacts.csv, artifacts.pdf, artifacts.png)],
    }
    artifacts.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return artifacts


__all__ = [
    "ABLATION_LABEL",
    "IDENTITY_ALLOWLIST",
    "MaterialAblationArtifacts",
    "MaterialEvidenceAblationError",
    "compare_material_campaigns",
    "write_material_evidence_ablation",
]
