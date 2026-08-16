"""Authenticated summaries for the ten-site geometric fixed-grid screen.

This report is deliberately separate from the registered-path multicity
report. The 16 locations at each site are a deterministic ground-grid sample,
not a pedestrian path. The resulting distributions are screening quantities
conditional on that grid, geometric materials, and a north-facing body.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from semantic_twin.exposure.roofline_campaign import (
    BODY_METRICS,
    FIRST_MATERIAL_INTERACTION_COMPONENTS,
    FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION,
    TIMING_FIELDS,
)

from .roofline_campaign_comparison import CampaignComparisonError, _Campaign, _load_campaign

SCREENING_CONTRACT = "geometric_fixed_grid_screening_v1"
GRID_CONTRACT = "fixed_ground_grid_v1"
REPORT_SCHEMA_VERSION = "geometric_fixed_grid_screening_report_v1"
ARTIFACT_MANIFEST_SCHEMA_VERSION = "geometric_fixed_grid_screening_artifacts_v1"
EXPECTED_SITES = (
    "korenmarkt",
    "prague_staromestske",
    "brussels_grandplace",
    "madrid_plazamayor",
    "mexico_zocalo",
    "tokyo_hachiko",
    "london_trafalgar",
    "milan_duomo",
    "krakow_rynek",
    "toulouse_capitole",
)
DISPLAY_NAMES = {
    "korenmarkt": "Ghent",
    "prague_staromestske": "Prague",
    "brussels_grandplace": "Brussels",
    "madrid_plazamayor": "Madrid",
    "mexico_zocalo": "Mexico City",
    "tokyo_hachiko": "Tokyo",
    "london_trafalgar": "London",
    "milan_duomo": "Milan",
    "krakow_rynek": "Krakow",
    "toulouse_capitole": "Toulouse",
}
EXPECTED_SEEDS = (7, 8, 9, 10)
EXPECTED_POINTS = 16
EXPECTED_COMPONENTS = tuple(FIRST_MATERIAL_INTERACTION_COMPONENTS)
QUANTILES = (("q10", 0.10), ("q50", 0.50), ("q90", 0.90))
NORMALIZATION = "per unit rho_A P_EIRP"
FIXED_YAW_DEG = 0.0
ADDITIVE_BODY_METRICS = tuple(name for name in BODY_METRICS if name != "peak_sab_w_m2")


class GeometricGridScreeningError(CampaignComparisonError):
    """A campaign set does not satisfy the fixed-grid screening contract."""


@dataclass(frozen=True)
class CampaignInput:
    """One sealed site identifier and completed campaign directory."""

    site: str
    directory: Path


@dataclass(frozen=True)
class GeometricGridScreeningArtifacts:
    """Files written by :func:`write_geometric_grid_screening`."""

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


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _configuration(campaign: _Campaign) -> dict[str, Any]:
    value = campaign.identity_data.get("configuration")
    if not isinstance(value, dict):
        raise GeometricGridScreeningError(f"campaign identity has no configuration object: {campaign.root}")
    return value


def _object(value: Any, *, name: str, campaign: _Campaign) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GeometricGridScreeningError(f"campaign identity has no {name} object: {campaign.root}")
    return value


def _require_equal(actual: Any, expected: Any, *, name: str, campaign: _Campaign) -> None:
    if actual != expected:
        raise GeometricGridScreeningError(
            f"screening contract requires {name}={expected!r}, got {actual!r}: {campaign.root}"
        )


def _validate_configuration(site: str, campaign: _Campaign) -> None:
    configuration = _configuration(campaign)
    exact = {
        "site": site,
        "cohort": "geometric_fixed_grid_screening",
        "material_mode": "geometric",
        "sampling_claim": SCREENING_CONTRACT,
        "grid_contract": GRID_CONTRACT,
        "planned_seeds": list(EXPECTED_SEEDS),
        "convergence_looks": [4],
        "schema_version": FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION,
        "transport_topology": "first_material_interaction_v1",
        "components": list(EXPECTED_COMPONENTS),
        "specular_acceptance": "first_material_interaction_exact_order_1",
        "minimum_completed_specular_order": 1,
        "reference_mode": "per_density_eirp",
    }
    for name, expected in exact.items():
        _require_equal(configuration.get(name), expected, name=f"configuration.{name}", campaign=campaign)
    if configuration.get("route_contract") is not None:
        raise GeometricGridScreeningError(
            f"fixed-grid screening must not seal a pedestrian-path contract: {campaign.root}"
        )
    _require_equal(campaign.schema_version, FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION, name="schema", campaign=campaign)
    _require_equal(campaign.components, EXPECTED_COMPONENTS, name="components", campaign=campaign)
    _require_equal(campaign.seeds, EXPECTED_SEEDS, name="completed seeds", campaign=campaign)
    _require_equal(campaign.planned_seeds, EXPECTED_SEEDS, name="planned seeds", campaign=campaign)
    _require_equal(campaign.points, EXPECTED_POINTS, name="grid-point count", campaign=campaign)
    _require_equal(campaign.sampling, "iid", name="launch sampling", campaign=campaign)


def _validate_transport(campaign: _Campaign) -> None:
    transport = _object(campaign.identity_data.get("transport"), name="transport", campaign=campaign)
    tracer = _object(transport.get("tracer"), name="transport.tracer", campaign=campaign)
    tracer_configuration = _object(
        tracer.get("configuration"), name="transport.tracer.configuration", campaign=campaign
    )
    for name, expected in {
        "frequency_hz": 15_000_000_000,
        "rays": 200_000,
        "local_cells": 4096,
        "max_bounces": 1,
    }.items():
        _require_equal(tracer_configuration.get(name), expected, name=f"tracer.{name}", campaign=campaign)
    if tracer.get("atlas_material") is not None:
        raise GeometricGridScreeningError(f"geometric screening must not bind an atlas: {campaign.root}")

    estimator = _object(transport.get("estimator"), name="transport.estimator", campaign=campaign)
    estimator_configuration = _object(
        estimator.get("configuration"), name="transport.estimator.configuration", campaign=campaign
    )
    for name, expected in {
        "transport_topology": "first_material_interaction_v1",
        "max_order": 1,
        "specular_order": 1,
        "specular_suffix_mode": "disabled",
    }.items():
        _require_equal(estimator_configuration.get(name), expected, name=f"estimator.{name}", campaign=campaign)


def _validate_materials_and_body(campaign: _Campaign) -> None:
    materials = _object(campaign.identity_data.get("materials"), name="materials", campaign=campaign)
    _require_equal(materials.get("material_mode"), "geometric", name="materials.material_mode", campaign=campaign)
    _require_equal(materials.get("atlas_material_present"), False, name="atlas_material_present", campaign=campaign)
    binding = _object(materials.get("binding"), name="materials.binding", campaign=campaign)
    _require_equal(binding.get("materials"), "geometric", name="materials.binding.materials", campaign=campaign)

    body = _object(campaign.identity_data.get("body"), name="body", campaign=campaign)
    for name, expected in {
        "phantom": "duke",
        "level": 2,
        "frequency_hz": 15_000_000_000,
        "surface_elements": 56_024,
    }.items():
        _require_equal(body.get(name), expected, name=f"body.{name}", campaign=campaign)


def _validate_grid(site: str, campaign: _Campaign) -> None:
    walk = _object(campaign.identity_data.get("walk"), name="walk", campaign=campaign)
    for name, expected in {
        "walk_kind": "grid",
        "walk_site": site,
        "standpoints": EXPECTED_POINTS,
    }.items():
        _require_equal(walk.get(name), expected, name=f"walk.{name}", campaign=campaign)
    provenance = _object(walk.get("provenance"), name="walk.provenance", campaign=campaign)
    for name, expected in {
        "sampling_claim": SCREENING_CONTRACT,
        "grid_contract": GRID_CONTRACT,
        "selection_count": EXPECTED_POINTS,
        "body_yaw_rule": "fixed_north_v1",
        "spacing_m": 6.0,
        "radius_m": 90.0,
    }.items():
        _require_equal(provenance.get(name), expected, name=f"walk.provenance.{name}", campaign=campaign)
    indices = provenance.get("selection_indices")
    if (
        not isinstance(indices, list)
        or len(indices) != EXPECTED_POINTS
        or any(isinstance(index, bool) or not isinstance(index, int) or index < 0 for index in indices)
        or indices != sorted(set(indices))
    ):
        raise GeometricGridScreeningError(f"grid selection_indices are not 16 unique ordered indices: {campaign.root}")
    full_count = provenance.get("full_grid_standpoints")
    if isinstance(full_count, bool) or not isinstance(full_count, int) or full_count < EXPECTED_POINTS:
        raise GeometricGridScreeningError(f"full grid has invalid standpoint metadata: {campaign.root}")
    if not _is_sha256(provenance.get("full_grid_points_sha256")):
        raise GeometricGridScreeningError(f"full grid has no valid point-array digest: {campaign.root}")
    _require_equal(
        provenance.get("point_kind"),
        ["fixed_ground_grid"] * EXPECTED_POINTS,
        name="walk.provenance.point_kind",
        campaign=campaign,
    )
    _require_equal(
        provenance.get("body_yaw_deg"),
        [FIXED_YAW_DEG] * EXPECTED_POINTS,
        name="walk.provenance.body_yaw_deg",
        campaign=campaign,
    )

    positions = np.asarray([row["position_m"] for row in campaign.locations], dtype=np.float64)
    yaws = np.asarray([row.get("body_yaw_deg") for row in campaign.locations], dtype=np.float64)
    if positions.shape != (EXPECTED_POINTS, 3) or np.any(~np.isfinite(positions)):
        raise GeometricGridScreeningError(f"grid positions are not a finite 16 by 3 array: {campaign.root}")
    if yaws.shape != (EXPECTED_POINTS,) or not np.array_equal(yaws, np.zeros(EXPECTED_POINTS, dtype=np.float64)):
        raise GeometricGridScreeningError(f"all screening body yaws must be exactly 0 degrees north: {campaign.root}")
    for index, row in enumerate(campaign.locations):
        if row.get("site") != site or row.get("cohort") != "geometric_fixed_grid_screening":
            raise GeometricGridScreeningError(f"grid-point identity drift at index {index}: {campaign.root}")
        if row.get("point_kind") != "fixed_ground_grid":
            raise GeometricGridScreeningError(f"grid point {index} has an invalid point_kind: {campaign.root}")

    point_hash = _array_digest(positions)
    yaw_hash = _array_digest(yaws)
    for name in ("points_sha256",):
        _require_equal(walk.get(name), point_hash, name=f"walk.{name}", campaign=campaign)
    _require_equal(
        provenance.get("selected_points_sha256"),
        point_hash,
        name="walk.provenance.selected_points_sha256",
        campaign=campaign,
    )
    _require_equal(walk.get("body_yaw_sha256"), yaw_hash, name="walk.body_yaw_sha256", campaign=campaign)


def _closure(campaign: _Campaign) -> dict[str, Any]:
    total_index = campaign.components.index("total")
    component_indices = [index for index, name in enumerate(campaign.components) if name != "total"]
    raw_total = campaign.raw_transfer[:, :, total_index]
    raw_sum = np.sum(campaign.raw_transfer[:, :, component_indices], axis=2)
    raw_residual = raw_total - raw_sum
    additive_indices = [BODY_METRICS.index(name) for name in ADDITIVE_BODY_METRICS]
    body_total = campaign.body_metrics[:, :, total_index, :][:, :, additive_indices]
    body_sum = np.sum(campaign.body_metrics[:, :, component_indices, :][:, :, :, additive_indices], axis=2)
    body_residual = body_total - body_sum
    raw_pass = bool(np.allclose(raw_total, raw_sum, rtol=2.0e-10, atol=1.0e-14))
    body_pass = bool(np.allclose(body_total, body_sum, rtol=2.0e-10, atol=1.0e-14))
    if not raw_pass or not body_pass:
        raise GeometricGridScreeningError(f"component closure failed: {campaign.root}")
    return {
        "status": "pass",
        "raw_transfer_max_abs_residual": float(np.max(np.abs(raw_residual))),
        "body_metric_max_abs_residual": float(np.max(np.abs(body_residual))),
        "additive_body_metrics_checked": list(ADDITIVE_BODY_METRICS),
        "nonadditive_body_metrics_excluded": {
            "peak_sab_w_m2": "the peak of a summed body field is not the sum of component-field peaks"
        },
    }


def _seed_standard_error(values: np.ndarray) -> float:
    return float(np.std(values, ddof=1) / np.sqrt(values.size))


def _timings(campaign: _Campaign) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for index, name in enumerate(TIMING_FIELDS):
        values = campaign.timings[:, :, index]
        finite = values[np.isfinite(values)]
        if finite.size != len(EXPECTED_SEEDS) * EXPECTED_POINTS:
            raise GeometricGridScreeningError(
                f"timing field {name} is incomplete for the four-seed, 16-point contract: {campaign.root}"
            )
        fields[name] = {
            "observations": int(finite.size),
            "total_seconds": float(np.sum(finite)),
            "mean_seconds_per_seed_point": float(np.mean(finite)),
        }
    nonoverlapping = (
        fields["estimator_wall_seconds"]["total_seconds"] + fields["body_coupling_seconds"]["total_seconds"]
    )
    return {
        "scope": "persisted seed-point timings; scene preparation and report generation excluded",
        "fields": fields,
        "nonoverlapping_observed_compute_seconds": float(nonoverlapping),
    }


def _site_report(site: str, campaign: _Campaign) -> dict[str, Any]:
    _validate_configuration(site, campaign)
    _validate_transport(campaign)
    _validate_materials_and_body(campaign)
    _validate_grid(site, campaign)
    closure = _closure(campaign)

    wbsar_index = BODY_METRICS.index("sar_wb_w_kg")
    total_index = campaign.components.index("total")
    wbsar = campaign.body_metrics[:, :, total_index, wbsar_index]
    point_mean = np.mean(wbsar, axis=0)
    point_se = np.std(wbsar, axis=0, ddof=1) / np.sqrt(wbsar.shape[0])
    quantiles: dict[str, Any] = {}
    for name, probability in QUANTILES:
        seed_values = np.quantile(wbsar, probability, axis=1)
        quantiles[name] = {
            "probability": probability,
            "estimate": float(np.quantile(point_mean, probability)),
            "seed_standard_error": _seed_standard_error(seed_values),
            "seed_quantile_values": [float(value) for value in seed_values],
        }

    component_means = {
        component: float(np.mean(campaign.body_metrics[:, :, index, wbsar_index]))
        for index, component in enumerate(campaign.components)
    }
    total_mean = component_means["total"]
    if not np.isfinite(total_mean) or total_mean <= 0.0:
        raise GeometricGridScreeningError(f"pooled normalized wbSAR is not positive: {campaign.root}")
    shares = {component: component_means[component] / total_mean for component in campaign.components[:-1]}
    if not np.isclose(sum(shares.values()), 1.0, rtol=2.0e-10, atol=1.0e-14):
        raise GeometricGridScreeningError(f"normalized wbSAR component shares do not close: {campaign.root}")

    points = []
    for index, location in enumerate(campaign.locations):
        points.append(
            {
                "grid_point": index,
                "position_m": [float(value) for value in location["position_m"]],
                "body_yaw_deg": FIXED_YAW_DEG,
                "normalized_wbsar_mean": float(point_mean[index]),
                "normalized_wbsar_seed_standard_error": float(point_se[index]),
            }
        )
    return {
        "site": site,
        "authentication": {
            "status": "pass",
            "campaign_identity_sha256": campaign.identity["sha256"],
            "campaign_manifest_sha256": _sha256(campaign.root / "manifest.json"),
        },
        "seeds": list(campaign.seeds),
        "grid_points": points,
        "normalized_wbsar_quantiles": quantiles,
        "normalized_wbsar_component_means": component_means,
        "normalized_wbsar_component_shares": shares,
        "timing": _timings(campaign),
        "closure": closure,
    }


def build_geometric_grid_screening(campaigns: Mapping[str, _Campaign]) -> dict[str, Any]:
    """Validate and summarize the exact ten-site fixed-grid campaign set."""
    if len(campaigns) != len(EXPECTED_SITES) or set(campaigns) != set(EXPECTED_SITES):
        raise GeometricGridScreeningError(
            "campaigns must contain the ten screening sites exactly once: " + ", ".join(EXPECTED_SITES)
        )
    reports = {site: _site_report(site, campaigns[site]) for site in EXPECTED_SITES}
    identities = [report["authentication"]["campaign_identity_sha256"] for report in reports.values()]
    roots = [campaigns[site].root for site in EXPECTED_SITES]
    if len(set(identities)) != len(identities) or len(set(roots)) != len(roots):
        raise GeometricGridScreeningError("each site must resolve to a distinct campaign identity and directory")
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "screening_contract": {
            "name": SCREENING_CONTRACT,
            "sites": list(EXPECTED_SITES),
            "site_count": len(EXPECTED_SITES),
            "grid_contract": GRID_CONTRACT,
            "grid_points_per_site": EXPECTED_POINTS,
            "seeds": list(EXPECTED_SEEDS),
            "material_mode": "geometric",
            "body_yaw": "fixed north, 0 degrees ENU",
            "transport_topology": "first_material_interaction_v1",
            "primary_rays_per_seed_point": 200_000,
            "first_diffuse_output_cells": 4096,
            "frequency_hz": 15_000_000_000,
            "normalization": NORMALIZATION,
        },
        "authentication": {
            "status": "pass",
            "campaigns_authenticated": len(reports),
            "method": (
                "identity wrapper, manifest, checkpoint, shard hash, schema, seed, grid, yaw, material, "
                "transport, and additive component-closure checks"
            ),
        },
        "disclosures": [
            "Geometry-only material priors were used; no panorama-derived semantic evidence was used.",
            "Each site is represented by 16 deterministic points selected from a fixed walkable-ground grid.",
            "The body faces north at every point, so exposure is conditional on a fixed 0 degree ENU yaw.",
            "Four IID seeds quantify screening-scale stochastic variation and do not establish convergence.",
            "Values are normalized per unit rho_A P_EIRP and are not deployment-absolute exposures.",
            "The point sets do not support pedestrian-path, population, prevalence, or site-ranking inference.",
        ],
        "uncertainty_definition": (
            "For each spatial quantile, seed_standard_error is the sample standard deviation of the four "
            "within-seed 16-point quantiles divided by sqrt(4). It is conditional on the fixed grid and does "
            "not include spatial-design, material-model, source-model, or orientation uncertainty."
        ),
        "component_share_definition": (
            "Each share is the pooled seed-point mean normalized wbSAR for one additive first-interaction "
            "component divided by the corresponding pooled total mean."
        ),
        "sites": reports,
    }


def _write_csv(path: Path, report: Mapping[str, Any]) -> None:
    fields = (
        "site",
        "quantile",
        "probability",
        "normalized_wbsar_estimate",
        "seed_standard_error",
        "direct_share",
        "all_specular_share",
        "first_diffuse_share",
        "observed_compute_seconds",
        "campaign_identity_sha256",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for site in EXPECTED_SITES:
            site_report = report["sites"][site]
            shares = site_report["normalized_wbsar_component_shares"]
            for quantile, _probability in QUANTILES:
                summary = site_report["normalized_wbsar_quantiles"][quantile]
                writer.writerow(
                    {
                        "site": site,
                        "quantile": quantile,
                        "probability": summary["probability"],
                        "normalized_wbsar_estimate": summary["estimate"],
                        "seed_standard_error": summary["seed_standard_error"],
                        "direct_share": shares["direct"],
                        "all_specular_share": shares["all_specular"],
                        "first_diffuse_share": shares["first_diffuse"],
                        "observed_compute_seconds": site_report["timing"]["nonoverlapping_observed_compute_seconds"],
                        "campaign_identity_sha256": site_report["authentication"]["campaign_identity_sha256"],
                    }
                )


def _plot(report: Mapping[str, Any], pdf: Path, png: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        import scienceplots  # noqa: F401
    except ImportError as error:
        raise GeometricGridScreeningError("SciencePlots and matplotlib are required for the figure") from error

    plt.style.use(["science", "no-latex"])
    plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})

    figure, (distribution_axis, component_axis) = plt.subplots(1, 2, figsize=(11.2, 5.4))
    y = np.arange(len(EXPECTED_SITES))
    q10 = np.asarray(
        [report["sites"][site]["normalized_wbsar_quantiles"]["q10"]["estimate"] for site in EXPECTED_SITES]
    )
    q50 = np.asarray(
        [report["sites"][site]["normalized_wbsar_quantiles"]["q50"]["estimate"] for site in EXPECTED_SITES]
    )
    q90 = np.asarray(
        [report["sites"][site]["normalized_wbsar_quantiles"]["q90"]["estimate"] for site in EXPECTED_SITES]
    )
    q50_se = np.asarray(
        [report["sites"][site]["normalized_wbsar_quantiles"]["q50"]["seed_standard_error"] for site in EXPECTED_SITES]
    )
    distribution_axis.hlines(y, q10, q90, color="#6b7280", lw=2.4)
    distribution_axis.errorbar(q50, y, xerr=q50_se, fmt="o", color="#111827", ecolor="#dc2626", capsize=2.5)
    distribution_axis.set_yticks(y, [DISPLAY_NAMES[site] for site in EXPECTED_SITES])
    distribution_axis.invert_yaxis()
    if np.all(q10 > 0.0):
        distribution_axis.set_xscale("log")
    distribution_axis.set_xlabel(r"Normalized wbSAR per unit $\rho_A P_{EIRP}$ (m$^2$ kg$^{-1}$)")
    distribution_axis.set_title("16-point q10, q50, and q90")
    distribution_axis.grid(axis="x", alpha=0.22)

    left = np.zeros(len(EXPECTED_SITES), dtype=np.float64)
    colors = {"direct": "#2563eb", "all_specular": "#f59e0b", "first_diffuse": "#059669"}
    labels = {"direct": "Direct", "all_specular": "Order-1 specular", "first_diffuse": "First diffuse"}
    for component in ("direct", "all_specular", "first_diffuse"):
        shares = np.asarray(
            [report["sites"][site]["normalized_wbsar_component_shares"][component] for site in EXPECTED_SITES]
        )
        component_axis.barh(y, shares, left=left, color=colors[component], label=labels[component])
        left += shares
    component_axis.invert_yaxis()
    component_axis.set_yticks([])
    component_axis.set_xlim(0.0, 1.0)
    component_axis.set_xlabel("Pooled normalized wbSAR component share")
    component_axis.set_title("First-interaction decomposition")
    component_axis.legend(loc="lower center", bbox_to_anchor=(0.5, -0.20), ncol=3, frameon=False)
    component_axis.grid(axis="x", alpha=0.22)

    figure.suptitle("Geometry-only fixed-grid screening (declared site order; no ranking inference)")
    figure.text(
        0.5,
        0.01,
        "Four IID seeds; red bars show seed SE of q50. Fixed north-facing Duke phantom. Values are not absolute exposure.",
        ha="center",
        fontsize=8,
    )
    figure.tight_layout(rect=(0.0, 0.06, 1.0, 0.94))
    figure.savefig(pdf, bbox_inches="tight")
    figure.savefig(png, dpi=220, bbox_inches="tight")
    plt.close(figure)


def _write_artifact_manifest(path: Path, artifacts: Iterable[Path], report: Mapping[str, Any]) -> None:
    payload = {
        "schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "screening_contract": SCREENING_CONTRACT,
        "authenticated": True,
        "sources": {
            site: {
                "campaign_identity_sha256": report["sites"][site]["authentication"]["campaign_identity_sha256"],
                "campaign_manifest_sha256": report["sites"][site]["authentication"]["campaign_manifest_sha256"],
            }
            for site in EXPECTED_SITES
        },
        "artifacts": {
            artifact.name: {"sha256": _sha256(artifact), "bytes": artifact.stat().st_size} for artifact in artifacts
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_geometric_grid_screening(
    inputs: Sequence[CampaignInput], output_prefix: str | Path
) -> GeometricGridScreeningArtifacts:
    """Authenticate the exact campaign set and write compact report artifacts."""
    sites = tuple(item.site.strip() for item in inputs)
    if len(sites) != len(EXPECTED_SITES) or set(sites) != set(EXPECTED_SITES):
        raise GeometricGridScreeningError(
            "--campaign inputs must name the ten screening sites exactly once: " + ", ".join(EXPECTED_SITES)
        )
    loaded = {site: _load_campaign(item.directory) for site, item in zip(sites, inputs, strict=True)}
    report = build_geometric_grid_screening(loaded)

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    artifacts = GeometricGridScreeningArtifacts(
        json=prefix.with_suffix(".json"),
        csv=prefix.with_suffix(".csv"),
        pdf=prefix.with_suffix(".pdf"),
        png=prefix.with_suffix(".png"),
        manifest=prefix.with_name(prefix.name + "_manifest.json"),
    )
    artifacts.json.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _write_csv(artifacts.csv, report)
    _plot(report, artifacts.pdf, artifacts.png)
    _write_artifact_manifest(
        artifacts.manifest,
        (artifacts.json, artifacts.csv, artifacts.pdf, artifacts.png),
        report,
    )
    return artifacts


__all__ = [
    "CampaignInput",
    "EXPECTED_SITES",
    "GeometricGridScreeningArtifacts",
    "GeometricGridScreeningError",
    "build_geometric_grid_screening",
    "write_geometric_grid_screening",
]
