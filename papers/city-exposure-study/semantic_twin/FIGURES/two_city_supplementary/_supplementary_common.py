"""Shared plotting helpers for the supplementary figures in this directory."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUTPUT_DIR = pathlib.Path(__file__).resolve().parent
DB = 10.0 / np.log(10.0)


@dataclass(frozen=True)
class CityStyle:
    label: str
    colour: str


def setup_style() -> None:
    """IEEE single-column feel, without a LaTeX dependency."""
    try:
        import scienceplots  # noqa: F401

        plt.style.use(["science", "ieee", "no-latex"])
    except Exception:  # pragma: no cover - style is cosmetic
        plt.style.use("default")
    mpl.rcParams.update(
        {
            "figure.dpi": 200,
            "savefig.dpi": 400,
            "font.size": 7,
            "axes.titlesize": 7.5,
            "axes.labelsize": 7,
            "legend.fontsize": 6,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.frameon": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.4,
            "lines.linewidth": 0.9,
            "lines.markersize": 2.6,
            "axes.prop_cycle": mpl.cycler(color=["#1b1b1b", "#c0392b", "#2471a3", "#117a3d", "#8e44ad"]),
        }
    )


def ecdf(values) -> tuple[np.ndarray, np.ndarray]:
    """Midpoint empirical CDF, the convention the published campaign figures use."""
    array = np.sort(np.asarray(values, dtype=np.float64))
    return array, (np.arange(array.size) + 0.5) / array.size


def save(fig, stem: str) -> None:
    for suffix in ("pdf", "png"):
        fig.savefig(OUTPUT_DIR / f"{stem}.{suffix}", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
