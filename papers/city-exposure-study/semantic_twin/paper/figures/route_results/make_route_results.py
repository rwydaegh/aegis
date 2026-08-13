#!/usr/bin/env python3
"""Render the authenticated five-city route result figure.

Run from any directory with:

    uv run --with scienceplots==2.2.1 \
        semantic_twin/paper/figures/route_results/make_route_results.py

The script refuses an aggregate that does not match the sealed manifest or
the fixed-route first-material-interaction contract. It writes a vector PDF,
a PNG review copy, and a machine-readable audit beside this file.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from importlib.metadata import version
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import scienceplots  # noqa: E402,F401
from matplotlib.lines import Line2D  # noqa: E402


HERE = Path(__file__).resolve().parent
SEMANTIC_TWIN = HERE.parents[2]
INPUT_DIRECTORY = SEMANTIC_TWIN / "outputs" / "roofline_campaign" / "current_five_city_first_material_interaction"
INPUT_JSON = INPUT_DIRECTORY / "current_five_city_first_material_interaction.json"
INPUT_MANIFEST = INPUT_DIRECTORY / "current_five_city_first_material_interaction_manifest.json"
OUTPUT_PDF = HERE / "route_results.pdf"
OUTPUT_PNG = HERE / "route_results.png"
OUTPUT_AUDIT = HERE / "route_results.json"

RESULT_SCHEMA = "roofline_multicity_results_v1"
MANIFEST_SCHEMA = "roofline_multicity_artifacts_v1"
TRANSPORT_TOPOLOGY = "first_material_interaction_v1"
SEALED_COMPONENTS = ("direct", "all_specular", "first_diffuse", "total")
ADDITIVE_COMPONENTS = SEALED_COMPONENTS[:-1]
EXPECTED_SEEDS = tuple(range(7, 23))
EXPECTED_STANDPOINTS = 73
EXPECTED_ZERO_DIRECT = {
    "Korenmarkt": (),
    "Prague": (),
    "Madrid": (),
    "Mexico": (0, 1, 3),
    "Tokyo": (13, 14, 15),
}
CITY_ORDER = tuple(EXPECTED_ZERO_DIRECT)
CITY_LABELS = {
    "Korenmarkt": "Korenmarkt",
    "Prague": "Prague",
    "Madrid": "Madrid",
    "Mexico": "Mexico City",
    "Tokyo": "Tokyo Hachiko",
}
CITY_TICK_LABELS = {
    "Korenmarkt": "Korenmarkt",
    "Prague": "Prague",
    "Madrid": "Madrid",
    "Mexico": "Mexico\nCity",
    "Tokyo": "Tokyo\nHachiko",
}
CITY_STYLES = {
    "Korenmarkt": {"color": "#000000", "linestyle": "-", "marker": "o"},
    "Prague": {"color": "#FF0000", "linestyle": "--", "marker": "s"},
    "Madrid": {"color": "#00A000", "linestyle": "-.", "marker": "^"},
    "Mexico": {"color": "#0000FF", "linestyle": ":", "marker": "D"},
    "Tokyo": {"color": "#FF7F00", "linestyle": (0, (3, 1, 1, 1)), "marker": "p"},
}
COMPONENT_STYLES = {
    "direct": {"label": "Direct", "color": "#000000", "hatch": ""},
    "all_specular": {"label": "Order-1 specular", "color": "#FF0000", "hatch": "////"},
    "first_diffuse": {"label": "First diffuse", "color": "#00A000", "hatch": "xxxx"},
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _ecdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    probability = (np.arange(ordered.size, dtype=np.float64) + 0.5) / ordered.size
    return ordered, probability


def _quantiles(values: np.ndarray) -> dict[str, float]:
    return {
        "minimum": float(np.min(values)),
        "q10": float(np.quantile(values, 0.10)),
        "median": float(np.median(values)),
        "q90": float(np.quantile(values, 0.90)),
        "maximum": float(np.max(values)),
    }


def _load_and_validate() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == MANIFEST_SCHEMA
    assert manifest["result_schema_version"] == RESULT_SCHEMA
    assert set(manifest["sources"]) == set(CITY_ORDER)
    expected_hash = manifest["artifacts"][INPUT_JSON.name]["sha256"]
    observed_hash = _sha256(INPUT_JSON)
    assert observed_hash == expected_hash

    payload = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    assert payload["schema_version"] == RESULT_SCHEMA
    assert payload["metadata"]["normalization"] == "per unit rho_A P_EIRP"
    assert payload["metadata"]["cdf_plotting_position"] == ("(rank - 0.5) / number of route standpoints")
    assert set(payload["cities"]) == set(CITY_ORDER)

    cities: dict[str, Any] = {}
    total_points = 0
    observed_zero: dict[str, tuple[int, ...]] = {}
    closure_residuals: list[float] = []
    dominance_counts = dict.fromkeys(ADDITIVE_COMPONENTS, 0)

    for city_name in CITY_ORDER:
        city = payload["cities"][city_name]
        source = manifest["sources"][city_name]
        assert city["city"] == city_name
        assert city["transport_topology"] == TRANSPORT_TOPOLOGY
        assert source["transport_topology"] == TRANSPORT_TOPOLOGY
        assert tuple(city["components"]) == SEALED_COMPONENTS
        assert tuple(source["components"]) == SEALED_COMPONENTS
        assert city["replicas"] == 16
        assert tuple(city["seeds"]) == EXPECTED_SEEDS
        assert city["contract"] == {
            "cohort": "comparable_city",
            "material_mode": "atlas",
            "reference_mode": "per_density_eirp",
            "route_contract": "provider_corridor_v1",
            "specular_acceptance": "first_material_interaction_exact_order_1",
        }

        route = city["route"]
        assert len(route) == city["standpoints"]
        assert [point["standpoint"] for point in route] == list(range(len(route)))
        assert np.all(np.diff([point["route_distance_m"] for point in route]) > 0.0)
        total_points += len(route)

        normalized_wbsar = np.asarray([point["wbsar"] for point in route], dtype=np.float64)
        assert np.isfinite(normalized_wbsar).all()
        assert np.all(normalized_wbsar > 0.0)

        body = np.asarray(
            [[point["component_body"][key]["sar_wb_w_kg"] for key in SEALED_COMPONENTS] for point in route],
            dtype=np.float64,
        )
        assert np.isfinite(body).all()
        assert np.all(body >= 0.0)
        np.testing.assert_array_equal(normalized_wbsar, body[:, -1])
        residual = body[:, :3].sum(axis=1) - body[:, 3]
        np.testing.assert_allclose(body[:, :3].sum(axis=1), body[:, 3], rtol=5e-13, atol=1e-12)
        closure_residuals.extend(residual.tolist())

        raw = np.asarray(
            [[point["component_raw_transfer_m_inv2"][key] for key in SEALED_COMPONENTS] for point in route],
            dtype=np.float64,
        )
        zero_direct = tuple(np.flatnonzero(raw[:, 0] == 0.0).tolist())
        assert zero_direct == tuple(city["tail_instability"]["zero_direct_standpoints"])
        assert zero_direct == EXPECTED_ZERO_DIRECT[city_name]
        observed_zero[city_name] = zero_direct
        if zero_direct:
            indices = np.asarray(zero_direct, dtype=int)
            assert np.all(raw[indices, 1] == 0.0)
            np.testing.assert_array_equal(raw[indices, 2], raw[indices, 3])
            assert np.all(body[indices, 0] == 0.0)
            assert np.all(body[indices, 1] == 0.0)
            np.testing.assert_array_equal(body[indices, 2], body[indices, 3])

        pointwise_shares = body[:, :3] / body[:, 3, None]
        dominant = np.argmax(pointwise_shares, axis=1)
        for index, component in enumerate(ADDITIVE_COMPONENTS):
            dominance_counts[component] += int(np.count_nonzero(dominant == index))

        route_mean_shares = body[:, :3].sum(axis=0) / body[:, 3].sum()
        np.testing.assert_allclose(route_mean_shares.sum(), 1.0, rtol=5e-13, atol=5e-15)
        sorted_values, sorted_probability = _ecdf(normalized_wbsar)
        shadow_coordinates = []
        for point_index in zero_direct:
            value = normalized_wbsar[point_index]
            rank = int(np.flatnonzero(sorted_values == value)[0])
            shadow_coordinates.append(
                {
                    "standpoint": point_index,
                    "normalized_wbsar_m2_per_kg": float(value),
                    "cdf_probability": float(sorted_probability[rank]),
                }
            )

        cities[city_name] = {
            "label": CITY_LABELS[city_name],
            "standpoints": len(route),
            "route_span_m": float(route[-1]["route_distance_m"]),
            "normalized_wbsar_m2_per_kg": normalized_wbsar,
            "normalized_wbsar_quantiles_m2_per_kg": _quantiles(normalized_wbsar),
            "route_mean_component_share": route_mean_shares,
            "zero_direct_and_specular": shadow_coordinates,
        }

    assert total_points == EXPECTED_STANDPOINTS
    assert observed_zero == EXPECTED_ZERO_DIRECT
    assert sum(len(points) for points in observed_zero.values()) == 6
    assert dominance_counts == {"direct": 67, "all_specular": 0, "first_diffuse": 6}

    validation = {
        "input_sha256": observed_hash,
        "manifest_sha256": _sha256(INPUT_MANIFEST),
        "total_standpoints": total_points,
        "zero_direct_and_specular_count": 6,
        "zero_direct_and_specular_indices": {city: list(indices) for city, indices in observed_zero.items() if indices},
        "dominant_component_counts": dominance_counts,
        "maximum_absolute_body_component_closure_residual": float(np.max(np.abs(np.asarray(closure_residuals)))),
    }
    return cities, validation


def _configure_style() -> None:
    plt.style.use(["science", "ieee", "no-latex"])
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["STIX Two Text", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "legend.fontsize": 6.7,
            "xtick.labelsize": 7.0,
            "ytick.labelsize": 7.0,
            "axes.linewidth": 0.6,
            "lines.linewidth": 1.05,
            "lines.markersize": 3.2,
            "lines.markeredgewidth": 0.75,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "xtick.minor.width": 0.45,
            "ytick.minor.width": 0.45,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "hatch.linewidth": 0.35,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.bbox": None,
            "savefig.facecolor": "white",
        }
    )


def _draw(cities: dict[str, Any], pdf_path: Path, png_path: Path) -> None:
    _configure_style()
    figure, (cdf_axis, share_axis) = plt.subplots(
        1,
        2,
        figsize=(7.16, 2.95),
        gridspec_kw={"width_ratios": (1.18, 1.0)},
    )

    for city_name in CITY_ORDER:
        city = cities[city_name]
        style = CITY_STYLES[city_name]
        x, y = _ecdf(city["normalized_wbsar_m2_per_kg"])
        cdf_axis.step(
            x,
            y,
            where="post",
            color=style["color"],
            linestyle=style["linestyle"],
            marker=style["marker"],
            markerfacecolor="white",
            markeredgecolor=style["color"],
            label=f"{city['label']} ($n={city['standpoints']}$)",
            zorder=2,
        )
        if city["zero_direct_and_specular"]:
            cdf_axis.plot(
                [point["normalized_wbsar_m2_per_kg"] for point in city["zero_direct_and_specular"]],
                [point["cdf_probability"] for point in city["zero_direct_and_specular"]],
                linestyle="none",
                marker="v",
                markersize=6.0,
                markerfacecolor="white",
                markeredgecolor=style["color"],
                markeredgewidth=1.2,
                zorder=5,
            )

    cdf_axis.set_xscale("log")
    cdf_axis.set_xlim(5.0e-7, 1.1)
    cdf_axis.set_ylim(0.0, 1.0)
    cdf_axis.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    cdf_axis.set_xlabel(
        r"Normalized whole-body SAR, "
        r"$\mathrm{SAR}_{\mathrm{wb}}/(\rho_A P_{\mathrm{EIRP}})$ [m$^2$ kg$^{-1}$]"
    )
    cdf_axis.set_ylabel("Fixed-route CDF")
    cdf_axis.grid(True, which="major", color="0.86", linewidth=0.45, zorder=0)
    cdf_handles, cdf_labels = cdf_axis.get_legend_handles_labels()
    cdf_handles.append(
        Line2D(
            [],
            [],
            linestyle="none",
            marker="v",
            markersize=5.4,
            markerfacecolor="white",
            markeredgecolor="black",
            markeredgewidth=1.0,
        )
    )
    cdf_labels.append("Zero direct and specular")
    cdf_axis.legend(
        cdf_handles,
        cdf_labels,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.025),
        ncol=2,
        frameon=True,
        framealpha=0.94,
        edgecolor="black",
        fancybox=False,
        borderpad=0.28,
        handlelength=1.55,
        columnspacing=0.75,
        labelspacing=0.25,
    )

    positions = np.arange(len(CITY_ORDER), dtype=np.float64)
    bottom = np.zeros(len(CITY_ORDER), dtype=np.float64)
    for component in ADDITIVE_COMPONENTS:
        index = ADDITIVE_COMPONENTS.index(component)
        values = 100.0 * np.asarray([cities[city]["route_mean_component_share"][index] for city in CITY_ORDER])
        style = COMPONENT_STYLES[component]
        share_axis.bar(
            positions,
            values,
            width=0.72,
            bottom=bottom,
            color=style["color"],
            edgecolor="white" if component == "direct" else "#202020",
            linewidth=0.22,
            hatch=style["hatch"],
            label=style["label"],
            zorder=2,
        )
        bottom += values

    for index, city_name in enumerate(CITY_ORDER):
        shadow_count = len(cities[city_name]["zero_direct_and_specular"])
        if shadow_count:
            share_axis.text(
                index,
                4.0,
                f"{shadow_count}/{cities[city_name]['standpoints']}\nshadow",
                ha="center",
                va="bottom",
                fontsize=6.1,
                color="white",
                zorder=5,
            )

    share_axis.set_xlim(-0.55, len(CITY_ORDER) - 0.45)
    share_axis.set_ylim(0.0, 100.0)
    share_axis.set_yticks([0, 25, 50, 75, 100])
    share_axis.set_ylabel("Route-mean wbSAR share [%]")
    share_axis.set_xticks(positions, [CITY_TICK_LABELS[city] for city in CITY_ORDER])
    share_axis.tick_params(axis="x", length=0, pad=3.0)
    share_axis.grid(axis="y", color="0.86", linewidth=0.45, zorder=0)
    share_axis.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.025),
        ncol=3,
        frameon=False,
        columnspacing=0.8,
        handlelength=1.45,
        handletextpad=0.35,
    )
    for label, axis in zip(("(a)", "(b)"), (cdf_axis, share_axis), strict=True):
        axis.text(0.018, 0.975, label, transform=axis.transAxes, ha="left", va="top")
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    figure.subplots_adjust(left=0.072, right=0.995, bottom=0.21, top=0.735, wspace=0.29)
    metadata = {
        "Title": "Fixed-route whole-body exposure and component shares",
        "Author": "AEGIS city exposure study",
        "Subject": "Authenticated five-city first-material-interaction results",
        "Keywords": "whole-body SAR, fixed routes, direct, specular, diffuse",
        "Creator": "make_route_results.py",
        "Producer": "Matplotlib",
        "CreationDate": None,
        "ModDate": None,
    }
    figure.savefig(pdf_path, metadata=metadata)
    figure.savefig(
        png_path,
        dpi=400,
        metadata={"Software": "make_route_results.py", "Title": metadata["Title"]},
    )
    plt.close(figure)


def _render_deterministically(cities: dict[str, Any]) -> dict[str, Any]:
    _draw(cities, OUTPUT_PDF, OUTPUT_PNG)
    first = {"pdf": _sha256(OUTPUT_PDF), "png": _sha256(OUTPUT_PNG)}
    with tempfile.TemporaryDirectory(prefix="route-results-") as temporary_directory:
        temporary = Path(temporary_directory)
        second_pdf = temporary / OUTPUT_PDF.name
        second_png = temporary / OUTPUT_PNG.name
        _draw(cities, second_pdf, second_png)
        second = {"pdf": _sha256(second_pdf), "png": _sha256(second_png)}
    assert first == second, f"nondeterministic rendering: {first} != {second}"
    return first


def _write_audit(cities: dict[str, Any], validation: dict[str, Any], hashes: dict[str, str]) -> None:
    pdf_width_in = 7.16
    png = plt.imread(OUTPUT_PNG)
    audit_cities = {}
    for city_name in CITY_ORDER:
        city = cities[city_name]
        audit_cities[city_name] = {
            "label": city["label"],
            "standpoints": city["standpoints"],
            "route_span_m": city["route_span_m"],
            "normalized_wbsar_quantiles_m2_per_kg": city["normalized_wbsar_quantiles_m2_per_kg"],
            "route_mean_component_share_percent": {
                component: float(100.0 * city["route_mean_component_share"][index])
                for index, component in enumerate(ADDITIVE_COMPONENTS)
            },
            "zero_direct_and_specular": city["zero_direct_and_specular"],
        }

    audit = {
        "schema_version": "route_results_figure_audit_v1",
        "source": {
            "aggregate": str(INPUT_JSON.relative_to(SEMANTIC_TWIN)),
            "manifest": str(INPUT_MANIFEST.relative_to(SEMANTIC_TWIN)),
            "aggregate_sha256": validation["input_sha256"],
            "manifest_sha256": validation["manifest_sha256"],
            "authenticated_against_manifest": True,
            "result_schema": RESULT_SCHEMA,
        },
        "campaign_contract": {
            "normalization": "per unit rho_A P_EIRP",
            "route_contract": "provider_corridor_v1",
            "transport_topology": TRANSPORT_TOPOLOGY,
            "components": list(SEALED_COMPONENTS),
            "replicas_per_city": 16,
            "seeds": list(EXPECTED_SEEDS),
            "scope": "fixed registered routes, not city or population samples",
        },
        "validation": validation,
        "figure_semantics": {
            "panel_a": ("midpoint empirical CDF of normalized whole-body SAR at every registered route standpoint"),
            "panel_a_shadow_marker": (
                "hollow downward triangle at each of six included points where direct and exact order-1 "
                "specular components are both zero"
            ),
            "panel_b": ("additive component sum divided by total whole-body SAR sum over each fixed route"),
            "city_comparison_limit": (
                "routes are fixed case studies; the figure does not estimate city or population distributions"
            ),
        },
        "cities": audit_cities,
        "render": {
            "scienceplots_version": version("SciencePlots"),
            "matplotlib_version": mpl.__version__,
            "style": ["science", "ieee", "no-latex"],
            "deterministic_second_render_match": True,
            "pdf": {
                "path": OUTPUT_PDF.name,
                "sha256": hashes["pdf"],
                "bytes": OUTPUT_PDF.stat().st_size,
                "width_in": pdf_width_in,
                "height_in": 2.95,
            },
            "png": {
                "path": OUTPUT_PNG.name,
                "sha256": hashes["png"],
                "bytes": OUTPUT_PNG.stat().st_size,
                "width_px": int(png.shape[1]),
                "height_px": int(png.shape[0]),
                "dpi": 400,
            },
        },
    }
    OUTPUT_AUDIT.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    cities, validation = _load_and_validate()
    hashes = _render_deterministically(cities)
    _write_audit(cities, validation, hashes)
    print(
        f"Wrote {OUTPUT_PDF.name}, {OUTPUT_PNG.name}, and {OUTPUT_AUDIT.name} "
        f"from {validation['total_standpoints']} authenticated route points."
    )
    print(
        "Retained and marked "
        f"{validation['zero_direct_and_specular_count']} points with zero direct and specular transfer."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
