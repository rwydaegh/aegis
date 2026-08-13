"""Render the five-city 12-to-16-replica convergence audit figure.

The sole numerical input is the authenticated current five-city aggregate for
the ``first_material_interaction_v1`` transport contract. The script refuses a
different byte hash, city set, seed set, look schedule, or route contract.

Run from any directory with:

    uv run --project /home/user/tools/devpc-python python \
        semantic_twin/paper/figures/convergence/make_convergence.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
from typing import Any

import numpy as np

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
EXPECTED_SEEDS = tuple(range(7, 23))
EXPECTED_LOOKS = (4, 8, 12, 16)
EXPECTED_TRANSITIONS = ((4, 8), (8, 12), (12, 16))
EXPECTED_TOPOLOGY = "first_material_interaction_v1"
EXPECTED_ROUTE_CONTRACT = "provider_corridor_v1"

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator  # noqa: E402


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
            "route_q50_abs_change_db_12_to_16": q50,
            "final_lower_decile_worst_abs_change_db_12_to_16": lower_tail,
            "lower_tail_to_route_q50_ratio": lower_tail / q50,
            "p90_standard_error_db_at_16": float(se16["p90_db_delta_approximation"]),
            "tail_status": city["tail_instability"]["status"],
            "final_lower_decile_standpoints": tail["final_lower_decile_points"]["standpoints"],
            "zero_direct_standpoints": city["tail_instability"]["zero_direct_standpoints"],
        }
    return metrics


def _decimal_log_tick(value: float, _position: int) -> str:
    labels = {
        1.0e-5: "0.00001",
        1.0e-4: "0.0001",
        1.0e-3: "0.001",
        1.0e-2: "0.01",
    }
    return labels.get(value, "")


def draw(metrics: dict[str, dict[str, Any]]) -> None:
    """Draw one paired-marker panel, then rasterize the vector PDF for review."""
    plt.style.use("default")
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
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "axes.titlesize": 8.0,
            "xtick.labelsize": 7.3,
            "ytick.labelsize": 7.3,
            "legend.fontsize": 7.0,
            "lines.linewidth": 1.0,
            "lines.markersize": 5.0,
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.alpha": 0.25,
            "grid.linewidth": 0.5,
            "legend.frameon": True,
            "legend.fancybox": False,
        },
    )
    figure, axis = plt.subplots(figsize=(3.5, 2.94))
    x = np.arange(len(EXPECTED_CITIES), dtype=float)
    q50 = np.array([metrics[name]["route_q50_abs_change_db_12_to_16"] for name in EXPECTED_CITIES])
    lower_tail = np.array(
        [metrics[name]["final_lower_decile_worst_abs_change_db_12_to_16"] for name in EXPECTED_CITIES]
    )

    for xpos, central, tail in zip(x, q50, lower_tail):
        axis.plot([xpos, xpos], [central, tail], color="0.72", lw=0.8, zorder=1)
    axis.plot(
        x,
        q50,
        linestyle="none",
        marker="o",
        color="#000000",
        markerfacecolor="none",
        markeredgewidth=0.9,
        zorder=3,
    )
    axis.plot(
        x,
        lower_tail,
        linestyle="none",
        marker="^",
        color="#FF0000",
        markerfacecolor="none",
        markeredgewidth=0.9,
        zorder=3,
    )

    axis.set_yscale("log")
    axis.set_ylim(5.0e-6, 5.3e-2)
    axis.set_xlim(-0.45, 4.45)
    axis.yaxis.set_major_locator(FixedLocator([1.0e-5, 1.0e-4, 1.0e-3, 1.0e-2]))
    axis.yaxis.set_major_formatter(FuncFormatter(_decimal_log_tick))
    axis.yaxis.set_minor_locator(NullLocator())
    axis.set_xticks(x)
    axis.set_xticklabels(("Korenmarkt", "Prague", "Madrid", "Mexico\nCity", "Tokyo\nHachiko"))
    axis.set_ylabel("Absolute change from 12 to 16 replicas [dB]")
    axis.set_xlabel("Registered city route")
    axis.grid(axis="y", which="major", color="0.82", lw=0.5)
    axis.grid(axis="x", visible=False)

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
    legend = axis.legend(
        handles=legend_handles,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.02),
        borderaxespad=0.0,
        ncol=1,
        framealpha=0.92,
        borderpad=0.25,
        handlelength=1.2,
        handletextpad=0.5,
    )
    legend.get_frame().set_edgecolor("black")
    legend.get_frame().set_linewidth(1.0)
    legend.get_frame().set_boxstyle("Square", pad=0.25)

    max_q50_name = max(EXPECTED_CITIES, key=lambda name: metrics[name]["route_q50_abs_change_db_12_to_16"])
    max_q50_index = EXPECTED_CITIES.index(max_q50_name)
    max_q50 = metrics[max_q50_name]["route_q50_abs_change_db_12_to_16"]
    axis.annotate(
        rf"all route medians $\leq {max_q50 * 1.0e5:.4f}\times 10^{{-5}}$ dB",
        xy=(max_q50_index, max_q50),
        xytext=(0.12, 8.0e-4),
        textcoords="data",
        ha="left",
        va="center",
        fontsize=7.0,
        arrowprops={"arrowstyle": "-", "color": "0.35", "lw": 0.7},
    )
    axis.annotate(
        "0.032226 dB",
        xy=(3.0, metrics["Mexico"]["final_lower_decile_worst_abs_change_db_12_to_16"]),
        xytext=(2.78, 7.0e-3),
        textcoords="data",
        ha="right",
        va="top",
        fontsize=7.0,
        color="#B00000",
        arrowprops={"arrowstyle": "-", "color": "#B00000", "lw": 0.7},
    )
    axis.annotate(
        "0.017636 dB",
        xy=(4.0, metrics["Tokyo"]["final_lower_decile_worst_abs_change_db_12_to_16"]),
        xytext=(4.25, 2.0e-3),
        textcoords="data",
        ha="right",
        va="top",
        fontsize=7.0,
        color="#B00000",
        arrowprops={"arrowstyle": "-", "color": "#B00000", "lw": 0.7},
    )

    figure.subplots_adjust(left=0.20, right=0.98, bottom=0.22, top=0.77)
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


def write_audit(payload: dict[str, Any], source_hash: str, metrics: dict[str, dict[str, Any]]) -> None:
    pdf = FIGURE_DIR / "convergence.pdf"
    png = FIGURE_DIR / "convergence.png"
    audit = {
        "schema_version": "five_city_convergence_figure_audit_v1",
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
            "Route-median exposure is stable by the 12-to-16-replica step, while shadow tails "
            "remain less stable in Mexico City and Tokyo Hachiko. Circles show the absolute change "
            "in fixed-route median whole-body SAR; triangles show the largest change among "
            "standpoints in the final lower decile. Values are in dB and conditional on each "
            "registered route. Each affected route contains three zero-direct standpoints."
        ),
        "outputs": {
            "pdf": {"path": pdf.name, "bytes": pdf.stat().st_size, "sha256": _sha256(pdf)},
            "png": {"path": png.name, "bytes": png.stat().st_size, "sha256": _sha256(png)},
        },
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
