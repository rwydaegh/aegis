"""Render the main-paper fixed-route exposure result figure.

The only scientific input is the authenticated current five-city aggregate.
The script validates its campaign and component contracts before writing a
two-column PDF, a PNG review companion, and a compact JSON data audit.

Run from any directory with::

    uv run --project /home/user/tools/devpc-python \
        semantic_twin/paper/figures/results/results.py
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


HERE = Path(__file__).resolve().parent
SEMANTIC_TWIN_ROOT = Path(__file__).resolve().parents[3]
SOURCE = (
    SEMANTIC_TWIN_ROOT
    / "outputs"
    / "roofline_campaign"
    / "current_five_city_first_material_interaction"
    / "current_five_city_first_material_interaction.json"
)
OUTPUT_STEM = HERE / "results"
AUDIT_PATH = HERE / "results_data_audit.json"

SCHEMA_VERSION = "roofline_multicity_results_v1"
TOPOLOGY = "first_material_interaction_v1"
COMPONENTS = ("direct", "all_specular", "first_diffuse", "total")
ADDITIVE_COMPONENTS = COMPONENTS[:-1]
EXPECTED_SEEDS = tuple(range(7, 23))
EXPECTED_TOTAL_STANDPOINTS = 73
BODY_ADDITIVE_METRICS = (
    "absorbed_power_w",
    "arriving_power_density_w_m2",
    "mean_sab_w_m2",
    "sar_wb_w_kg",
    "susceptibility",
)

# Saturated house palette, with line shape and marker redundancy for print.
CITY_STYLES = {
    "Korenmarkt": {
        "label": "Ghent",
        "colour": "#000000",
        "linestyle": "-",
        "marker": "o",
    },
    "Prague": {
        "label": "Prague",
        "colour": "#FF0000",
        "linestyle": "--",
        "marker": "s",
    },
    "Madrid": {
        "label": "Madrid",
        "colour": "#00C000",
        "linestyle": "-.",
        "marker": "^",
    },
    "Mexico": {
        "label": "Mexico City",
        "colour": "#0000FF",
        "linestyle": ":",
        "marker": "D",
    },
    "Tokyo": {
        "label": "Tokyo Hachiko",
        "colour": "#FF7F00",
        "linestyle": (0, (3, 1, 1, 1)),
        "marker": "v",
    },
}
CITY_ORDER = tuple(CITY_STYLES)


def _ecdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return the aggregate's midpoint empirical-CDF convention."""
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    assert ordered.size > 0
    probability = (np.arange(ordered.size, dtype=np.float64) + 0.5) / ordered.size
    return ordered, probability


def _relative_error(observed: float, expected: float) -> float:
    scale = max(abs(observed), abs(expected), np.finfo(np.float64).tiny)
    return abs(observed - expected) / scale


def _quantiles(values: np.ndarray) -> dict[str, float]:
    return {
        "minimum": float(np.min(values)),
        "p05": float(np.quantile(values, 0.05)),
        "median": float(np.median(values)),
        "p95": float(np.quantile(values, 0.95)),
        "maximum": float(np.max(values)),
    }


def _validate_and_audit(payload: dict[str, Any]) -> dict[str, Any]:
    """Refuse any aggregate outside the sealed publication contract."""
    assert payload.get("schema_version") == SCHEMA_VERSION
    assert set(payload) == {"schema_version", "metadata", "cities"}
    assert set(payload["cities"]) == set(CITY_ORDER)
    assert payload["metadata"]["normalization"] == "per unit rho_A P_EIRP"
    assert payload["metadata"]["cdf_plotting_position"] == ("(rank - 0.5) / number of route standpoints")

    audit_cities: dict[str, Any] = {}
    total_standpoints = 0
    total_finite_surplus = 0
    total_zero_direct = 0
    raw_max_relative_error = 0.0
    body_max_relative_error = 0.0

    for city_name in CITY_ORDER:
        city = payload["cities"][city_name]
        assert city["city"] == city_name
        assert city["transport_topology"] == TOPOLOGY
        assert tuple(city["components"]) == COMPONENTS
        assert city["replicas"] == len(EXPECTED_SEEDS) == 16
        assert tuple(city["seeds"]) == EXPECTED_SEEDS
        assert city["contract"] == {
            "cohort": "comparable_city",
            "material_mode": "atlas",
            "reference_mode": "per_density_eirp",
            "route_contract": "provider_corridor_v1",
            "specular_acceptance": "first_material_interaction_exact_order_1",
        }
        provenance = city["provenance"]
        assert provenance["campaign_schema_version"] == ("roofline_body_campaign_first_material_interaction_v1")
        assert provenance["launch_sampling"] == "iid"
        for digest_key in ("campaign_identity_sha256", "campaign_manifest_sha256"):
            assert re.fullmatch(r"[0-9a-f]{64}", provenance[digest_key])
        metadata_topology = payload["metadata"]["transport_topologies"][city_name]
        assert metadata_topology == {
            "components": list(COMPONENTS),
            "transport_topology": TOPOLOGY,
        }

        route = city["route"]
        assert city["standpoints"] == len(route)
        assert [point["standpoint"] for point in route] == list(range(len(route)))
        total_standpoints += len(route)

        derived_zero_direct: list[int] = []
        wb_sar: list[float] = []
        finite_surplus: list[float] = []
        for index, point in enumerate(route):
            raw = point["component_raw_transfer_m_inv2"]
            body = point["component_body"]
            assert set(raw) == set(COMPONENTS)
            assert set(body) == set(COMPONENTS)
            assert all(raw[component] >= 0.0 for component in COMPONENTS)

            raw_sum = sum(raw[component] for component in ADDITIVE_COMPONENTS)
            raw_error = _relative_error(raw["total"], raw_sum)
            raw_max_relative_error = max(raw_max_relative_error, raw_error)
            assert np.isclose(raw["total"], raw_sum, rtol=1.0e-12, atol=1.0e-15)
            assert np.isclose(point["raw_direct_transfer_m_inv2"], raw["direct"], rtol=0.0, atol=0.0)
            assert np.isclose(point["raw_total_transfer_m_inv2"], raw["total"], rtol=0.0, atol=0.0)

            body_metric_names = set(body["total"])
            assert body_metric_names == set(BODY_ADDITIVE_METRICS) | {"peak_sab_w_m2"}
            assert all(set(body[component]) == body_metric_names for component in COMPONENTS)
            for metric in BODY_ADDITIVE_METRICS:
                component_sum = sum(body[component][metric] for component in ADDITIVE_COMPONENTS)
                body_error = _relative_error(body["total"][metric], component_sum)
                body_max_relative_error = max(body_max_relative_error, body_error)
                assert np.isclose(body["total"][metric], component_sum, rtol=1.0e-12, atol=1.0e-12)

            value = float(point["wbsar"])
            assert value > 0.0
            assert np.isclose(value, body["total"]["sar_wb_w_kg"], rtol=0.0, atol=0.0)
            wb_sar.append(value)

            if raw["direct"] == 0.0:
                derived_zero_direct.append(index)
                assert point["multipath_surplus_db"] is None
            else:
                surplus = float(point["multipath_surplus_db"])
                assert np.isfinite(surplus)
                recomputed = 10.0 * np.log10(raw["total"] / raw["direct"])
                assert np.isclose(surplus, recomputed, rtol=1.0e-12, atol=1.0e-12)
                finite_surplus.append(surplus)

        declared_zero_direct = city["tail_instability"]["zero_direct_standpoints"]
        assert derived_zero_direct == declared_zero_direct
        assert len(finite_surplus) + len(derived_zero_direct) == len(route)
        total_finite_surplus += len(finite_surplus)
        total_zero_direct += len(derived_zero_direct)

        wb_array = np.asarray(wb_sar, dtype=np.float64)
        surplus_array = np.asarray(finite_surplus, dtype=np.float64)
        audit_cities[city_name] = {
            "figure_label": CITY_STYLES[city_name]["label"],
            "registered_standpoints": len(route),
            "replicas": city["replicas"],
            "sealed_campaign_provenance": {
                "identity_sha256": provenance["campaign_identity_sha256"],
                "manifest_sha256": provenance["campaign_manifest_sha256"],
            },
            "whole_body_sar_m2_per_kg": _quantiles(wb_array),
            "multipath_surplus_db_finite": {
                "count": int(surplus_array.size),
                **_quantiles(surplus_array),
            },
            "structural_zero_direct": {
                "count": len(derived_zero_direct),
                "standpoint_indices": derived_zero_direct,
                "fraction_of_city_route": len(derived_zero_direct) / len(route),
            },
        }

    assert total_standpoints == EXPECTED_TOTAL_STANDPOINTS
    assert total_zero_direct == 6
    assert total_finite_surplus == EXPECTED_TOTAL_STANDPOINTS - total_zero_direct == 67

    all_wb_sar = np.asarray(
        [point["wbsar"] for city in payload["cities"].values() for point in city["route"]],
        dtype=np.float64,
    )
    return {
        "audit_schema_version": "fixed_route_results_figure_audit_v1",
        "source": {
            "path_from_semantic_twin_root": str(SOURCE.relative_to(SEMANTIC_TWIN_ROOT)),
            "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "aggregate_schema_version": SCHEMA_VERSION,
        },
        "campaign_contract": {
            "transport_topology": TOPOLOGY,
            "components": list(COMPONENTS),
            "normalization": payload["metadata"]["normalization"],
            "route_scope": "fixed registered routes, not population samples",
            "replicas_per_city": 16,
            "seeds": list(EXPECTED_SEEDS),
            "cities": [CITY_STYLES[name]["label"] for name in CITY_ORDER],
        },
        "integrity": {
            "schema_validated": True,
            "city_contracts_validated": True,
            "topology_and_components_validated": True,
            "component_conservation_validated": True,
            "body_additive_metrics_validated": list(BODY_ADDITIVE_METRICS),
            "body_peak_not_additive": (
                "peak absorbed power density is a spatial maximum and is not subject to component-sum conservation"
            ),
            "raw_component_sum_max_relative_error": raw_max_relative_error,
            "body_component_sum_max_relative_error": body_max_relative_error,
        },
        "claims": {
            "registered_standpoints": total_standpoints,
            "finite_multipath_surplus_standpoints": total_finite_surplus,
            "structural_zero_direct_standpoints": total_zero_direct,
            "structural_zero_direct_fraction": total_zero_direct / total_standpoints,
            "pooled_fixed_route_whole_body_sar_m2_per_kg": _quantiles(all_wb_sar),
            "pooled_whole_body_sar_dynamic_range_db": float(10.0 * np.log10(np.max(all_wb_sar) / np.min(all_wb_sar))),
            "cities": audit_cities,
        },
        "figure_semantics": {
            "left_panel": "all registered fixed-route standpoints",
            "right_panel": (
                "finite multipath surplus only; six structural zero-direct standpoints are "
                "explicitly counted in the panel annotation"
            ),
            "cdf_plotting_position": payload["metadata"]["cdf_plotting_position"],
        },
    }


def _apply_style() -> None:
    use_tex = shutil.which("latex") is not None and shutil.which("dvipng") is not None
    mpl.rcParams.update(
        {
            "text.usetex": use_tex,
            "font.family": "serif",
            "font.serif": ["cmr10", "Computer Modern Roman", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "axes.formatter.use_mathtext": True,
            "axes.unicode_minus": False,
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "legend.fontsize": 7.0,
            "xtick.labelsize": 7.0,
            "ytick.labelsize": 7.0,
            "lines.linewidth": 1.2,
            "lines.markersize": 3.8,
            "lines.markeredgewidth": 0.9,
            "axes.linewidth": 0.6,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "xtick.minor.width": 0.45,
            "ytick.minor.width": 0.45,
            "legend.frameon": True,
            "legend.edgecolor": "black",
            "legend.fancybox": False,
            "legend.framealpha": 0.92,
            "legend.borderpad": 0.25,
            "legend.handlelength": 1.6,
            "legend.handletextpad": 0.5,
            "legend.labelspacing": 0.3,
            "figure.dpi": 200,
            # Preserve the exact 7.16 in IEEE double-column canvas. All artists
            # are laid out inside it, so a tight bounding box must not widen it.
            "savefig.bbox": None,
            "pdf.fonttype": 42,
        }
    )


def _draw(payload: dict[str, Any]) -> None:
    _apply_style()
    figure, (sar_axis, surplus_axis) = plt.subplots(1, 2, figsize=(7.16, 3.05))

    for city_name in CITY_ORDER:
        city = payload["cities"][city_name]
        style = CITY_STYLES[city_name]
        common = {
            "where": "post",
            "color": style["colour"],
            "linestyle": style["linestyle"],
            "marker": style["marker"],
            "markerfacecolor": "none",
            "markeredgewidth": 0.9,
        }
        wb_sar = np.asarray([point["wbsar"] for point in city["route"]], dtype=np.float64)
        x, y = _ecdf(wb_sar)
        sar_axis.step(x, y, label=style["label"], **common)

        finite_surplus = np.asarray(
            [point["multipath_surplus_db"] for point in city["route"] if point["multipath_surplus_db"] is not None],
            dtype=np.float64,
        )
        x, y = _ecdf(finite_surplus)
        surplus_axis.step(x, y, **common)

    sar_axis.set_xscale("log")
    sar_ticks = [1.0e-6, 1.0e-5, 1.0e-4, 1.0e-3, 1.0e-2, 1.0e-1, 1.0]
    sar_axis.set_xticks(sar_ticks)
    sar_axis.set_xticklabels(["0.000001", "0.00001", "0.0001", "0.001", "0.01", "0.1", "1"])
    sar_axis.set_xlim(5.0e-7, 1.1)
    sar_axis.set_xlabel(r"normalized whole-body SAR [m$^2$ kg$^{-1}$]")
    sar_axis.set_ylabel("fixed-route empirical CDF [1]")

    surplus_axis.set_xlim(0.0, 2.0)
    surplus_axis.set_xticks([0.0, 0.5, 1.0, 1.5, 2.0])
    surplus_axis.set_xlabel("multipath surplus [dB]")
    surplus_axis.set_ylabel("fixed-route empirical CDF [1]")
    surplus_axis.text(
        0.5,
        1.025,
        "zero-direct points omitted from surplus (6 total):\nMexico City 3/11; Tokyo Hachiko 3/16",
        transform=surplus_axis.transAxes,
        ha="center",
        va="bottom",
        fontsize=6.2,
        color="0.25",
    )

    for label, axis in zip(("(a)", "(b)"), (sar_axis, surplus_axis)):
        axis.set_ylim(0.0, 1.0)
        axis.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
        axis.grid(True, color="0.86", linewidth=0.45, zorder=0)
        axis.text(0.02, 0.97, label, transform=axis.transAxes, ha="left", va="top")

    handles, labels = sar_axis.get_legend_handles_labels()
    legend = figure.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=5,
        columnspacing=1.2,
    )
    legend.get_frame().set_linewidth(1.0)
    legend.get_frame().set_edgecolor("black")
    figure.subplots_adjust(left=0.075, right=0.99, bottom=0.19, top=0.81, wspace=0.28)

    figure.savefig(OUTPUT_STEM.with_suffix(".pdf"))
    figure.savefig(OUTPUT_STEM.with_suffix(".png"), dpi=300)
    plt.close(figure)


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    audit = _validate_and_audit(payload)
    _draw(payload)
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    claims = audit["claims"]
    print(f"source sha256: {audit['source']['sha256']}")
    print(
        "validated: "
        f"{claims['registered_standpoints']} route points, "
        f"{claims['finite_multipath_surplus_standpoints']} finite surplus values, "
        f"{claims['structural_zero_direct_standpoints']} structural zero-direct points"
    )
    for city_name in CITY_ORDER:
        city = claims["cities"][city_name]
        sar = city["whole_body_sar_m2_per_kg"]
        surplus = city["multipath_surplus_db_finite"]
        zeros = city["structural_zero_direct"]["count"]
        print(
            f"{city['figure_label']}: n={city['registered_standpoints']}, "
            f"whole-body SAR median={sar['median']:.9g} m^2 kg^-1, "
            f"finite surplus n={surplus['count']}, median={surplus['median']:.6g} dB, "
            f"zero direct={zeros}"
        )
    print(f"wrote {OUTPUT_STEM.with_suffix('.pdf')}")
    print(f"wrote {OUTPUT_STEM.with_suffix('.png')}")
    print(f"wrote {AUDIT_PATH}")


if __name__ == "__main__":
    main()
