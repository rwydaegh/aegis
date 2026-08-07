"""Auditable publication exports for completed single-IID roofline campaigns.

The paired campaign report answers a sampler-method question. This module has
the separate job of comparing the current production result across cities. It
loads every input through the campaign comparator's strict single-campaign
reader, so identity wrappers, manifests, replica hashes, schemas, route rows,
and numeric arrays are authenticated before any result is plotted.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from semantic_twin.exposure.roofline_campaign import BODY_METRICS, SCHEMA_VERSION, TIMING_FIELDS

from .roofline_campaign_comparison import (
    CampaignComparisonError,
    _Campaign,
    _convergence_evidence,
    _load_campaign,
)

RESULT_SCHEMA_VERSION = "roofline_multicity_results_v1"
ARTIFACT_MANIFEST_SCHEMA_VERSION = "roofline_multicity_artifacts_v1"
NORMALIZATION = "per unit rho_A P_EIRP"
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_NAMESPACE = "AEGIS_multicity_route_bootstrap_v1"
BOOTSTRAP_QUANTILES = (0.10, 0.50, 0.90)

_ROUTE_METRICS = (
    ("raw_total_transfer_m_inv2", "total transfer", "m^-2"),
    ("raw_direct_transfer_m_inv2", "direct transfer", "m^-2"),
    ("multipath_surplus_db", "multipath surplus", "dB"),
    ("peak_sab_ensemble_field", "peak Sab of the replica-mean field", "1"),
    ("peak_sab_mean_per_replica", "mean per-replica peak Sab", "1"),
    ("mean_sab", "area-mean Sab", "1"),
    ("absorbed_power", "absorbed power", "m^2"),
    ("wbsar", "whole-body SAR", "m^2 kg^-1"),
)


@dataclass(frozen=True)
class CampaignInput:
    """One city label and completed single-IID campaign directory."""

    city: str
    directory: Path


@dataclass(frozen=True)
class MulticityArtifacts:
    """Files written by :func:`write_multicity_results`."""

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


def _cdf(values: np.ndarray) -> dict[str, list[float]]:
    finite = np.sort(np.asarray(values, dtype=np.float64)[np.isfinite(values)])
    if finite.size == 0:
        return {"x": [], "probability": []}
    return {
        "x": [float(value) for value in finite],
        "probability": [float(value) for value in (np.arange(finite.size) + 0.5) / finite.size],
    }


def _bootstrap_seed(identity_sha256: str) -> int:
    payload = f"{BOOTSTRAP_NAMESPACE}:{identity_sha256}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], byteorder="little", signed=False)


def _finite_quantile(values: np.ndarray, quantile: float) -> float | None:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return None
    return float(np.quantile(finite, quantile))


def _bootstrap_quantiles(sampled_routes: np.ndarray, final_route: np.ndarray) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for quantile in BOOTSTRAP_QUANTILES:
        bootstrap_values = np.asarray([_finite_quantile(route, quantile) for route in sampled_routes], dtype=np.float64)
        bootstrap_values = bootstrap_values[np.isfinite(bootstrap_values)]
        key = f"q{int(round(100 * quantile)):02d}"
        report[key] = {
            "estimate": _finite_quantile(final_route, quantile),
            "ci95_percentile": (
                None
                if bootstrap_values.size == 0
                else [
                    float(np.quantile(bootstrap_values, 0.025)),
                    float(np.quantile(bootstrap_values, 0.975)),
                ]
            ),
            "finite_bootstrap_replicates": int(bootstrap_values.size),
        }
    return report


def _bootstrap_route_uncertainty(campaign: _Campaign) -> dict[str, Any]:
    seed = _bootstrap_seed(campaign.identity["sha256"])
    generator = np.random.Generator(np.random.PCG64(seed))
    count = len(campaign.seeds)
    indices = generator.integers(0, count, size=(BOOTSTRAP_REPLICATES, count))

    component_total = campaign.components.index("total")
    component_direct = campaign.components.index("direct")
    body = {name: campaign.body_metrics[:, :, component_total, index] for index, name in enumerate(BODY_METRICS)}
    raw_total = campaign.raw_transfer[:, :, component_total]
    raw_direct = campaign.raw_transfer[:, :, component_direct]
    replica_metrics = {
        "raw_total_transfer_m_inv2": raw_total,
        "raw_direct_transfer_m_inv2": raw_direct,
        "peak_sab_mean_per_replica": body["peak_sab_w_m2"],
        "mean_sab": body["mean_sab_w_m2"],
        "absorbed_power": body["absorbed_power_w"],
        "wbsar": body["sar_wb_w_kg"],
    }
    result: dict[str, Any] = {}
    for name, values in replica_metrics.items():
        sampled_routes = np.mean(values[indices], axis=1)
        final_route = np.mean(values, axis=0)
        result[name] = _bootstrap_quantiles(sampled_routes, final_route)

    sampled_total = np.mean(raw_total[indices], axis=1)
    sampled_direct = np.mean(raw_direct[indices], axis=1)
    sampled_surplus = np.full(sampled_total.shape, np.nan, dtype=np.float64)
    sampled_positive = (sampled_total > 0.0) & (sampled_direct > 0.0)
    sampled_surplus[sampled_positive] = 10.0 * np.log10(
        sampled_total[sampled_positive] / sampled_direct[sampled_positive]
    )
    final_total = np.mean(raw_total, axis=0)
    final_direct = np.mean(raw_direct, axis=0)
    final_surplus = np.full(final_total.shape, np.nan, dtype=np.float64)
    final_positive = (final_total > 0.0) & (final_direct > 0.0)
    final_surplus[final_positive] = 10.0 * np.log10(final_total[final_positive] / final_direct[final_positive])
    result["multipath_surplus_db"] = _bootstrap_quantiles(sampled_surplus, final_surplus)
    return {
        "method": "IID percentile bootstrap over complete route replicas",
        "spatial_dependence": "one bootstrap draw resamples whole replicas jointly across all standpoints",
        "rng": "numpy.random.PCG64",
        "seed_derivation": f"uint64_le(sha256({BOOTSTRAP_NAMESPACE}:campaign_identity_sha256)[0:8])",
        "seed": seed,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "confidence_level": 0.95,
        "quantiles": result,
        "unavailable_metric": {
            "peak_sab_ensemble_field": (
                "the campaign persists the final replica-mean Sab maximum but not a per-replica body field "
                "from which that nonlinear maximum could be bootstrapped"
            )
        },
    }


def _route_distances(campaign: _Campaign) -> np.ndarray:
    positions = np.asarray([row["position_m"] for row in campaign.locations], dtype=np.float64)
    if positions.shape[0] == 1:
        return np.zeros(1, dtype=np.float64)
    steps = np.linalg.norm(np.diff(positions, axis=0), axis=1)
    return np.concatenate((np.zeros(1, dtype=np.float64), np.cumsum(steps)))


def _available_looks(campaign: _Campaign, requested: Sequence[int] | None) -> tuple[int, ...]:
    replicas = len(campaign.seeds)
    if requested is None:
        declared = campaign.convergence_looks
        looks = tuple(look for look in declared if 0 < look <= replicas)
        if replicas not in looks:
            looks = (*looks, replicas)
    else:
        looks = tuple(int(look) for look in requested)
        if not looks or tuple(sorted(set(looks))) != looks or looks[0] < 1:
            raise ValueError("looks must be unique, increasing, and positive")
        if looks[-1] > replicas:
            raise CampaignComparisonError(
                f"requested look {looks[-1]} exceeds {replicas} committed replicas in {campaign.root}"
            )
    return looks


def _require_current_iid(campaign: _Campaign) -> None:
    if campaign.sampling != "iid":
        raise CampaignComparisonError(f"multicity production report requires IID campaigns: {campaign.root}")
    if campaign.seeds != campaign.planned_seeds:
        raise CampaignComparisonError(
            f"multicity production report requires a completed planned seed set: {campaign.root}"
        )
    configuration = campaign.identity_data.get("configuration", {})
    if configuration.get("reference_mode") != "per_density_eirp":
        raise CampaignComparisonError(
            f"multicity production report requires reference_mode='per_density_eirp': {campaign.root}"
        )


def _point_rows(campaign: _Campaign) -> list[dict[str, Any]]:
    raw = np.mean(campaign.raw_transfer, axis=0)
    body = np.mean(campaign.body_metrics, axis=0)
    direct = raw[:, campaign.components.index("direct")]
    total = raw[:, campaign.components.index("total")]
    surplus = np.full(campaign.points, np.nan, dtype=np.float64)
    positive = (direct > 0.0) & (total > 0.0)
    surplus[positive] = 10.0 * np.log10(total[positive] / direct[positive])
    distance = _route_distances(campaign)

    total_body = body[:, campaign.components.index("total"), :]
    metric = {name: total_body[:, index] for index, name in enumerate(BODY_METRICS)}
    rows: list[dict[str, Any]] = []
    for index, location in enumerate(campaign.locations):
        try:
            ensemble_peak = float(location["components"]["total"]["body"]["ensemble_field_peak_sab_w_m2"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CampaignComparisonError(
                f"locations.jsonl lacks the final ensemble-field peak Sab at standpoint {index}: {campaign.root}"
            ) from exc
        if not np.isfinite(ensemble_peak) or ensemble_peak < 0.0:
            raise CampaignComparisonError(
                f"locations.jsonl has an invalid ensemble-field peak Sab at standpoint {index}: {campaign.root}"
            )
        row = {
            "standpoint": index,
            "position_m": [float(value) for value in location["position_m"]],
            "route_distance_m": float(distance[index]),
            "raw_total_transfer_m_inv2": float(total[index]),
            "raw_direct_transfer_m_inv2": float(direct[index]),
            "multipath_surplus_db": None if not np.isfinite(surplus[index]) else float(surplus[index]),
            "peak_sab_ensemble_field": ensemble_peak,
            "peak_sab_mean_per_replica": float(metric["peak_sab_w_m2"][index]),
            "mean_sab": float(metric["mean_sab_w_m2"][index]),
            "absorbed_power": float(metric["absorbed_power_w"][index]),
            "wbsar": float(metric["sar_wb_w_kg"][index]),
        }
        if campaign.schema_version != SCHEMA_VERSION:
            row["component_raw_transfer_m_inv2"] = {
                component: float(raw[index, component_index])
                for component_index, component in enumerate(campaign.components)
            }
            row["component_body"] = {
                component: {
                    metric_name: float(body[index, component_index, metric_index])
                    for metric_index, metric_name in enumerate(BODY_METRICS)
                }
                for component_index, component in enumerate(campaign.components)
            }
        rows.append(row)
    return rows


def _convergence_rows(campaign: _Campaign, looks: tuple[int, ...]) -> list[dict[str, Any]]:
    evidence = _convergence_evidence(campaign, looks)
    rows: list[dict[str, Any]] = []
    for previous, current in zip(looks, looks[1:]):
        transition = evidence["look_to_look"][f"{previous}_to_{current}"]
        body = transition["body_metrics"]
        rows.append(
            {
                "from_replicas": previous,
                "to_replicas": current,
                "total_transfer": transition["total_transfer"]["pointwise"],
                "mean_sab": body["mean_sab_w_m2"]["pointwise"],
                "wbsar": body["sar_wb_w_kg"]["pointwise"],
            }
        )
    standard_error: list[dict[str, Any]] = []
    for look in looks:
        at_look = evidence["standard_error"][str(look)]
        standard_error.append(
            {
                "replicas": look,
                "total_transfer": at_look["total_transfer"],
                "mean_sab": at_look["body_metrics"]["mean_sab_w_m2"],
                "wbsar": at_look["body_metrics"]["sar_wb_w_kg"],
            }
        )
    return [{"look_to_look": rows, "standard_error": standard_error}]


def _quantile_db_change(previous: np.ndarray, current: np.ndarray, quantile: float) -> float | None:
    previous_quantile = _finite_quantile(previous, quantile)
    current_quantile = _finite_quantile(current, quantile)
    if previous_quantile is None or current_quantile is None or previous_quantile <= 0.0 or current_quantile <= 0.0:
        return None
    return float(abs(10.0 * np.log10(current_quantile / previous_quantile)))


def _pointwise_db_change(previous: np.ndarray, current: np.ndarray, indices: np.ndarray) -> dict[str, Any]:
    selected_previous = previous[indices]
    selected_current = current[indices]
    valid = (selected_previous > 0.0) & (selected_current > 0.0)
    change = np.abs(10.0 * np.log10(selected_current[valid] / selected_previous[valid]))
    return {
        "standpoints": [int(index) for index in indices],
        "finite_change_count": int(change.size),
        "undefined_db_change_count": int(indices.size - change.size),
        "maximum_abs_db": None if change.size == 0 else float(np.max(change)),
        "p90_abs_db": None if change.size == 0 else float(np.quantile(change, 0.90)),
    }


def _tail_instability(campaign: _Campaign, looks: tuple[int, ...]) -> dict[str, Any]:
    total_index = campaign.components.index("total")
    direct_index = campaign.components.index("direct")
    wbsar_index = BODY_METRICS.index("sar_wb_w_kg")
    direct_final = np.mean(campaign.raw_transfer[:, :, direct_index], axis=0)
    wbsar_by_look = {look: np.mean(campaign.body_metrics[:look, :, total_index, wbsar_index], axis=0) for look in looks}
    final_wbsar = wbsar_by_look[looks[-1]]
    lower_count = max(1, int(np.ceil(0.10 * campaign.points)))
    lower_indices = np.argsort(final_wbsar, kind="stable")[:lower_count]
    transitions = []
    for previous, current in zip(looks, looks[1:]):
        previous_values = wbsar_by_look[previous]
        current_values = wbsar_by_look[current]
        transitions.append(
            {
                "from_replicas": previous,
                "to_replicas": current,
                "route_quantile_abs_change_db": {
                    f"q{int(round(100 * quantile)):02d}": _quantile_db_change(previous_values, current_values, quantile)
                    for quantile in BOOTSTRAP_QUANTILES
                },
                "final_lower_decile_points": _pointwise_db_change(previous_values, current_values, lower_indices),
            }
        )
    zero_direct = np.flatnonzero(direct_final <= 0.0)
    nonpositive_wbsar = np.flatnonzero(final_wbsar <= 0.0)
    return {
        "status": "structural_zero_direct_present" if zero_direct.size else "finite_direct_support",
        "zero_direct_standpoints": [int(index) for index in zero_direct],
        "nonpositive_final_wbsar_standpoints": [int(index) for index in nonpositive_wbsar],
        "final_lower_decile_definition": (
            f"lowest {lower_count} of {campaign.points} standpoints ranked by final replica-mean wbSAR"
        ),
        "final_lower_decile_standpoints": [int(index) for index in lower_indices],
        "look_to_look": transitions,
        "interpretation": (
            "Central route-quantile stability does not certify individual low-support standpoints. "
            "Inspect final_lower_decile_points and zero_direct_standpoints before treating the lower tail as stable."
        ),
    }


def _timings(campaign: _Campaign) -> dict[str, dict[str, float | int | None]]:
    result: dict[str, dict[str, float | int | None]] = {}
    for index, name in enumerate(TIMING_FIELDS):
        values = campaign.timings[:, :, index]
        finite = values[np.isfinite(values)]
        result[name] = {
            "observations": int(finite.size),
            "total_seconds": None if finite.size == 0 else float(np.sum(finite)),
            "mean_seconds_per_replica_standpoint": None if finite.size == 0 else float(np.mean(finite)),
        }
    return result


def _city_data(city: str, campaign: _Campaign, looks: Sequence[int] | None) -> dict[str, Any]:
    _require_current_iid(campaign)
    selected_looks = _available_looks(campaign, looks)
    rows = _point_rows(campaign)
    cdfs = {
        key: _cdf(np.asarray([np.nan if row[key] is None else row[key] for row in rows], dtype=np.float64))
        for key, _label, _unit in _ROUTE_METRICS
    }
    configuration = campaign.identity_data.get("configuration", {})
    topology = (
        {}
        if campaign.schema_version == SCHEMA_VERSION
        else {"transport_topology": campaign.transport_topology, "components": list(campaign.components)}
    )
    return {
        "city": city,
        **topology,
        "provenance": {
            "directory": str(campaign.root),
            "campaign_schema_version": campaign.schema_version,
            "campaign_identity_sha256": campaign.identity["sha256"],
            "campaign_manifest_sha256": _sha256(campaign.root / "manifest.json"),
            "launch_sampling": campaign.sampling,
        },
        "contract": {
            "cohort": configuration.get("cohort"),
            "route_contract": configuration.get("route_contract"),
            "material_mode": configuration.get("material_mode"),
            "reference_mode": configuration.get("reference_mode"),
            "specular_acceptance": configuration.get("specular_acceptance"),
        },
        "replicas": len(campaign.seeds),
        "seeds": list(campaign.seeds),
        "standpoints": campaign.points,
        "route": rows,
        "route_cdf": cdfs,
        "convergence": _convergence_rows(campaign, selected_looks)[0],
        "route_quantile_uncertainty": _bootstrap_route_uncertainty(campaign),
        "tail_instability": _tail_instability(campaign, selected_looks),
        "timings": _timings(campaign),
    }


def build_multicity_results(
    campaigns: Mapping[str, _Campaign], *, looks: Sequence[int] | None = None
) -> dict[str, Any]:
    """Build report data from campaigns already loaded by the strict reader."""
    if not campaigns:
        raise ValueError("at least one campaign is required")
    cities = {city: _city_data(city, campaign, looks) for city, campaign in campaigns.items()}
    topology_metadata = (
        {}
        if all(campaign.schema_version == SCHEMA_VERSION for campaign in campaigns.values())
        else {
            "transport_topologies": {
                city: {
                    "transport_topology": campaign.transport_topology,
                    "components": list(campaign.components),
                }
                for city, campaign in campaigns.items()
            }
        }
    )
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "metadata": {
            "caption": (
                "Current single-IID roofline campaigns. Exposure values are normalized per unit rho_A P_EIRP "
                "and are not deployment-absolute values."
            ),
            "normalization": NORMALIZATION,
            "transport_scope": "direct plus stochastic and specular transport under each sealed campaign contract",
            "route_metric_definitions": {key: {"label": label, "unit": unit} for key, label, unit in _ROUTE_METRICS},
            "peak_definitions": {
                "peak_sab_ensemble_field": "body-surface maximum after averaging the per-element Sab field",
                "peak_sab_mean_per_replica": "arithmetic mean of each replica's body-surface maximum Sab",
            },
            "cdf_plotting_position": "(rank - 0.5) / number of route standpoints",
            "uncertainty_scope": (
                "bootstrap intervals quantify finite-replica uncertainty conditional on the fixed registered route; "
                "they do not quantify route-selection or city-sampling uncertainty"
            ),
            **topology_metadata,
        },
        "cities": cities,
    }


def _write_csv(path: Path, data: Mapping[str, Any]) -> None:
    first_interaction = any("components" in campaign for campaign in data["cities"].values())
    topology_fields = (
        (
            "transport_topology",
            "campaign_components",
            "raw_all_specular_transfer_m_inv2",
            "raw_first_diffuse_transfer_m_inv2",
        )
        if first_interaction
        else ()
    )
    fieldnames = (
        "city",
        "campaign_identity_sha256",
        "replicas",
        *topology_fields,
        "standpoint",
        "x_m",
        "y_m",
        "z_m",
        "route_distance_m",
        *[key for key, _label, _unit in _ROUTE_METRICS],
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for city, campaign in data["cities"].items():
            for row in campaign["route"]:
                x_m, y_m, z_m = row["position_m"]
                component_raw = row.get("component_raw_transfer_m_inv2", {})
                writer.writerow(
                    {
                        "city": city,
                        "campaign_identity_sha256": campaign["provenance"]["campaign_identity_sha256"],
                        "replicas": campaign["replicas"],
                        **(
                            {
                                "transport_topology": campaign.get("transport_topology", "hybrid_max_bounces_v1"),
                                "campaign_components": ",".join(
                                    campaign.get("components", ["direct", "specular", "diffuse", "total"])
                                ),
                                "raw_all_specular_transfer_m_inv2": component_raw.get("all_specular"),
                                "raw_first_diffuse_transfer_m_inv2": component_raw.get("first_diffuse"),
                            }
                            if first_interaction
                            else {}
                        ),
                        "standpoint": row["standpoint"],
                        "x_m": x_m,
                        "y_m": y_m,
                        "z_m": z_m,
                        **{key: row[key] for key, _label, _unit in _ROUTE_METRICS},
                    }
                )


def _plot(data: Mapping[str, Any], pdf: Path, png: Path) -> None:
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 2, figsize=(11.5, 7.4))
    cdf_panels = (
        (axes[0, 0], "wbsar", r"Normalized whole-body SAR (m$^2$ kg$^{-1}$)"),
        (axes[0, 1], "peak_sab_mean_per_replica", "Normalized mean per-replica peak $S_{ab}$"),
        (axes[1, 0], "multipath_surplus_db", "Multipath surplus (dB)"),
    )
    colors = plt.get_cmap("tab10")
    for city_index, (city, campaign) in enumerate(data["cities"].items()):
        color = colors(city_index % 10)
        for axis, metric, xlabel in cdf_panels:
            cdf = campaign["route_cdf"][metric]
            axis.plot(cdf["x"], cdf["probability"], drawstyle="steps-post", lw=1.8, color=color, label=city)
            uncertainty = campaign["route_quantile_uncertainty"]["quantiles"].get(metric)
            if uncertainty is not None:
                for quantile_key, probability in (("q50", 0.50), ("q90", 0.90)):
                    estimate = uncertainty[quantile_key]["estimate"]
                    interval = uncertainty[quantile_key]["ci95_percentile"]
                    if estimate is not None and interval is not None:
                        axis.hlines(probability, interval[0], interval[1], color=color, lw=1.0, zorder=4)
                        axis.plot(estimate, probability, "o", ms=3.0, color=color, zorder=5)
            axis.set_xlabel(xlabel)
            axis.set_ylabel("Route CDF")
            axis.set_ylim(0.0, 1.0)
            axis.grid(alpha=0.22)
        transitions = campaign["convergence"]["look_to_look"]
        x = [row["to_replicas"] for row in transitions]
        y = [row["wbsar"]["maximum_abs_db"] for row in transitions]
        axes[1, 1].plot(x, y, marker="o", ms=3.5, lw=1.6, color=color, label=city)
        central = [row["route_quantile_abs_change_db"]["q50"] for row in campaign["tail_instability"]["look_to_look"]]
        axes[1, 1].plot(x, central, ls="--", lw=1.2, color=color)

    for axis in (axes[0, 0], axes[0, 1]):
        positive = [line.get_xdata() for line in axis.lines if np.all(np.asarray(line.get_xdata()) > 0.0)]
        if positive and len(positive) == len(axis.lines):
            axis.set_xscale("log")
    axes[1, 1].set_xlabel("Replicas in current look")
    axes[1, 1].set_ylabel("Maximum route wbSAR change (dB)")
    axes[1, 1].grid(alpha=0.22)
    axes[1, 1].text(
        0.02,
        0.98,
        "solid: max pointwise\ndashed: route q50",
        transform=axes[1, 1].transAxes,
        va="top",
        fontsize=8,
    )
    zero_direct = [
        f"{city}: {len(campaign['tail_instability']['zero_direct_standpoints'])}"
        for city, campaign in data["cities"].items()
        if campaign["tail_instability"]["zero_direct_standpoints"]
    ]
    if zero_direct:
        axes[1, 0].text(
            0.02,
            0.98,
            "zero-direct points omitted from surplus CDF\n" + ", ".join(zero_direct),
            transform=axes[1, 0].transAxes,
            va="top",
            fontsize=8,
        )
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.suptitle("Current normalized roofline campaigns", y=0.985)
    figure.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.955),
        ncol=min(5, len(labels)),
        frameon=False,
    )
    figure.text(
        0.5,
        0.012,
        "CDF circles show q50/q90 replica-bootstrap 95% intervals. Worst-point convergence remains visible.",
        ha="center",
        fontsize=8,
    )
    figure.tight_layout(rect=(0.0, 0.035, 1.0, 0.9))
    figure.savefig(pdf, bbox_inches="tight")
    figure.savefig(png, dpi=220, bbox_inches="tight")
    plt.close(figure)


def _write_artifact_manifest(path: Path, artifacts: Iterable[Path], data: Mapping[str, Any]) -> None:
    records = {artifact.name: {"sha256": _sha256(artifact), "bytes": artifact.stat().st_size} for artifact in artifacts}
    source_campaigns = {
        city: {
            "campaign_identity_sha256": campaign["provenance"]["campaign_identity_sha256"],
            "campaign_manifest_sha256": campaign["provenance"]["campaign_manifest_sha256"],
            **(
                {
                    "transport_topology": campaign["transport_topology"],
                    "components": campaign["components"],
                }
                if "transport_topology" in campaign
                else {}
            ),
        }
        for city, campaign in data["cities"].items()
    }
    payload = {
        "schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "sources": source_campaigns,
        "artifacts": records,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_multicity_results(
    inputs: Sequence[CampaignInput], output_prefix: str | Path, *, looks: Sequence[int] | None = None
) -> MulticityArtifacts:
    """Validate campaigns and write JSON, CSV, PDF, PNG, and a hash manifest."""
    if not inputs:
        raise ValueError("at least one --city campaign is required")
    names = [item.city.strip() for item in inputs]
    if any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("city names must be non-empty and unique")
    loaded = {name: _load_campaign(item.directory) for name, item in zip(names, inputs, strict=True)}
    data = build_multicity_results(loaded, looks=looks)

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    artifacts = MulticityArtifacts(
        json=prefix.with_suffix(".json"),
        csv=prefix.with_suffix(".csv"),
        pdf=prefix.with_suffix(".pdf"),
        png=prefix.with_suffix(".png"),
        manifest=prefix.with_name(prefix.name + "_manifest.json"),
    )
    artifacts.json.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    _write_csv(artifacts.csv, data)
    _plot(data, artifacts.pdf, artifacts.png)
    _write_artifact_manifest(
        artifacts.manifest,
        (artifacts.json, artifacts.csv, artifacts.pdf, artifacts.png),
        data,
    )
    return artifacts


__all__ = [
    "CampaignInput",
    "MulticityArtifacts",
    "build_multicity_results",
    "write_multicity_results",
]
