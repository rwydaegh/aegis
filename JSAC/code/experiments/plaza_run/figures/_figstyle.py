"""Style + IO helpers for plaza_run paper figures.

Re-exports from ``theory/scripts/_plot_style.py`` (sys.path stitch — that
module isn't a package). Adds a ``save_both`` helper that emits both a PDF
(canonical, for paper inclusion) and a PNG (for visual critique loops).

Convention: IEEE single column (3.5") by default. Use ``columns=2`` (7.16")
only for hero figures. Height is flexible; pick aspect by content.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_THEORY_SCRIPTS = _REPO_ROOT / "theory" / "scripts"
if str(_THEORY_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_THEORY_SCRIPTS))

import matplotlib.pyplot as plt  # noqa: E402
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402


def save_both(fig: plt.Figure, basename: Path | str, *, dpi: int = 220) -> tuple[Path, Path]:
    """Save ``basename.pdf`` (paper-canonical) and ``basename.png`` (critique view)."""
    base = Path(basename)
    base.parent.mkdir(parents=True, exist_ok=True)
    pdf = base.with_suffix(".pdf")
    png = base.with_suffix(".png")
    fig.savefig(pdf)
    fig.savefig(png, dpi=dpi)
    return pdf, png


__all__ = ["apply_monograph_style", "fig_size_ieee", "save_both"]
