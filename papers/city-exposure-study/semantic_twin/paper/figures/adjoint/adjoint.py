"""Draw the receiver-side first-diffuse estimator used in the paper."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[1]
sys.path.insert(0, str(PAPER_ROOT / "figures"))

from _style.paper_style import paper_style, save_figure  # noqa: E402

BLUE = "#0000FF"
RED = "#FF0000"
ORANGE = "#FF7F00"
BUILDING = "#D6D6D6"
EDGE = "#222222"


def _buildings(ax: plt.Axes) -> None:
    blocks = ((0.02, 0.00, 0.22, 0.54), (0.67, 0.00, 0.26, 0.68))
    for x, y, width, height in blocks:
        ax.add_patch(Rectangle((x, y), width, height, facecolor=BUILDING, edgecolor=EDGE, linewidth=0.8))
    ax.plot([0.0, 1.0], [0.0, 0.0], color=EDGE, linewidth=0.8, marker="")


def _format(ax: plt.Axes, label: str) -> None:
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(-0.02, 0.95)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.text(0.015, 0.75, label, transform=ax.transAxes, ha="left", va="top", fontweight="bold")


def _forward_panel(ax: plt.Axes) -> None:
    _buildings(ax)
    receiver = np.array([0.50, 0.03])
    sources = np.column_stack(
        (
            np.concatenate((np.linspace(0.04, 0.22, 8), np.linspace(0.69, 0.91, 10))),
            np.concatenate((np.full(8, 0.57), np.full(10, 0.71))),
        )
    )
    for source in sources:
        ax.plot(
            [source[0], receiver[0]],
            [source[1], receiver[1]],
            color=RED,
            alpha=0.18,
            linewidth=0.55,
            marker="",
        )
    ax.scatter(sources[:, 0], sources[:, 1], marker="s", s=8, facecolors="none", edgecolors=RED, linewidths=0.6)
    ax.scatter(*receiver, s=22, facecolor=BLUE, edgecolor="white", linewidth=0.6, zorder=5)
    ax.text(0.02, 0.79, "roofline segments", color=RED, ha="left", va="center")
    ax.text(0.50, 0.10, "route point", color=BLUE, ha="center", va="bottom")
    ax.text(0.50, 0.89, "Forward: trace from every possible source", ha="center", va="center")
    _format(ax, "(a)")


def _adjoint_panel(ax: plt.Axes) -> None:
    _buildings(ax)
    receiver = np.array([0.50, 0.03])
    angles = np.deg2rad(np.linspace(18.0, 162.0, 19))
    length = 0.80
    endpoints = receiver + length * np.column_stack((np.cos(angles), np.sin(angles)))
    for endpoint in endpoints:
        ax.plot(
            [receiver[0], endpoint[0]],
            [receiver[1], endpoint[1]],
            color=BLUE,
            alpha=0.28,
            linewidth=0.65,
            marker="",
        )

    surface = np.array([0.24, 0.39])
    source_left = np.array([0.13, 0.57])
    source_right = np.array([0.79, 0.71])
    ax.plot([receiver[0], surface[0]], [receiver[1], surface[1]], color=BLUE, linewidth=1.35, marker="")
    ax.plot(
        [surface[0], source_left[0]],
        [surface[1], source_left[1]],
        color=RED,
        linestyle="--",
        linewidth=1.0,
        marker="",
    )
    ax.plot(
        [surface[0], source_right[0]],
        [surface[1], source_right[1]],
        color=RED,
        linestyle="--",
        linewidth=1.0,
        marker="",
    )
    ax.scatter(*surface, s=28, facecolor=ORANGE, edgecolor=EDGE, linewidth=0.6, zorder=5)
    ax.scatter(*receiver, s=22, facecolor=BLUE, edgecolor="white", linewidth=0.6, zorder=5)
    ax.plot([0.04, 0.22], [0.57, 0.57], color=RED, linewidth=1.4, marker="")
    ax.plot([0.69, 0.91], [0.71, 0.71], color=RED, linewidth=1.4, marker="")
    ax.annotate(
        "first surface",
        xy=surface,
        xytext=(0.28, 0.66),
        arrowprops={"arrowstyle": "->", "color": EDGE, "lw": 0.7},
        ha="left",
        va="center",
    )
    ax.text(0.64, 0.43, "source\nconnections", color=RED, ha="center", va="center")
    ax.text(0.50, 0.14, "route point", color=BLUE, ha="center", va="bottom")
    ax.text(0.50, 0.89, "Adjoint: launch once from the receiver", ha="center", va="center")
    _format(ax, "(b)")


def main() -> None:
    with paper_style("double", height_ratio=0.31, use_tex=True):
        figure, axes = plt.subplots(1, 2)
        _forward_panel(axes[0])
        _adjoint_panel(axes[1])
        save_figure(figure, HERE / "adjoint.pdf")
        save_figure(figure, HERE / "adjoint.png", dpi=300)
        plt.close(figure)


if __name__ == "__main__":
    main()
