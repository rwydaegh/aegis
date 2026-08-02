"""Explainer figures for PAPER_METHODS.md.

These exist to make the method understandable before any result is quoted, so
they are drawn to be read rather than to be pretty. Every number in them comes
from the shipped models rather than from a sketch, which is why the elevation
weight panels import the real illumination laws instead of redrawing 1/sin^3 by
hand.

    python figures/make_explainer_figures.py

Writes PDF for the paper and PNG for looking at.
"""

from __future__ import annotations

import pathlib
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, FancyArrowPatch, Rectangle

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/user/aegis/theory/scripts")

from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

from semantic_twin.propagation.directions import (  # noqa: E402
    MODELS,
    elevation_band_measure,
)

OUT = pathlib.Path(__file__).resolve().parent

#: Rooftop class: antenna height above the pedestrian's head, and horizontal
#: range. These are the numbers the shipped model carries.
ROOF_H = (13.5, 43.5)
ROOF_D = (25.0, 250.0)
STREET_H = (2.5, 6.5)
STREET_D = (10.0, 150.0)

INK = "#1a1a1a"
SKY = "#2f6fb5"
WARM = "#d1622b"
MUTED = "#8a8f98"
FILL = "#e8e4dc"


def save(fig, stem: str) -> None:
    for suffix in ("pdf", "png"):
        fig.savefig(OUT / f"{stem}.{suffix}", dpi=300)
    plt.close(fig)
    print(f"wrote {stem}.pdf and {stem}.png")


def elevation_geometry() -> None:
    """Why a steep arrival means a near source, not a high one.

    This is the figure that answers the question the elevation band always
    provokes: how can a base station be 60 degrees up. It is 60 degrees up
    because you are standing 25 m from a 45 m building, not because anything
    floats above a roof.
    """
    fig, ax = plt.subplots(figsize=fig_size_ieee(columns=2, aspect=0.42))

    ground_y = 0.0
    ped_x = 0.0
    head = 1.5

    ax.axhline(ground_y, color=INK, lw=1.0, zorder=1)
    ax.add_patch(Rectangle((-30, -6), 320, 6, facecolor=FILL, edgecolor="none", zorder=0))

    # The pedestrian, drawn small because the point is the sightlines.
    ax.plot([ped_x, ped_x], [0, head], color=INK, lw=2.2, solid_capstyle="round", zorder=4)
    ax.plot([ped_x], [head + 0.25], marker="o", ms=5, color=INK, zorder=4)
    ax.text(-6, 7.0, "pedestrian,\nhead at 1.5 m", ha="right", va="bottom", fontsize=7.5, color=INK)

    # The pedestrian's own horizon, which is what every angle here is measured from.
    ax.plot([-18, 288], [head, head], color=MUTED, lw=0.9, ls=(0, (5, 4)), zorder=2)
    ax.text(
        150,
        head - 1.2,
        "the pedestrian's horizon: every angle in this study is measured from here",
        ha="center",
        va="top",
        fontsize=7.5,
        color=MUTED,
        style="italic",
    )

    # Three masts spanning the rooftop class, chosen to make the point. The arc
    # radii are staggered because all three angles share a vertex, and equal
    # radii would stack three labels on top of each other.
    # The label positions are given explicitly rather than derived, because all
    # three sightlines share a vertex and anything automatic stacks them.
    masts = [
        (25.0, 43.5, WARM, 34.0, 0.46, (28, 52), "tall mast, close\n43.5 m up, 25 m away"),
        (76.6, 13.5, SKY, 60.0, 0.60, (92, 30), "short mast, mid\n13.5 m up, 77 m away"),
        (249.3, 13.5, SKY, 96.0, 0.74, (238, 26), "short mast, far\n13.5 m up, 249 m away"),
    ]
    for x, h, colour, arc_r, along, label_xy, label in masts:
        top = head + h
        ax.add_patch(Rectangle((x - 7, ground_y), 14, top - 1.0, facecolor="#cfd4da", edgecolor=INK, lw=0.7, zorder=2))
        ax.plot([x, x], [top - 1.0, top], color=INK, lw=1.4, zorder=3)
        ax.plot([x], [top], marker="s", ms=5.5, color=colour, zorder=5)
        ax.add_patch(
            FancyArrowPatch(
                (x, top),
                (ped_x, head),
                arrowstyle="-|>",
                mutation_scale=9,
                color=colour,
                lw=1.4,
                shrinkA=3,
                shrinkB=3,
                zorder=4,
            )
        )
        elev = np.degrees(np.arctan2(h, x))
        ax.add_patch(
            Arc(
                (ped_x, head),
                arc_r,
                arc_r,
                angle=0,
                theta1=0,
                theta2=elev,
                color=colour,
                lw=1.0,
                ls=(0, (3, 2)),
                zorder=4,
            )
        )
        # Angle label sits on its own sightline, at a distance chosen per mast.
        ax.text(
            along * x,
            head + along * h + 1.6,
            f"{elev:.1f} deg",
            fontsize=8.5,
            color=colour,
            ha="center",
            va="bottom",
            zorder=6,
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.9),
        )
        ax.annotate(
            label,
            xy=(x, top + 1.0),
            xytext=label_xy,
            fontsize=7.5,
            color=colour,
            ha="center",
            va="bottom",
            arrowprops=dict(arrowstyle="-", lw=0.6, color=colour, shrinkB=2),
        )

    ax.set_xlim(-52, 292)
    ax.set_ylim(-9, 70)
    ax.set_xlabel("horizontal distance from the pedestrian (m)")
    ax.set_ylabel("height (m)")
    ax.set_title("A steep arrival means a near source, not a high one", fontsize=10)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(False)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    save(fig, "18_elevation_geometry")


def deployment_box() -> None:
    """The source population as a box in (distance, height), and its shadow in angle.

    Left panel is what a deployment assumption actually is: a set of admissible
    places to put a mast. Right panel is the only thing the tracer ever sees,
    which is how much power arrives from each elevation. The whole illumination
    model is the map between them, and the correction of 2026-08-02 was to that
    map and not to either end of it.
    """
    fig, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.42))
    fig.subplots_adjust(wspace=0.34)

    ax = axes[0]
    # Lines of constant elevation first, so the boxes sit on top of them.
    d = np.linspace(2, 340, 300)
    for elev, ly in ((3.1, None), (10.0, None), (30.0, 50.0), (60.1, 50.0)):
        ax.plot(d, d * np.tan(np.radians(elev)), color=MUTED, lw=0.8, ls=(0, (4, 3)), zorder=1)
        if ly is None:
            y = 306 * np.tan(np.radians(elev))
            ax.text(308, y, f"{elev:g} deg", fontsize=7, color=MUTED, va="center", ha="left")
        else:
            ax.text(
                ly / np.tan(np.radians(elev)), 51.5, f"{elev:g} deg", fontsize=7, color=MUTED, ha="center", va="bottom"
            )

    for (h0, h1), (d0, d1), colour, label, ly in (
        (ROOF_H, ROOF_D, WARM, "macro on rooftops", 0.62),
        (STREET_H, STREET_D, SKY, "street small cells", 0.5),
    ):
        ax.add_patch(
            Rectangle((d0, h0), d1 - d0, h1 - h0, facecolor=colour, alpha=0.20, edgecolor=colour, lw=1.3, zorder=2)
        )
        ax.text(
            d0 + 0.55 * (d1 - d0),
            h0 + ly * (h1 - h0),
            label,
            color=colour,
            fontsize=8.5,
            ha="center",
            va="center",
            zorder=4,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8),
        )

    ax.set_xlim(0, 342)
    ax.set_ylim(0, 57)
    ax.set_xlabel("horizontal range from the pedestrian (m)")
    ax.set_ylabel("antenna height above the head (m)")
    ax.set_title("Where a mast is allowed to be", fontsize=9.5)

    # The corner of the box that sets the steep edge, which is the whole answer
    # to why the band reaches 60 degrees.
    ax.plot([ROOF_D[0]], [ROOF_H[1]], marker="o", ms=7, mfc="none", mec=INK, mew=1.3, zorder=6)
    ax.annotate(
        "this one corner sets\nthe 60 deg upper edge",
        xy=(ROOF_D[0], ROOF_H[1]),
        xytext=(150, 50),
        fontsize=7.5,
        color=INK,
        ha="center",
        va="center",
        zorder=6,
        arrowprops=dict(arrowstyle="->", lw=0.8, color=INK, shrinkB=6),
    )

    ax = axes[1]
    edges = np.linspace(0.5, 62.0, 320)
    centres = 0.5 * (edges[:-1] + edges[1:])
    for name, colour, label in (
        ("rooftop", WARM, "macro on rooftops"),
        ("street_small_cell", SKY, "street small cells"),
    ):
        w = np.asarray(elevation_band_measure(MODELS[name], edges), dtype=float)
        w = w / w.max()
        ax.plot(centres, w, color=colour, lw=1.6, label=label)
        ax.fill_between(centres, 0, w, color=colour, alpha=0.15)

    ax.set_xlim(0, 62)
    ax.set_ylim(0, 1.14)
    ax.set_xlabel("elevation above the horizon (deg)")
    ax.set_ylabel("illumination density,\npeak normalised")
    ax.set_title("Where the power actually comes from", fontsize=9.5)
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    ax.axvspan(30, 62, color=MUTED, alpha=0.12, zorder=0)
    ax.text(
        46,
        0.50,
        "45 % of the rooftop band's\nsolid angle is out here,\nand it carries 3.3 %\nof the power",
        fontsize=7,
        color=INK,
        ha="center",
        va="center",
    )
    save(fig, "19_deployment_box")


def _first_hit(origin, direction, boxes, ground_y=0.0, far=200.0):
    """Distance to the first blocker along a 2D ray, or ``far`` if it escapes.

    The rays in this figure have to be occluded or the figure argues the
    opposite of what it says: an unoccluded fan makes it look as though
    buildings do not block, which is the one thing the whole method is about.
    """
    ox, oy = origin
    dx, dy = direction
    best = far
    if dy < 0:
        t = (ground_y - oy) / dy
        if 0 < t < best:
            best = t
    for bx, bw, bh in boxes:
        # Slab test against the axis aligned box [bx, bx+bw] x [0, bh].
        lo, hi = 0.0, best
        for o, dd, mn, mx in ((ox, dx, bx, bx + bw), (oy, dy, ground_y, bh)):
            if abs(dd) < 1e-12:
                if o < mn or o > mx:
                    lo, hi = 1.0, 0.0
                    break
            else:
                t0, t1 = (mn - o) / dd, (mx - o) / dd
                if t0 > t1:
                    t0, t1 = t1, t0
                lo, hi = max(lo, t0), min(hi, t1)
        if lo <= hi and lo > 1e-9:
            best = lo
    return best


def adjoint_idea() -> None:
    """Why the rays are launched from the pedestrian and not from the masts."""
    fig, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.44), sharey=True)

    # Placed so the observer stands in an open square rather than a narrow slot,
    # which is what the sites in this study actually are.
    buildings = [(-58, 18, 26), (-34, 16, 17), (18, 14, 30), (46, 18, 22)]

    for ax, mode in zip(axes, ("forward", "adjoint")):
        ax.axhline(0, color=INK, lw=1.0, zorder=3)
        for x, w, h in buildings:
            ax.add_patch(Rectangle((x, 0), w, h, facecolor="#cfd4da", edgecolor=INK, lw=0.7, zorder=2))
        ax.plot([0, 0], [0, 1.5], color=INK, lw=2.0, zorder=5)
        ax.plot([0], [1.9], marker="o", ms=4.5, color=INK, zorder=5)

        if mode == "forward":
            # Sources spray, and essentially nothing lands on the observer.
            for sx, sy in ((-50, 30), (-27, 21), (25, 34), (55, 26)):
                ax.plot([sx], [sy], marker="s", ms=5, color=WARM, zorder=5)
                for angle in np.linspace(190, 350, 19):
                    d = (np.cos(np.radians(angle)), np.sin(np.radians(angle)))
                    t = _first_hit((sx, sy), d, buildings, far=58.0)
                    ax.plot([sx, sx + t * d[0]], [sy, sy + t * d[1]], color=WARM, lw=0.4, alpha=0.35, zorder=1)
            ax.set_title("Forward: launch from every mast", fontsize=9.5)
            ax.text(
                0,
                -7.0,
                "almost no ray finds the pedestrian,\nso almost all of the work is wasted",
                ha="center",
                va="top",
                fontsize=7.5,
                color=WARM,
            )
        else:
            # One fan from the observer. Rays that reach the sky are the ones
            # that carry power, and the gaps between buildings are the sky
            # fraction the method actually measures.
            for angle in np.linspace(4, 176, 46):
                d = (np.cos(np.radians(angle)), np.sin(np.radians(angle)))
                t = _first_hit((0.0, 1.5), d, buildings, far=64.0)
                escaped = t >= 63.9
                ax.plot(
                    [0, t * d[0]],
                    [1.5, 1.5 + t * d[1]],
                    color=SKY if escaped else MUTED,
                    lw=0.6 if escaped else 0.5,
                    alpha=0.8 if escaped else 0.6,
                    zorder=1,
                )
            ax.set_title("Adjoint: launch from the pedestrian", fontsize=9.5)
            ax.text(
                0,
                -7.0,
                "every ray contributes. Blue reaches the sky, grey hits a wall.\nReciprocity turns an escape direction into an arrival direction",
                ha="center",
                va="top",
                fontsize=7.5,
                color=SKY,
            )

        ax.set_xlim(-70, 70)
        ax.set_ylim(-17, 48)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ("top", "right", "left", "bottom"):
            ax.spines[side].set_visible(False)
    save(fig, "20_adjoint_idea")


def one_ray() -> None:
    """What one traced ray contributes, from launch to deposit."""
    fig, ax = plt.subplots(figsize=fig_size_ieee(columns=2, aspect=0.36))

    ax.axhline(0, color=INK, lw=1.0, zorder=3)
    # Two facing walls. The path below reflects specularly off each in turn, so
    # the angle of incidence really does equal the angle of reflection here
    # rather than being drawn by eye.
    ax.add_patch(Rectangle((34, 0), 20, 26, facecolor="#cfd4da", edgecolor=INK, lw=0.7, zorder=2))
    ax.add_patch(Rectangle((-40, 0), 22, 40, facecolor="#cfd4da", edgecolor=INK, lw=0.7, zorder=2))
    ax.plot([0, 0], [0, 1.5], color=INK, lw=2.0, zorder=5)
    ax.plot([0], [1.9], marker="o", ms=4.5, color=INK, zorder=5)
    ax.text(0, -2.0, "$S$", ha="center", va="top", fontsize=10, color=INK)

    slope = np.tan(np.radians(20.0))
    p0 = np.array([0.0, 1.5])
    p1 = np.array([34.0, 1.5 + 34.0 * slope])  # right wall, vertical normal
    p2 = np.array([-18.0, p1[1] + 52.0 * slope])  # left wall, vertical normal
    p3 = p2 + np.array([46.0, 46.0 * slope])  # escapes
    path = np.vstack([p0, p1, p2, p3])
    throughput = [1.0, 0.42, 0.19]
    for i in range(len(path) - 1):
        ax.add_patch(
            FancyArrowPatch(
                tuple(path[i]),
                tuple(path[i + 1]),
                arrowstyle="-|>",
                mutation_scale=11,
                color=SKY,
                lw=0.9 + 3.0 * throughput[i],
                shrinkA=0,
                shrinkB=0,
                zorder=4,
            )
        )
    for i in (1, 2):
        ax.plot([path[i][0]], [path[i][1]], marker="o", ms=6, color=WARM, zorder=5)

    ax.annotate(
        "bounce 1. Multiply the throughput by the Fresnel\n"
        "power reflectance $R(\\theta)$, then draw specular or\n"
        "diffuse with probability $\\exp(-g^2)$",
        xy=tuple(p1),
        xytext=(60, 40),
        fontsize=7.4,
        color=WARM,
        ha="left",
        va="center",
        arrowprops=dict(arrowstyle="->", lw=0.7, color=WARM, shrinkB=4),
    )
    ax.annotate(
        "bounce 2. $w$ is now 0.19",
        xy=tuple(p2),
        xytext=(-44, 52),
        fontsize=7.4,
        color=WARM,
        ha="left",
        va="center",
        arrowprops=dict(arrowstyle="->", lw=0.7, color=WARM, shrinkB=5),
    )
    ax.annotate(
        "escapes at $\\hat u_{ext}$. Deposit $w$ into the bin for the\n"
        "direction it LEFT $S$ in, weighted by $Q_S(\\hat u_{ext})$",
        xy=tuple(p3),
        xytext=(36, 60),
        fontsize=7.4,
        color=SKY,
        ha="left",
        va="center",
        arrowprops=dict(arrowstyle="->", lw=0.7, color=SKY, shrinkB=5),
    )
    ax.annotate(
        "launch at $\\hat u_{loc}$ with $w = 1$",
        xy=(13, 1.5 + 13 * slope),
        xytext=(-45, -10),
        fontsize=7.4,
        color=SKY,
        ha="left",
        va="center",
        arrowprops=dict(arrowstyle="->", lw=0.7, color=SKY, shrinkB=3),
    )

    ax.set_xlim(-46, 116)
    ax.set_ylim(-15, 70)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title("One ray, from launch to deposit. Line thickness is throughput", fontsize=10)
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    save(fig, "21_one_ray")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    apply_monograph_style(mode="png")
    elevation_geometry()
    deployment_box()
    adjoint_idea()
    one_ray()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
