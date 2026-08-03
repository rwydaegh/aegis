"""How far the photographic evidence reaches.

The paper's method argument is one thread: transmitter and receiver sit at the
same point, so a street level photograph taken from that point sees the surfaces
the early bounces hit. Material is measured rather than assumed, and how far the
measurement reaches is what sets the bounce budget. That thread was carried
entirely by prose and tables. This is the figure for it.

Two panels, because there are two different questions and they must not be
differenced against each other.

Panel a asks what a viewpoint can ever see. Observed means geometrically visible
from the standpoint, on a mask built by first hit probing of 2e6 directions from
the standpoint itself. A path that returns to where it started has both ends on
that set by construction, an outward path has only its first interaction there,
and the panel is the size of that difference on real photogrammetric geometry.

Panel b asks what a camera actually photographed. Observed means a registered
panorama landed transient free rays on the triangle and the class it collected
carries a material. That is a property of how densely the square was walked, so
it decays with distance from a camera, and the panel is that decay.

    python FIGURES/make_evidence_reach_figure.py

Reads only shipped outputs. Writes PDF for the paper and PNG for looking at.
"""

from __future__ import annotations

import json
import pathlib
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

sys.path.insert(0, "/home/user/aegis/theory/scripts")

from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parent

#: Panel a. Closed loop against outward path, on visibility masks probed from
#: each standpoint. 42 standpoints over four meshes on three continents.
VISIBILITY = sorted((ROOT / "outputs" / "monostatic").glob("monovis_*_visibility_locations.jsonl"))

#: Panel b. Coverage by real panorama evidence against distance to the nearest
#: registered station. Korenmarkt, 130 m crop, 40 walk standpoints and 8
#: stations, 200k rays each. The report's nearest distance bin holds exactly the
#: eight station positions and no walk standpoint, which is why the first
#: category below is drawn as the cameras themselves.
EVIDENCE = ROOT / "outputs" / "bounce_budget" / "korenmarkt_130m_bounce_evidence.json"

INK = "#1a1a1a"
SKY = "#2f6fb5"
WARM = "#d1622b"
MUTED = "#8a8f98"

#: Panel b draws the first three interactions, dark to light.
DEPTH_INK = ("#123f6d", "#3f7fbe", "#93bade")


def save(fig, stem: str) -> None:
    for suffix in ("pdf", "png"):
        fig.savefig(OUT / f"{stem}.{suffix}", dpi=300)
    plt.close(fig)
    print(f"wrote {stem}.pdf and {stem}.png")


def load_visibility() -> tuple[np.ndarray, np.ndarray]:
    """Per standpoint chain shares at orders 1, 2, 3 for both formulations."""
    closed, opened = [], []
    for path in VISIBILITY:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            cov = json.loads(line)["coverage"]
            closed.append([cov["closed_loop_chain_observed"][k] for k in (1, 2, 3)])
            opened.append([cov["open_path_chain_observed"][k] for k in (1, 2, 3)])
    return np.array(closed), np.array(opened)


def load_evidence() -> dict:
    payload = json.loads(EVIDENCE.read_text())
    tally = payload["bounce_evidence"]
    bins = tally["against_distance_from_nearest_station"]["walk"]
    stations = np.array([row["walk"] for row in tally["per_standpoint"] if row["kind"] == "station"])
    walk_bins = bins[1:]
    return {
        "labels": ["at a camera"]
        + [
            f"{int(row['metres_from_nearest_station'][0])} to {int(row['metres_from_nearest_station'][1])} m"
            for row in walk_bins
        ],
        "counts": [len(stations)] + [row["standpoints"] for row in walk_bins],
        "curves": {
            depth: [row["median_covered_fraction_by_power"][f"bounce_{depth}"] for row in bins] for depth in (1, 2, 3)
        },
        "station_first": stations[:, 0],
        "walk_standpoints": sum(row["standpoints"] for row in walk_bins),
        "pooled_walk_first": tally["pooled_walk_standpoints_only"]["walk"]["covered_fraction_by_power"][0],
    }


def panel_a(ax, closed: np.ndarray, opened: np.ndarray) -> None:
    order = np.array([1.0, 2.0, 3.0])
    med_closed = np.median(closed, axis=0)
    med_open = np.median(opened, axis=0)

    ax.fill_between(order, med_open, med_closed, color=MUTED, alpha=0.16, lw=0, zorder=1)

    for track, med, colour, marker, dx in (
        (closed, med_closed, SKY, "o", -0.045),
        (opened, med_open, WARM, "s", 0.045),
    ):
        lo = np.percentile(track, 25, axis=0)
        hi = np.percentile(track, 75, axis=0)
        ax.vlines(order + dx, lo, hi, color=colour, lw=1.0, alpha=0.55, zorder=3)
        ax.plot(order, med, color=colour, lw=1.7, zorder=4)
        ax.plot(order, med, color=colour, ls="none", marker=marker, ms=4.2, zorder=5)

    # Six figures on the closed loop because that is where the exactness lives,
    # three on the outward path because there is nothing beyond them to show.
    for x, y, text in zip(order, med_closed, ("1.000000", "0.999972", "0.980")):
        ax.annotate(
            text,
            xy=(x, y),
            xytext=(7, 4),
            textcoords="offset points",
            ha="left",
            fontsize=6.8,
            color=SKY,
        )
    for x, y in zip(order, med_open):
        ax.annotate(
            f"{y:.3f}",
            xy=(x, y),
            xytext=(-7, -8),
            textcoords="offset points",
            ha="right",
            fontsize=6.8,
            color=WARM,
        )

    ax.text(
        2.02,
        1.058,
        "the path comes back to the standpoint",
        fontsize=7.2,
        color=SKY,
        ha="center",
        va="center",
    )
    ax.text(
        1.06,
        0.800,
        "the path keeps going,\nwhich is what the\nestimator actually does",
        fontsize=7.2,
        color=WARM,
        ha="left",
        va="top",
        linespacing=1.25,
    )
    ax.text(
        2.42,
        0.925,
        "surfaces the\nstandpoint\ncannot see",
        fontsize=6.9,
        color=INK,
        ha="center",
        va="center",
        linespacing=1.3,
    )

    ax.set_xticks(order)
    ax.set_xlim(0.60, 3.36)
    ax.set_ylim(0.645, 1.095)
    ax.set_yticks([0.7, 0.8, 0.9, 1.0])
    ax.set_xlabel("interaction order")
    ax.set_ylabel("share of power whose whole chain lands\non surfaces visible from the standpoint")


def panel_b(ax, ev: dict) -> None:
    slots = np.arange(len(ev["labels"]), dtype=float)

    ax.axhline(ev["pooled_walk_first"], color=INK, lw=0.9, ls=(0, (4, 3)), zorder=2)
    ax.text(
        0.30,
        ev["pooled_walk_first"] + 0.026,
        f"{ev['pooled_walk_first']:.3f}, the first\ninteraction pooled over the\npublished 90 m walk",
        fontsize=6.9,
        color=INK,
        ha="left",
        va="bottom",
        linespacing=1.25,
    )

    labels = {1: "first interaction", 2: "second interaction", 3: "third interaction"}
    for depth, colour in zip((1, 2, 3), DEPTH_INK):
        ax.plot(
            slots,
            ev["curves"][depth],
            color=colour,
            lw=1.6,
            marker="o",
            ms=3.6,
            zorder=4,
            label=labels[depth],
        )

    good = ev["station_first"][ev["station_first"] > 0.5]
    bad = ev["station_first"][ev["station_first"] <= 0.5]
    ax.plot(
        np.zeros_like(good),
        good,
        marker="o",
        ls="none",
        ms=4.0,
        mfc="white",
        mec=DEPTH_INK[0],
        mew=1.0,
        zorder=6,
    )
    ax.plot(
        np.zeros_like(bad),
        bad,
        marker="o",
        ls="none",
        ms=4.4,
        mfc="white",
        mec=WARM,
        mew=1.2,
        zorder=6,
    )
    ax.text(
        -0.24,
        1.075,
        f"at a camera: {len(good)} of the 8 stations sit between {good.min():.3f} and {good.max():.3f}",
        fontsize=6.9,
        color=INK,
        ha="left",
        va="center",
    )
    ax.annotate(
        f"the eighth, at {bad[0]:.3f}, excluded.\nA registration failure that\nthe skyline residual gate passed",
        xy=(0.07, bad[0]),
        xytext=(0.44, 0.300),
        fontsize=6.9,
        color=WARM,
        ha="left",
        va="center",
        linespacing=1.25,
        arrowprops=dict(arrowstyle="->", lw=0.7, color=WARM, shrinkB=3),
    )

    handles = [
        Line2D([], [], color=c, lw=1.6, marker="o", ms=3.6, label=labels[d]) for d, c in zip((1, 2, 3), DEPTH_INK)
    ]
    ax.legend(
        handles=handles,
        loc="lower left",
        bbox_to_anchor=(0.005, 0.005),
        fontsize=6.9,
        frameon=False,
        handlelength=1.6,
        labelspacing=0.32,
        borderpad=0.2,
    )

    ax.set_xticks(slots)
    ax.set_xticklabels(ev["labels"], fontsize=7.0)
    for slot, count in zip(slots, ev["counts"]):
        ax.annotate(
            f"n = {count}",
            xy=(slot, 0),
            xytext=(0, -17),
            textcoords="offset points",
            ha="center",
            va="top",
            fontsize=6.2,
            color=MUTED,
        )
    ax.set_xlim(-0.28, slots[-1] + 0.28)
    ax.set_ylim(0.0, 1.13)
    ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_xlabel("distance from the standpoint to the nearest registered panorama", labelpad=18)
    ax.set_ylabel("share of power landing on\nphotographed material")


def evidence_reach() -> None:
    closed, opened = load_visibility()
    ev = load_evidence()

    fig, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.46))
    panel_a(axes[0], closed, opened)
    panel_b(axes[1], ev)

    heads = (
        (
            "a  a path that comes back stays on visible surfaces",
            "observed means visible from the standpoint, where transmitter,\n"
            f"receiver and camera all stand. {len(closed)} standpoints, four city meshes",
        ),
        (
            "b  photographed is a radius, not a property of a square",
            "observed means a registered panorama photographed the surface.\n"
            f"Korenmarkt, 130 m crop, {len(ev['station_first'])} stations and "
            f"{ev['walk_standpoints']} walk standpoints",
        ),
    )
    for ax, (title, sub) in zip(axes, heads):
        ax.set_title(title, fontsize=8.2, color=INK, loc="left", pad=20.0)
        ax.text(
            0.0,
            1.012,
            sub,
            transform=ax.transAxes,
            fontsize=6.5,
            color=MUTED,
            ha="left",
            va="bottom",
            style="italic",
            linespacing=1.3,
        )
        ax.grid(True, alpha=0.20, lw=0.5)
        ax.set_axisbelow(True)

    fig.tight_layout(w_pad=1.0)
    fig.text(
        0.5,
        -0.012,
        "a: outputs/monostatic/monovis_*_visibility_locations.jsonl.    "
        "b: outputs/bounce_budget/korenmarkt_130m_bounce_evidence.json.    "
        "FIGURES/make_evidence_reach_figure.py",
        ha="center",
        va="top",
        fontsize=6.0,
        color=MUTED,
    )
    save(fig, "22_evidence_reach")


def main() -> int:
    apply_monograph_style(
        mode="png",
        extra_rc={
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "axes.titlesize": 8.2,
            "xtick.labelsize": 7.2,
            "ytick.labelsize": 7.2,
            "legend.fontsize": 6.9,
        },
    )
    evidence_reach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
