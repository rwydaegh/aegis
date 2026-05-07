"""
Shared Matplotlib figure styling to match the monograph (`monograph/monograph.tex`).

Monograph settings:
- A4 paper (21.0 cm wide)
- geometry margin = 2.4 cm (both sides)
- base font size = 11 pt (article class)

So text width = 21.0 - 2*2.4 = 16.2 cm = 6.37795 in.
"""

from __future__ import annotations

# Per user request: keep scienceplots import available to scripts that want it.
import scienceplots  # noqa: F401

from dataclasses import dataclass
from typing import Literal, Optional

import matplotlib as mpl
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class MonographTypography:
    base_fontsize_pt: float = 11.0
    # Slightly smaller ticks/legends to avoid overcrowding at textwidth figures.
    tick_fontsize_pt: float = 10.0
    legend_fontsize_pt: float = 8.5
    title_fontsize_pt: float = 11.0


MONOGRAPH = MonographTypography()

# A4 paper width and geometry margin from monograph/monograph.tex
_A4_WIDTH_CM = 21.0
_MARGIN_CM = 2.4
TEXTWIDTH_CM = _A4_WIDTH_CM - 2 * _MARGIN_CM
TEXTWIDTH_IN = TEXTWIDTH_CM / 2.54


def fig_size_textwidth(*, aspect: float, scale: float = 2.0 / 3.0) -> tuple[float, float]:
    """
    Return (width, height) in inches for a figure that matches a fraction of TeX text width.

    aspect = height/width.
    """
    if not (0 < float(scale) <= 1.0):
        raise ValueError(f"scale must be in (0, 1]; got {scale!r}")
    w = float(TEXTWIDTH_IN) * float(scale)
    h = float(TEXTWIDTH_IN) * float(aspect) * float(scale)
    return (w, h)


# IEEE journal column widths (IEEEtran two-column class).
# A standard single column is 3.5 in (~88.9 mm); a `figure*` two-column wide
# float is 7.16 in (~181.9 mm).
IEEE_COL_IN = 3.5
IEEE_TWO_COL_IN = 7.16


def fig_size_ieee(*, columns: Literal[1, 2], aspect: float) -> tuple[float, float]:
    """
    Return (width, height) in inches sized for an IEEE two-column journal.

    columns = 1 -> single-column figure, 3.5 in wide.
    columns = 2 -> figure* (two-column wide float), 7.16 in wide.
    aspect = height / width.
    """
    if columns == 1:
        w = IEEE_COL_IN
    elif columns == 2:
        w = IEEE_TWO_COL_IN
    else:
        raise ValueError(f"columns must be 1 or 2, got {columns!r}")
    return (w, w * float(aspect))


def apply_monograph_style(
    *,
    mode: Literal["png", "pdf"] = "png",
    constrained_layout: bool = False,
    extra_rc: Optional[dict] = None,
) -> None:
    """
    Apply a strict, publication-oriented style:
    - scienceplots: 'science' + 'no-latex' for PNG iteration
    - scienceplots: 'science' + 'latex' for final PDF
    - monograph-matching typography (11pt base)
    """
    if mode not in ("png", "pdf"):
        raise ValueError(f"mode must be 'png' or 'pdf', got {mode!r}")

    if mode == "png":
        plt.style.use(["science", "no-latex"])
        use_tex = False
    else:
        # SciencePlots doesn't ship a "latex" style; LaTeX rendering is enabled via rcParams.
        # We keep the "science" style and turn on `text.usetex`.
        plt.style.use(["science"])
        use_tex = True

    rc: dict = {
        # Typography: align to the monograph
        "font.size": MONOGRAPH.base_fontsize_pt,
        "axes.labelsize": MONOGRAPH.base_fontsize_pt,
        "axes.titlesize": MONOGRAPH.title_fontsize_pt,
        "legend.fontsize": MONOGRAPH.legend_fontsize_pt,
        "xtick.labelsize": MONOGRAPH.tick_fontsize_pt,
        "ytick.labelsize": MONOGRAPH.tick_fontsize_pt,
        # Lines/markers: slightly heavier than defaults for print
        "lines.linewidth": 1.6,
        "lines.markersize": 4.5,
        "axes.linewidth": 0.8,
        # Grids: subtle, never dominant
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
        # Savefig defaults
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        # Layout (optional; many scripts call tight_layout explicitly)
        "figure.constrained_layout.use": bool(constrained_layout),
        # LaTeX text rendering for final PDFs
        "text.usetex": bool(use_tex),
    }

    if use_tex:
        # Match the monograph's font stack (Latin Modern) and math packages.
        # Keep this minimal to avoid TeX dependency issues across machines.
        rc["text.latex.preamble"] = (
            r"\usepackage[T1]{fontenc}"
            r"\usepackage{lmodern}"
            r"\usepackage{microtype}"
            r"\usepackage{amsmath,amssymb}"
            r"\usepackage{bm}"
        )

    if extra_rc:
        rc.update(extra_rc)

    mpl.rcParams.update(rc)

