"""Render the five-city 12-to-16-replica convergence audit figure.

The sole numerical input is the authenticated current five-city aggregate for
the ``first_material_interaction_v1`` transport contract. The script refuses a
different byte hash, city set, seed set, look schedule, or route contract.

Run from any directory with:

    uv run --with SciencePlots --project /home/user/tools/devpc-python python \
        semantic_twin/paper/figures/convergence/make_convergence.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import struct
import subprocess
from typing import Any

import numpy as np
import scienceplots  # noqa: F401  # registers the SciencePlots style sheets

SEMANTIC_TWIN_ROOT = pathlib.Path(__file__).resolve().parents[3]
FIGURE_DIR = pathlib.Path(__file__).resolve().parent
INPUT = (
    SEMANTIC_TWIN_ROOT
    / "outputs"
    / "roofline_campaign"
    / "current_five_city_first_material_interaction"
    / "current_five_city_first_material_interaction.json"
)
EXPECTED_INPUT_SHA256 = "d530a056bfa7be9cf1966a7169cea58b0fcae48dc9cab89ab62ae4577aa765bd"
EXPECTED_SCHEMA = "roofline_multicity_results_v1"
EXPECTED_CITIES = ("Korenmarkt", "Prague", "Madrid", "Mexico", "Tokyo")
CITY_DISPLAY = {"Korenmarkt": "Ghent", "Prague": "Prague", "Madrid": "Madrid",
                "Mexico": "Mexico City", "Tokyo": "Tokyo Hachiko"}
EXPECTED_SEEDS = tuple(range(7, 23))
EXPECTED_LOOKS = (4, 8, 12, 16)
EXPECTED_TRANSITIONS = ((4, 8), (8, 12), (12, 16))
EXPECTED_TOPOLOGY = "first_material_interaction_v1"
EXPECTED_ROUTE_CONTRACT = "provider_corridor_v1"

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import LogLocator, NullFormatter  # noqa: E402


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, found {actual!r}")


def load_and_validate() -> tuple[dict[str, Any], str]:
    """Load the sealed aggregate and assert the figure's full data contract."""
    source_hash = _sha256(INPUT)
    _require(source_hash, EXPECTED_INPUT_SHA256, "aggregate SHA-256")
    payload = json.loads(INPUT.read_text())
    _require(payload.get("schema_version"), EXPECTED_SCHEMA, "aggregate schema")
    _require(set(payload.get("cities", {})), set(EXPECTED_CITIES), "city set")
    _require(len(payload["cities"]), 5, "city count")

    metadata = payload.get("metadata", {})
    topologies = metadata.get("transport_topologies", {})
    _require(set(topologies), set(EXPECTED_CITIES), "metadata city set")

    for name in EXPECTED_CITIES:
        city = payload["cities"][name]
        _require(city.get("city"), name, f"{name} city label")
        _require(city.get("transport_topology"), EXPECTED_TOPOLOGY, f"{name} topology")
        _require(city.get("replicas"), 16, f"{name} replica count")
        _require(tuple(city.get("seeds", ())), EXPECTED_SEEDS, f"{name} seeds")
        _require(city.get("standpoints"), len(city.get("route", ())), f"{name} standpoint count")
        _require(city["contract"].get("route_contract"), EXPECTED_ROUTE_CONTRACT, f"{name} route")
        _require(city["provenance"].get("launch_sampling"), "iid", f"{name} launch sampling")
        _require(topologies[name].get("transport_topology"), EXPECTED_TOPOLOGY, f"{name} metadata topology")

        se_looks = tuple(entry["replicas"] for entry in city["convergence"]["standard_error"])
        _require(se_looks, EXPECTED_LOOKS, f"{name} standard-error looks")
        convergence_transitions = tuple(
            (entry["from_replicas"], entry["to_replicas"]) for entry in city["convergence"]["look_to_look"]
        )
        tail_transitions = tuple(
            (entry["from_replicas"], entry["to_replicas"]) for entry in city["tail_instability"]["look_to_look"]
        )
        _require(convergence_transitions, EXPECTED_TRANSITIONS, f"{name} convergence transitions")
        _require(tail_transitions, EXPECTED_TRANSITIONS, f"{name} tail transitions")

    return payload, source_hash


def extract_metrics(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for name in EXPECTED_CITIES:
        city = payload["cities"][name]
        tail = next(
            entry
            for entry in city["tail_instability"]["look_to_look"]
            if (entry["from_replicas"], entry["to_replicas"]) == (12, 16)
        )
        se16 = next(entry for entry in city["convergence"]["standard_error"] if entry["replicas"] == 16)[
            "total_transfer"
        ]
        q50 = float(tail["route_quantile_abs_change_db"]["q50"])
        lower_tail = float(tail["final_lower_decile_points"]["maximum_abs_db"])
        if not (np.isfinite(q50) and q50 > 0.0 and np.isfinite(lower_tail) and lower_tail > 0.0):
            raise ValueError(f"{name}: log-scale convergence metrics must be finite and positive")
        metrics[name] = {
            "standpoints": int(city["standpoints"]),
            "route_q50_abs_change_db_by_transition": {
                f"{entry['from_replicas']}_to_{entry['to_replicas']}": float(
                    entry["route_quantile_abs_change_db"]["q50"]
                )
                for entry in city["tail_instability"]["look_to_look"]
            },
            "route_q50_abs_change_db_12_to_16": q50,
            "final_lower_decile_worst_abs_change_db_12_to_16": lower_tail,
            "lower_tail_to_route_q50_ratio": lower_tail / q50,
            "p90_standard_error_db_at_16": float(se16["p90_db_delta_approximation"]),
            "tail_status": city["tail_instability"]["status"],
            "final_lower_decile_standpoints": tail["final_lower_decile_points"]["standpoints"],
            "zero_direct_standpoints": city["tail_instability"]["zero_direct_standpoints"],
        }
    return metrics


def draw(metrics: dict[str, dict[str, Any]]) -> None:
    """Draw central and lower-tail convergence, then rasterize for review."""
    plt.style.use("science")
    matplotlib.rcParams.update(
        {
            "text.usetex": True,
            "text.latex.preamble": (
                r"\usepackage[T1]{fontenc}"
                r"\usepackage{lmodern}"
                r"\usepackage{microtype}"
                r"\usepackage{amsmath,amssymb}"
            ),
            "font.family": "serif",
            "font.serif": ["Latin Modern Roman"],
            "font.size": 8.2,
            "axes.labelsize": 8.2,
            "axes.titlesize": 8.2,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.2,
            "lines.linewidth": 1.05,
            "lines.markersize": 5.2,
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "axes.grid.axis": "both",
            "grid.alpha": 0.25,
            "grid.linewidth": 0.5,
            "legend.frameon": True,
            "legend.fancybox": False,
            "savefig.bbox": None,
        },
    )
    figure, (axis_central, axis_tail) = plt.subplots(
        1,
        2,
        figsize=(7.16, 2.62),
        gridspec_kw={"width_ratios": [1.02, 1.0], "wspace": 0.28},
    )

    transition_keys = ("4_to_8", "8_to_12", "12_to_16")
    transition_labels = (r"$4\!\rightarrow\!8$", r"$8\!\rightarrow\!12$", r"$12\!\rightarrow\!16$")
    transition_x = np.arange(len(transition_keys), dtype=float)
    city_styles = {
        "Korenmarkt": ("#000000", "o"),
        "Prague": ("#0000FF", "s"),
        "Madrid": ("#008000", "D"),
        "Mexico": ("#FF0000", "^"),
        "Tokyo": ("#FF8C00", "v"),
    }
    for name in EXPECTED_CITIES:
        color, marker = city_styles[name]
        values = np.array([metrics[name]["route_q50_abs_change_db_by_transition"][key] for key in transition_keys])
        axis_central.plot(
            transition_x,
            values,
            color=color,
            marker=marker,
            markerfacecolor="white",
            markeredgecolor=color,
            markeredgewidth=0.9,
            label=CITY_DISPLAY.get(name, name),
            zorder=3,
        )

    axis_central.set_yscale("log")
    axis_central.set_ylim(5.0e-6, 8.0e-4)
    axis_central.set_xlim(-0.18, 2.18)
    axis_central.set_xticks(transition_x, transition_labels)
    axis_central.set_xlabel("Nested replica means")
    axis_central.set_ylabel(r"Absolute route-median change [dB]")
    axis_central.yaxis.set_major_locator(LogLocator(base=10.0, numticks=4))
    axis_central.yaxis.set_minor_locator(LogLocator(base=10.0, subs=(2.0, 5.0), numticks=12))
    axis_central.yaxis.set_minor_formatter(NullFormatter())
    axis_central.grid(which="major", color="0.82", lw=0.5)
    axis_central.grid(which="minor", color="0.90", lw=0.35)
    axis_central.text(
        0.015,
        0.975,
        r"\textbf{(a)} Central route statistic",
        transform=axis_central.transAxes,
        ha="left",
        va="top",
    )
    legend = axis_central.legend(
        loc="lower left",
        bbox_to_anchor=(0.0, 1.025),
        borderaxespad=0.0,
        ncol=5,
        frameon=False,
        columnspacing=0.75,
        handlelength=1.25,
        handletextpad=0.35,
    )
    for handle in legend.legend_handles:
        handle.set_markersize(4.8)

    x = np.arange(len(EXPECTED_CITIES), dtype=float)
    q50 = np.array([metrics[name]["route_q50_abs_change_db_12_to_16"] for name in EXPECTED_CITIES])
    lower_tail = np.array(
        [metrics[name]["final_lower_decile_worst_abs_change_db_12_to_16"] for name in EXPECTED_CITIES]
    )

    for xpos, central, tail in zip(x, q50, lower_tail):
        axis_tail.plot([xpos, xpos], [central, tail], color="0.72", lw=0.8, zorder=1)
    axis_tail.plot(
        x,
        q50,
        linestyle="none",
        marker="o",
        color="#000000",
        markerfacecolor="none",
        markeredgewidth=0.9,
        zorder=3,
    )
    axis_tail.plot(
        x,
        lower_tail,
        linestyle="none",
        marker="^",
        color="#FF0000",
        markerfacecolor="none",
        markeredgewidth=0.9,
        zorder=3,
    )

    axis_tail.set_yscale("log")
    axis_tail.set_ylim(5.0e-6, 7.0e-2)
    axis_tail.set_xlim(-0.45, 4.45)
    axis_tail.yaxis.set_major_locator(LogLocator(base=10.0, numticks=6))
    axis_tail.yaxis.set_minor_locator(LogLocator(base=10.0, subs=(2.0, 5.0), numticks=15))
    axis_tail.yaxis.set_minor_formatter(NullFormatter())
    axis_tail.set_xticks(x)
    axis_tail.set_xticklabels(("Ghent", "Prague", "Madrid", "Mexico\nCity", "Tokyo\nHachiko"))
    axis_tail.set_ylabel(r"Absolute $12\!\rightarrow\!16$ change [dB]")
    axis_tail.set_xlabel("Registered city route")
    axis_tail.grid(axis="y", which="major", color="0.82", lw=0.5)
    axis_tail.grid(axis="y", which="minor", color="0.90", lw=0.35)
    axis_tail.grid(axis="x", visible=False)
    axis_tail.text(
        0.015,
        0.975,
        r"\textbf{(b)} Lower-tail check",
        transform=axis_tail.transAxes,
        ha="left",
        va="top",
    )

    legend_handles = [
        Line2D(
            [],
            [],
            linestyle="none",
            marker="o",
            color="#000000",
            markerfacecolor="none",
            markeredgewidth=0.9,
            label=r"route median ($q_{50}$)",
        ),
        Line2D(
            [],
            [],
            linestyle="none",
            marker="^",
            color="#FF0000",
            markerfacecolor="none",
            markeredgewidth=0.9,
            label="worst point in final lower decile",
        ),
    ]
    legend = axis_tail.legend(
        handles=legend_handles,
        loc="lower right",
        bbox_to_anchor=(1.0, 1.025),
        borderaxespad=0.0,
        ncol=2,
        frameon=False,
        handlelength=1.2,
        handletextpad=0.5,
    )
    max_q50_name = max(EXPECTED_CITIES, key=lambda name: metrics[name]["route_q50_abs_change_db_12_to_16"])
    max_q50_index = EXPECTED_CITIES.index(max_q50_name)
    max_q50 = metrics[max_q50_name]["route_q50_abs_change_db_12_to_16"]
    axis_tail.annotate(
        rf"all medians $\leq {max_q50 * 1.0e5:.2f}\times 10^{{-5}}$ dB",
        xy=(max_q50_index, max_q50),
        xytext=(0.0, 6.0e-4),
        textcoords="data",
        ha="left",
        va="center",
        fontsize=7.0,
        arrowprops={"arrowstyle": "-", "color": "0.35", "lw": 0.7},
    )
    axis_tail.annotate(
        "0.0322 dB",
        xy=(3.0, metrics["Mexico"]["final_lower_decile_worst_abs_change_db_12_to_16"]),
        xytext=(2.65, 8.0e-3),
        textcoords="data",
        ha="right",
        va="top",
        fontsize=7.0,
        color="#B00000",
        arrowprops={"arrowstyle": "-", "color": "#B00000", "lw": 0.7},
    )
    axis_tail.annotate(
        "0.0176 dB",
        xy=(4.0, metrics["Tokyo"]["final_lower_decile_worst_abs_change_db_12_to_16"]),
        xytext=(4.35, 6.0e-3),
        textcoords="data",
        ha="right",
        va="top",
        fontsize=7.0,
        color="#B00000",
        arrowprops={"arrowstyle": "-", "color": "#B00000", "lw": 0.7},
    )

    figure.subplots_adjust(left=0.083, right=0.992, bottom=0.205, top=0.85)
    pdf = FIGURE_DIR / "convergence.pdf"
    png = FIGURE_DIR / "convergence.png"
    figure.savefig(
        pdf,
        metadata={"Creator": "make_convergence.py", "CreationDate": None, "ModDate": None},
    )
    plt.close(figure)
    subprocess.run(
        ["pdftocairo", "-png", "-singlefile", "-r", "300", str(pdf), str(png.with_suffix(""))],
        check=True,
    )


def validate_outputs(pdf: pathlib.Path, png: pathlib.Path) -> dict[str, Any]:
    """Refuse wrong dimensions, unembedded fonts, or Type 3 fonts."""
    png_header = png.read_bytes()[:24]
    _require(png_header[:8], b"\x89PNG\r\n\x1a\n", "PNG signature")
    png_pixels = struct.unpack(">II", png_header[16:24])
    _require(png_pixels, (2148, 786), "300 dpi PNG dimensions")

    pdf_info = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True).stdout
    page_match = re.search(r"Page size:\s+([0-9.]+) x ([0-9.]+) pts", pdf_info)
    if page_match is None:
        raise ValueError("PDF page size was not reported")
    page_points = (float(page_match.group(1)), float(page_match.group(2)))
    if not (abs(page_points[0] - 515.52) < 0.01 and abs(page_points[1] - 188.64) < 0.01):
        raise ValueError(f"PDF page size: expected (515.52, 188.64), found {page_points}")

    font_info = subprocess.run(["pdffonts", str(pdf)], check=True, capture_output=True, text=True).stdout
    if "Type 3" in font_info:
        raise ValueError("PDF contains a Type 3 font")
    font_rows = [line for line in font_info.splitlines()[2:] if line.strip()]
    embedded = [re.search(r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", row) for row in font_rows]
    if not font_rows or any(match is None or match.group(1) != "yes" for match in embedded):
        raise ValueError("PDF contains an unembedded or unrecognized font row")
    font_types = sorted(
        {"Type 1" if " Type 1 " in row else "CID TrueType" if " CID TrueType " in row else "other" for row in font_rows}
    )
    return {
        "png_pixels": list(png_pixels),
        "pdf_page_points": list(page_points),
        "pdf_page_inches": [7.16, 2.62],
        "font_types": font_types,
        "all_fonts_embedded": True,
        "type_3_fonts": 0,
    }


def write_audit(payload: dict[str, Any], source_hash: str, metrics: dict[str, dict[str, Any]]) -> None:
    pdf = FIGURE_DIR / "convergence.pdf"
    png = FIGURE_DIR / "convergence.png"
    output_qa = validate_outputs(pdf, png)
    audit = {
        "schema_version": "five_city_convergence_figure_audit_v2",
        "source": {
            "path": str(INPUT.relative_to(SEMANTIC_TWIN_ROOT)),
            "sha256": source_hash,
            "aggregate_schema_version": payload["schema_version"],
            "numeric_source_count": 1,
        },
        "contract": {
            "city_count": 5,
            "cities": list(EXPECTED_CITIES),
            "transport_topology": EXPECTED_TOPOLOGY,
            "route_contract": EXPECTED_ROUTE_CONTRACT,
            "launch_sampling": "iid",
            "seeds": list(EXPECTED_SEEDS),
            "replicas": 16,
            "looks": list(EXPECTED_LOOKS),
            "transition_shown": [12, 16],
            "figure_transitions": [[4, 8], [8, 12], [12, 16]],
            "figure_width_in": 7.16,
            "figure_height_in": 2.62,
            "png_dpi": 300,
            "style": "SciencePlots science with TeX-rendered embedded Latin Modern fonts",
        },
        "metric_definitions": {
            "route_q50_abs_change_db_12_to_16": (
                "absolute change in the fixed-route q50 whole-body SAR between the nested 12- and "
                "16-replica means, expressed in dB"
            ),
            "final_lower_decile_worst_abs_change_db_12_to_16": (
                "largest absolute dB change among standpoints in the lower decile ranked by the "
                "final 16-replica-mean whole-body SAR"
            ),
            "scope": (
                "finite-replica uncertainty conditional on each fixed registered route; excludes "
                "route-selection and city-sampling uncertainty"
            ),
        },
        "cities": metrics,
        "claims": {
            "maximum_route_q50_abs_change_db_12_to_16": max(
                entry["route_q50_abs_change_db_12_to_16"] for entry in metrics.values()
            ),
            "mexico_lower_tail_abs_change_db_12_to_16": metrics["Mexico"][
                "final_lower_decile_worst_abs_change_db_12_to_16"
            ],
            "tokyo_lower_tail_abs_change_db_12_to_16": metrics["Tokyo"][
                "final_lower_decile_worst_abs_change_db_12_to_16"
            ],
        },
        "suggested_caption": (
            "Convergence over nested replica means. (a) The absolute change in fixed-route median "
            "whole-body SAR is at most 5.91e-5 dB in the 12-to-16-replica check. (b) Circles show "
            "that final central change. Triangles show the largest "
            "change among standpoints in the final lower decile. The Mexico City and Tokyo Hachiko "
            "lower tails remain less stable, and each route contains three zero-direct standpoints. "
            "Values are conditional on each fixed registered route."
        ),
        "outputs": {
            "pdf": {"path": pdf.name, "bytes": pdf.stat().st_size},
            "png": {"path": png.name, "bytes": png.stat().st_size, "sha256": _sha256(png)},
        },
        "output_qa": output_qa,
    }
    (FIGURE_DIR / "convergence.audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")


def main() -> int:
    payload, source_hash = load_and_validate()
    metrics = extract_metrics(payload)
    draw(metrics)
    write_audit(payload, source_hash, metrics)
    print(f"wrote {FIGURE_DIR / 'convergence.pdf'}")
    print(f"wrote {FIGURE_DIR / 'convergence.png'}")
    print(f"wrote {FIGURE_DIR / 'convergence.audit.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
