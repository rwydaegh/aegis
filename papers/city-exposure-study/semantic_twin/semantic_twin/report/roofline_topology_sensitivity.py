"""Authenticated paired sensitivity report for the two roofline topologies.

This is deliberately separate from the IID versus rotated-Fibonacci report.
It compares one legacy hybrid campaign with one closed first-material-
interaction campaign only after strict campaign loading and a fail-closed
identity audit whose allowlist contains topology-specific fields alone.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from semantic_twin.exposure.roofline_campaign import (
    BODY_METRICS,
    FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION,
    SCHEMA_VERSION,
    TIMING_FIELDS,
)

from .roofline_campaign_comparison import CampaignComparisonError, _Campaign, _load_campaign

REPORT_SCHEMA_VERSION = "roofline_transport_topology_sensitivity_v1"
ARTIFACT_SCHEMA_VERSION = "roofline_transport_topology_sensitivity_artifacts_v1"
HYBRID_TOPOLOGY = "hybrid_max_bounces_v1"
FIRST_TOPOLOGY = "first_material_interaction_v1"

_REMOVED_IDENTITY_PATHS = (
    ("configuration", "schema_version"),
    ("configuration", "transport_topology"),
    ("configuration", "components"),
    ("configuration", "specular_acceptance"),
    ("configuration", "minimum_completed_specular_order"),
    ("configuration", "convergence_looks"),
    ("components",),
    ("schema_version",),
    ("transport", "estimator", "configuration", "transport_topology"),
    ("transport", "estimator", "configuration", "max_order"),
    ("transport", "estimator", "configuration", "specular_suffix_mode"),
    ("transport", "estimator", "configuration", "specular_candidate_budget"),
    ("transport", "estimator", "configuration", "sampled_specular"),
    ("transport", "estimator", "configuration", "specular_transport", "candidate_budget"),
    ("transport", "tracer", "configuration", "max_bounces"),
    ("transport", "tracer", "configuration", "roulette_start"),
    ("code",),
    ("runtime",),
    ("output",),
)
_ALLOWED_IDENTITY_PATHS = tuple(".".join(path) for path in _REMOVED_IDENTITY_PATHS) + (
    "configuration.planned_seeds[tail_after_common_prefix]",
    "inputs.files[roofline_campaign_run_config]",
)


@dataclass(frozen=True)
class TopologySensitivityArtifacts:
    """Files written by :func:`write_topology_sensitivity`."""

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


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _get_path(value: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = value
    for part in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _pop_path(value: dict[str, Any], path: Sequence[str]) -> None:
    current: Any = value
    for part in path[:-1]:
        if not isinstance(current, dict):
            return
        current = current.get(part)
    if isinstance(current, dict):
        current.pop(path[-1], None)


def _is_run_config(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    path = record.get("path")
    name = Path(path).name if isinstance(path, str) else ""
    return name.startswith("roofline_campaign_") and name.endswith(".json")


def _normalize_inputs(identity: dict[str, Any]) -> None:
    inputs = identity.get("inputs")
    if not isinstance(inputs, dict):
        return
    files = inputs.get("files")
    if not isinstance(files, list):
        raise CampaignComparisonError("campaign identity inputs.files must be a list")
    run_configs = [record for record in files if _is_run_config(record)]
    if len(run_configs) != 1:
        raise CampaignComparisonError("topology sensitivity requires exactly one sealed roofline run config input")
    retained = [record for record in files if not _is_run_config(record)]
    inputs["files"] = retained
    inputs["file_count"] = len(retained)
    inputs["bytes"] = sum(int(record["bytes"]) for record in retained)


def _normalized_identity(campaign: _Campaign, common_seeds: tuple[int, ...]) -> dict[str, Any]:
    value = copy.deepcopy(campaign.identity_data)
    configuration = value.get("configuration")
    if not isinstance(configuration, dict):
        raise CampaignComparisonError("campaign identity has no configuration object")
    planned = tuple(int(seed) for seed in configuration.get("planned_seeds", ()))
    if planned[: len(common_seeds)] != common_seeds:
        raise CampaignComparisonError("planned seeds do not contain the common committed prefix")
    configuration["planned_seeds"] = list(common_seeds)
    for path in _REMOVED_IDENTITY_PATHS:
        _pop_path(value, path)
    _normalize_inputs(value)
    return value


def _mapping_difference_paths(left: dict[Any, Any], right: dict[Any, Any], prefix: str) -> list[str]:
    differences: list[str] = []
    for key in sorted(set(left) | set(right)):
        path = f"{prefix}.{key}" if prefix else str(key)
        if key not in left or key not in right:
            differences.append(path)
        else:
            differences.extend(_identity_difference_paths(left[key], right[key], path))
    return differences


def _sequence_difference_paths(left: list[Any], right: list[Any], prefix: str) -> list[str]:
    if len(left) != len(right):
        return [prefix]
    differences: list[str] = []
    for index, (lhs, rhs) in enumerate(zip(left, right, strict=True)):
        differences.extend(_identity_difference_paths(lhs, rhs, f"{prefix}[{index}]"))
    return differences


def _identity_difference_paths(left: Any, right: Any, prefix: str = "") -> list[str]:
    if isinstance(left, dict) and isinstance(right, dict):
        return _mapping_difference_paths(left, right, prefix)
    if isinstance(left, list) and isinstance(right, list):
        return _sequence_difference_paths(left, right, prefix)
    return [] if left == right else [prefix]


def _validate_route(left: _Campaign, right: _Campaign) -> None:
    if left.points != right.points:
        raise CampaignComparisonError("topology campaigns have different route lengths")
    for index, (hybrid, first) in enumerate(zip(left.locations, right.locations, strict=True)):
        for field in ("standpoint", "position_m", "body_yaw_deg", "ground_z_m"):
            if field not in hybrid or field not in first or hybrid[field] != first[field]:
                raise CampaignComparisonError(f"route field {field!r} differs at standpoint {index}")


def _validate_pair(hybrid: _Campaign, first: _Campaign) -> tuple[int, ...]:
    if hybrid.schema_version != SCHEMA_VERSION or hybrid.transport_topology != HYBRID_TOPOLOGY:
        raise CampaignComparisonError("hybrid input is not a legacy hybrid roofline campaign")
    if first.schema_version != FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION or first.transport_topology != FIRST_TOPOLOGY:
        raise CampaignComparisonError("first-interaction input has the wrong schema or topology")
    if hybrid.sampling != first.sampling:
        raise CampaignComparisonError("topology campaigns use different launch samplers")
    common_count = min(len(hybrid.seeds), len(first.seeds))
    if common_count < 1 or hybrid.seeds[:common_count] != first.seeds[:common_count]:
        raise CampaignComparisonError("topology campaigns do not share a committed seed prefix")
    common = hybrid.seeds[:common_count]
    _validate_route(hybrid, first)
    normalized_hybrid = _normalized_identity(hybrid, common)
    normalized_first = _normalized_identity(first, common)
    if normalized_hybrid != normalized_first:
        paths = _identity_difference_paths(normalized_hybrid, normalized_first)
        raise CampaignComparisonError("undeclared cross-topology identity drift: " + ", ".join(paths[:12]))
    return common


def _db_change(hybrid: np.ndarray, first: np.ndarray) -> list[float | None]:
    hybrid = np.asarray(hybrid, dtype=np.float64)
    first = np.asarray(first, dtype=np.float64)
    result: list[float | None] = []
    for lhs, rhs in zip(hybrid.ravel(), first.ravel(), strict=True):
        result.append(None if lhs <= 0.0 or rhs <= 0.0 else float(10.0 * np.log10(rhs / lhs)))
    return result


def _scalar_pair(hybrid: float, first: float) -> dict[str, float | None]:
    return {
        "hybrid": float(hybrid),
        "first_material_interaction": float(first),
        "difference_first_minus_hybrid": float(first - hybrid),
        "absolute_difference": float(abs(first - hybrid)),
        "difference_db": None if hybrid <= 0.0 or first <= 0.0 else float(10.0 * np.log10(first / hybrid)),
    }


def _route_quantiles(hybrid: np.ndarray, first: np.ndarray) -> dict[str, Any]:
    paired_changes = np.asarray(
        [change for change in _db_change(hybrid, first) if change is not None], dtype=np.float64
    )
    result: dict[str, Any] = {
        "definitions": {
            "per_arm": (
                "each arm's route quantile computed independently, then compared; "
                "difference_db is the ratio of the two quantiles, not a quantile of per-standpoint changes"
            ),
            "paired_db_change": (
                "quantiles of the per-standpoint dB change first/hybrid, "
                "excluding standpoints where either arm is nonpositive"
            ),
        },
        "paired_db_change": {
            "defined_standpoints": int(paired_changes.size),
            "excluded_standpoints": int(np.asarray(hybrid).size - paired_changes.size),
        },
    }
    for quantile in (0.10, 0.50, 0.90):
        key = f"q{int(quantile * 100)}"
        result[key] = _scalar_pair(float(np.quantile(hybrid, quantile)), float(np.quantile(first, quantile)))
        result["paired_db_change"][key] = (
            None if paired_changes.size == 0 else float(np.quantile(paired_changes, quantile))
        )
    return result


def _looks(hybrid: _Campaign, first: _Campaign, count: int) -> tuple[int, ...]:
    common = sorted(set(hybrid.convergence_looks).intersection(first.convergence_looks))
    reached = [look for look in common if 0 < look <= count]
    if count not in reached:
        reached.append(count)
    return tuple(sorted(set(reached)))


def _summary_arrays(campaign: _Campaign, count: int) -> tuple[np.ndarray, np.ndarray]:
    return np.mean(campaign.raw_transfer[:count], axis=0), np.mean(campaign.body_metrics[:count], axis=0)


def _per_seed_points(hybrid: _Campaign, first: _Campaign, seeds: tuple[int, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    h_direct = hybrid.components.index("direct")
    h_total = hybrid.components.index("total")
    f_direct = first.components.index("direct")
    f_total = first.components.index("total")
    for replica, seed in enumerate(seeds):
        for point in range(hybrid.points):
            raw = {
                "direct": _scalar_pair(
                    hybrid.raw_transfer[replica, point, h_direct], first.raw_transfer[replica, point, f_direct]
                ),
                "total": _scalar_pair(
                    hybrid.raw_transfer[replica, point, h_total], first.raw_transfer[replica, point, f_total]
                ),
                "hybrid_specular": float(hybrid.raw_transfer[replica, point, hybrid.components.index("specular")]),
                "hybrid_diffuse": float(hybrid.raw_transfer[replica, point, hybrid.components.index("diffuse")]),
                "first_all_specular": float(first.raw_transfer[replica, point, first.components.index("all_specular")]),
                "first_first_diffuse": float(
                    first.raw_transfer[replica, point, first.components.index("first_diffuse")]
                ),
            }
            body = {
                metric: _scalar_pair(
                    hybrid.body_metrics[replica, point, h_total, metric_index],
                    first.body_metrics[replica, point, f_total, metric_index],
                )
                for metric_index, metric in enumerate(BODY_METRICS)
            }
            rows.append({"seed": seed, "standpoint": point, "raw_transfer": raw, "total_body_metrics": body})
    return rows


def _route_report(hybrid: _Campaign, first: _Campaign, count: int) -> dict[str, Any]:
    h_raw, h_body = _summary_arrays(hybrid, count)
    f_raw, f_body = _summary_arrays(first, count)
    report: dict[str, Any] = {"raw_transfer": {}, "total_body_metrics": {}}
    for component in ("direct", "total"):
        h_values = h_raw[:, hybrid.components.index(component)]
        f_values = f_raw[:, first.components.index(component)]
        report["raw_transfer"][component] = {
            "hybrid_by_standpoint": [float(value) for value in h_values],
            "first_material_interaction_by_standpoint": [float(value) for value in f_values],
            "difference_by_standpoint": [float(value) for value in f_values - h_values],
            "absolute_difference_by_standpoint": [float(value) for value in np.abs(f_values - h_values)],
            "difference_db_by_standpoint": _db_change(h_values, f_values),
            "route_quantiles": _route_quantiles(h_values, f_values),
        }
    for metric_index, metric in enumerate(BODY_METRICS):
        h_values = h_body[:, hybrid.components.index("total"), metric_index]
        f_values = f_body[:, first.components.index("total"), metric_index]
        report["total_body_metrics"][metric] = {
            "hybrid_by_standpoint": [float(value) for value in h_values],
            "first_material_interaction_by_standpoint": [float(value) for value in f_values],
            "difference_by_standpoint": [float(value) for value in f_values - h_values],
            "absolute_difference_by_standpoint": [float(value) for value in np.abs(f_values - h_values)],
            "difference_db_by_standpoint": _db_change(h_values, f_values),
            "route_quantiles": _route_quantiles(h_values, f_values),
        }
    return report


def _zero_direct(hybrid: _Campaign, first: _Campaign, count: int) -> dict[str, Any]:
    h = np.mean(hybrid.raw_transfer[:count, :, hybrid.components.index("direct")], axis=0)
    f = np.mean(first.raw_transfer[:count, :, first.components.index("direct")], axis=0)
    h_zero = set(int(value) for value in np.flatnonzero(h <= 0.0))
    f_zero = set(int(value) for value in np.flatnonzero(f <= 0.0))
    return {
        "hybrid": sorted(h_zero),
        "first_material_interaction": sorted(f_zero),
        "shared": sorted(h_zero & f_zero),
        "hybrid_only": sorted(h_zero - f_zero),
        "first_material_interaction_only": sorted(f_zero - h_zero),
    }


def _convergence(hybrid: _Campaign, first: _Campaign, count: int) -> list[dict[str, Any]]:
    rows = []
    for look in _looks(hybrid, first, count):
        route = _route_report(hybrid, first, look)
        wb = route["total_body_metrics"]["sar_wb_w_kg"]
        finite_db = np.asarray([value for value in wb["difference_db_by_standpoint"] if value is not None])
        rows.append(
            {
                "replicas": look,
                "wbsar_route_quantiles": wb["route_quantiles"],
                "wbsar_maximum_abs_pointwise_db": (None if finite_db.size == 0 else float(np.max(np.abs(finite_db)))),
            }
        )
    return rows


def _timing(campaign: _Campaign, count: int) -> dict[str, dict[str, float | int | None]]:
    report = {}
    for index, name in enumerate(TIMING_FIELDS):
        values = campaign.timings[:count, :, index]
        finite = values[np.isfinite(values)]
        report[name] = {
            "observations": int(finite.size),
            "total_seconds": None if finite.size == 0 else float(np.sum(finite)),
            "mean_seconds": None if finite.size == 0 else float(np.mean(finite)),
        }
    return report


def _timing_report(hybrid: _Campaign, first: _Campaign, count: int) -> dict[str, Any]:
    hybrid_timing = _timing(hybrid, count)
    first_timing = _timing(first, count)
    comparison = {}
    for name in TIMING_FIELDS:
        hybrid_total = hybrid_timing[name]["total_seconds"]
        first_total = first_timing[name]["total_seconds"]
        comparison[name] = {
            "difference_seconds": (
                None if hybrid_total is None or first_total is None else float(first_total - hybrid_total)
            ),
            "ratio_first_over_hybrid": (
                None
                if hybrid_total is None or first_total is None or hybrid_total <= 0.0
                else float(first_total / hybrid_total)
            ),
        }
    return {
        "hybrid": hybrid_timing,
        "first_material_interaction": first_timing,
        "comparison": comparison,
    }


def _topology_parameters(campaign: _Campaign) -> dict[str, Any]:
    identity = campaign.identity_data
    estimator = ("transport", "estimator", "configuration")
    tracer = ("transport", "tracer", "configuration")
    return {
        "schema_version": campaign.schema_version,
        "transport_topology": campaign.transport_topology,
        "components": list(campaign.components),
        "specular_acceptance": _get_path(identity, ("configuration", "specular_acceptance")),
        "maximum_bounces": _get_path(identity, (*tracer, "max_bounces")),
        "estimator_max_order": _get_path(identity, (*estimator, "max_order")),
        "specular_suffix_mode": _get_path(identity, (*estimator, "specular_suffix_mode")),
        "specular_candidate_budget": _get_path(identity, (*estimator, "specular_candidate_budget")),
        "specular_transport_candidate_budget": _get_path(
            identity, (*estimator, "specular_transport", "candidate_budget")
        ),
    }


def compare_topologies(hybrid_directory: str | Path, first_directory: str | Path) -> dict[str, Any]:
    """Load, authenticate, and compare the declared topology pair."""
    hybrid = _load_campaign(hybrid_directory)
    first = _load_campaign(first_directory)
    seeds = _validate_pair(hybrid, first)
    normalized = _normalized_identity(hybrid, seeds)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "comparison": "first_material_interaction_v1 minus hybrid_max_bounces_v1",
        "normalization": "per each campaign's identical sealed reference mode",
        "common_contract_sha256": hashlib.sha256(_canonical(normalized).encode()).hexdigest(),
        "allowed_identity_differences": list(_ALLOWED_IDENTITY_PATHS),
        "topology_parameters": {
            "hybrid": _topology_parameters(hybrid),
            "first_material_interaction": _topology_parameters(first),
        },
        "hybrid": {
            "directory": str(hybrid.root),
            "schema_version": hybrid.schema_version,
            "transport_topology": hybrid.transport_topology,
            "components": list(hybrid.components),
            "identity_sha256": hybrid.identity["sha256"],
            "manifest_sha256": _sha256(hybrid.root / "manifest.json"),
        },
        "first_material_interaction": {
            "directory": str(first.root),
            "schema_version": first.schema_version,
            "transport_topology": first.transport_topology,
            "components": list(first.components),
            "identity_sha256": first.identity["sha256"],
            "manifest_sha256": _sha256(first.root / "manifest.json"),
        },
        "common_seeds": list(seeds),
        "standpoints": hybrid.points,
        "route": [
            {
                "standpoint": index,
                "position_m": hybrid.locations[index]["position_m"],
                "body_yaw_deg": hybrid.locations[index]["body_yaw_deg"],
                "ground_z_m": hybrid.locations[index]["ground_z_m"],
            }
            for index in range(hybrid.points)
        ],
        "per_seed_point": _per_seed_points(hybrid, first, seeds),
        "final_route": _route_report(hybrid, first, len(seeds)),
        "zero_direct_strata": _zero_direct(hybrid, first, len(seeds)),
        "convergence": _convergence(hybrid, first, len(seeds)),
        "timing": _timing_report(hybrid, first, len(seeds)),
    }


def _write_csv(path: Path, report: Mapping[str, Any]) -> None:
    fields = (
        "seed",
        "standpoint",
        "hybrid_direct",
        "first_direct",
        "direct_difference",
        "direct_absolute_difference",
        "direct_difference_db",
        "hybrid_total",
        "first_total",
        "total_difference",
        "total_absolute_difference",
        "total_difference_db",
        "hybrid_specular",
        "hybrid_diffuse",
        "first_all_specular",
        "first_first_diffuse",
        *[f"hybrid_{metric}" for metric in BODY_METRICS],
        *[f"first_{metric}" for metric in BODY_METRICS],
        *[f"difference_{metric}" for metric in BODY_METRICS],
        *[f"absolute_difference_{metric}" for metric in BODY_METRICS],
        *[f"difference_db_{metric}" for metric in BODY_METRICS],
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["per_seed_point"]:
            raw = row["raw_transfer"]
            values: dict[str, Any] = {"seed": row["seed"], "standpoint": row["standpoint"]}
            for component in ("direct", "total"):
                pair = raw[component]
                values.update(
                    {
                        f"hybrid_{component}": pair["hybrid"],
                        f"first_{component}": pair["first_material_interaction"],
                        f"{component}_difference": pair["difference_first_minus_hybrid"],
                        f"{component}_absolute_difference": pair["absolute_difference"],
                        f"{component}_difference_db": pair["difference_db"],
                    }
                )
            for name in ("hybrid_specular", "hybrid_diffuse", "first_all_specular", "first_first_diffuse"):
                values[name] = raw[name]
            for metric, pair in row["total_body_metrics"].items():
                values[f"hybrid_{metric}"] = pair["hybrid"]
                values[f"first_{metric}"] = pair["first_material_interaction"]
                values[f"difference_{metric}"] = pair["difference_first_minus_hybrid"]
                values[f"absolute_difference_{metric}"] = pair["absolute_difference"]
                values[f"difference_db_{metric}"] = pair["difference_db"]
            writer.writerow(values)


def _cdf(values: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(np.asarray(values, dtype=np.float64))
    return x, (np.arange(x.size) + 0.5) / x.size


def _plot(report: Mapping[str, Any], pdf: Path, png: Path) -> None:
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 2, figsize=(10.8, 7.2))
    for axis, section, metric, label in (
        (axes[0, 0], "total_body_metrics", "sar_wb_w_kg", "Normalized wbSAR"),
        (axes[0, 1], "raw_transfer", "total", r"Total transfer (m$^{-2}$)"),
    ):
        values = report["final_route"][section][metric]
        for key, topology, style in (
            ("hybrid_by_standpoint", "hybrid", "-"),
            ("first_material_interaction_by_standpoint", "first interaction", "--"),
        ):
            x, probability = _cdf(values[key])
            axis.plot(x, probability, style, drawstyle="steps-post", label=topology)
        axis.set_xlabel(label)
        axis.set_ylabel("Route CDF")
        axis.grid(alpha=0.25)
    wb = report["final_route"]["total_body_metrics"]["sar_wb_w_kg"]
    axes[1, 0].plot(wb["difference_db_by_standpoint"], marker="o", ms=3)
    axes[1, 0].axhline(0.0, color="black", lw=0.8)
    axes[1, 0].set_xlabel("Standpoint")
    axes[1, 0].set_ylabel("wbSAR first minus hybrid (dB)")
    axes[1, 0].grid(alpha=0.25)
    timing_names = ("stochastic_trace_seconds", "specular_seconds", "body_coupling_seconds")
    x = np.arange(len(timing_names))
    axes[1, 1].bar(
        x - 0.18,
        [report["timing"]["hybrid"][name]["total_seconds"] or 0.0 for name in timing_names],
        width=0.36,
        label="hybrid",
    )
    axes[1, 1].bar(
        x + 0.18,
        [report["timing"]["first_material_interaction"][name]["total_seconds"] or 0.0 for name in timing_names],
        width=0.36,
        label="first interaction",
    )
    axes[1, 1].set_xticks(x, ["trace", "specular", "body"])
    axes[1, 1].set_ylabel("Observed total time (s)")
    axes[1, 1].grid(axis="y", alpha=0.25)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.suptitle("Transport-topology sensitivity", y=0.985)
    figure.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.95), ncol=2, frameon=False)
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.89))
    figure.savefig(pdf, bbox_inches="tight")
    figure.savefig(png, dpi=220, bbox_inches="tight")
    plt.close(figure)


def _artifact_manifest(path: Path, report: Mapping[str, Any], artifacts: Iterable[Path]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": ARTIFACT_SCHEMA_VERSION,
                "report_schema_version": REPORT_SCHEMA_VERSION,
                "hybrid_identity_sha256": report["hybrid"]["identity_sha256"],
                "first_material_interaction_identity_sha256": report["first_material_interaction"]["identity_sha256"],
                "artifacts": {
                    artifact.name: {"sha256": _sha256(artifact), "bytes": artifact.stat().st_size}
                    for artifact in artifacts
                },
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def write_topology_sensitivity(
    hybrid_directory: str | Path, first_directory: str | Path, output_prefix: str | Path
) -> TopologySensitivityArtifacts:
    """Write authenticated JSON, CSV, PDF, PNG, and artifact hashes."""
    report = compare_topologies(hybrid_directory, first_directory)
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    artifacts = TopologySensitivityArtifacts(
        json=prefix.with_suffix(".json"),
        csv=prefix.with_suffix(".csv"),
        pdf=prefix.with_suffix(".pdf"),
        png=prefix.with_suffix(".png"),
        manifest=prefix.with_name(prefix.name + "_manifest.json"),
    )
    artifacts.json.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    _write_csv(artifacts.csv, report)
    _plot(report, artifacts.pdf, artifacts.png)
    _artifact_manifest(
        artifacts.manifest,
        report,
        (artifacts.json, artifacts.csv, artifacts.pdf, artifacts.png),
    )
    return artifacts


__all__ = [
    "TopologySensitivityArtifacts",
    "compare_topologies",
    "write_topology_sensitivity",
]
