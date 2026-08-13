"""Deterministic SciencePlots settings for IEEE Access figures."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import matplotlib as mpl
import matplotlib.pyplot as plt
import scienceplots  # noqa: F401  # Registers the SciencePlots style sheets.
from cycler import cycler

MM_PER_INCH = 25.4

# These values come from the May 2026 IEEE Access class. They are the actual
# \columnwidth and \textwidth, rather than generic IEEE approximations.
SINGLE_COLUMN_MM = 85.29
DOUBLE_COLUMN_MM = 177.53
SINGLE_COLUMN_IN = SINGLE_COLUMN_MM / MM_PER_INCH
DOUBLE_COLUMN_IN = DOUBLE_COLUMN_MM / MM_PER_INCH

# A color-vision-deficiency-safe set based on the Okabe-Ito palette. Every
# series also receives a distinct line and marker, so meaning never depends on
# color alone.
PALETTE = (
    "#000000",  # black
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#009E73",  # bluish green
    "#E69F00",  # orange
    "#CC79A7",  # reddish purple
)
LINE_STYLES = ("-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1)))
MARKERS = ("o", "s", "^", "D", "v", "P")


def figure_size(
    width: Literal["single", "double"] = "single",
    *,
    height_ratio: float = 0.72,
) -> tuple[float, float]:
    """Return an exact IEEE Access figure size in inches."""

    if height_ratio <= 0:
        raise ValueError("height_ratio must be positive")
    figure_width = SINGLE_COLUMN_IN if width == "single" else DOUBLE_COLUMN_IN
    return figure_width, figure_width * height_ratio


def series_style(index: int, *, markevery: int | float | tuple[int, int] = 1) -> dict[str, object]:
    """Return redundant color, line, and hollow-marker encoding for one series."""

    slot = index % len(PALETTE)
    color = PALETTE[slot]
    return {
        "color": color,
        "linestyle": LINE_STYLES[slot],
        "marker": MARKERS[slot],
        "markerfacecolor": "none",
        "markeredgecolor": color,
        "markevery": markevery,
    }


def _rc_parameters(
    width: Literal["single", "double"],
    height_ratio: float,
    use_tex: bool,
) -> dict[str, object]:
    style_cycle = cycler(color=PALETTE) + cycler(linestyle=LINE_STYLES) + cycler(marker=MARKERS)
    return {
        "axes.prop_cycle": style_cycle,
        "axes.grid": False,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "axes.unicode_minus": False,
        "figure.figsize": figure_size(width, height_ratio=height_ratio),
        "figure.dpi": 150,
        "figure.constrained_layout.use": True,
        "font.family": "serif",
        "font.serif": [
            "Nimbus Roman",
            "Times New Roman",
            "Times",
            "TeX Gyre Termes",
            "DejaVu Serif",
        ],
        "font.size": 8,
        "legend.fontsize": 7,
        "legend.frameon": False,
        "lines.linewidth": 1.1,
        "lines.markersize": 4.0,
        "lines.markerfacecolor": "none",
        "lines.markeredgewidth": 0.8,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.bbox": None,
        "savefig.dpi": 600,
        "savefig.facecolor": "white",
        "savefig.transparent": False,
        "svg.fonttype": "none",
        "svg.hashsalt": "aegis-city-exposure-study",
        "text.usetex": use_tex,
        "text.latex.preamble": (
            r"\usepackage{amsmath,amssymb}"
            r"\usepackage{newtxtext,newtxmath}"
            r"\usepackage{siunitx}"
        ),
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
    }


@contextmanager
def paper_style(
    width: Literal["single", "double"] = "single",
    *,
    height_ratio: float = 0.72,
    use_tex: bool = True,
) -> Iterator[None]:
    """Apply SciencePlots ``science`` and ``ieee`` with manuscript overrides."""

    if width not in {"single", "double"}:
        raise ValueError("width must be 'single' or 'double'")
    with plt.style.context(["science", "ieee"]):
        with mpl.rc_context(_rc_parameters(width, height_ratio, use_tex)):
            yield


def save_figure(
    figure: mpl.figure.Figure,
    output: str | Path,
    *,
    dpi: int = 600,
) -> None:
    """Save a PDF, PNG, or SVG with stable metadata and uncropped dimensions."""

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        metadata: dict[str, object] = {
            "Title": path.stem,
            "Author": "AEGIS city exposure study",
            "Creator": "Matplotlib with SciencePlots",
            "Producer": "Matplotlib",
            "CreationDate": None,
            "ModDate": None,
        }
        figure.savefig(path, metadata=metadata)
    elif suffix == ".png":
        figure.savefig(path, dpi=dpi, metadata={"Software": "Matplotlib with SciencePlots"})
    elif suffix == ".svg":
        figure.savefig(path, metadata={"Title": path.stem, "Creator": "Matplotlib with SciencePlots"})
    else:
        raise ValueError(f"unsupported figure extension: {path.suffix}")
