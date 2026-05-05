"""Chronic-dose ECDF for §VII.E.

Per-body absorbed energy (Joules) over the 5-minute trace, ECDF over the
50 bodies, colour-coded by tier. Uses the Multi-body ECBF precoder (the
proposed solution) but since precoders collapse to MRT in this regime,
the curve is invariant to that choice; we annotate that fact.

Run:
    python -m JSAC.planning.experiments.plaza_run.figures.chronic_dose
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from _data import TIER_DISPLAY, load_canonical
from _figstyle import apply_monograph_style, fig_size_ieee, save_both

FIG_DIR = Path(__file__).resolve().parent
TIER_COLORS = {0: "#b2182b", 1: "#2166ac", 2: "#404040"}


def chronic_dose_per_body(p_abs: np.ndarray, dt_s: float, precoder_idx: int) -> np.ndarray:
    """Return absorbed energy in Joules for each body over the full trace."""
    return p_abs[:, :, precoder_idx].sum(axis=0) * dt_s


def main() -> None:
    apply_monograph_style(mode="png")
    run = load_canonical("specular_aware")
    p_idx = run.precoder_index("multibody_ecbf")
    energy_j = chronic_dose_per_body(run.p_abs, run.dt_s, p_idx)
    duration_s = run.n_slots * run.dt_s

    fig, ax = plt.subplots(figsize=fig_size_ieee(columns=1, aspect=0.70))
    for tier_id, label in TIER_DISPLAY.items():
        mask = run.tier == tier_id
        if mask.sum() == 0:
            continue
        e = np.sort(energy_j[mask]) * 1e6  # µJ
        f = np.arange(1, len(e) + 1) / len(e)
        ax.plot(e, f, label=f"{label} (n={mask.sum()})", color=TIER_COLORS[tier_id], lw=1.7)
    ax.set_xlabel(rf"Absorbed energy over {duration_s:.0f} s trace ($\mu$J)")
    ax.set_ylabel("ECDF over bodies")
    ax.set_xscale("log")
    ax.set_ylim(0, 1)
    ax.legend(loc="lower right", framealpha=0.95)

    fig.tight_layout()
    pdf, png = save_both(fig, FIG_DIR / "chronic_dose")
    plt.close(fig)
    print(f"saved {pdf}")
    print(f"saved {png}")
    print(
        f"tier medians (uJ over {duration_s:.0f}s): "
        + ", ".join(
            f"{TIER_DISPLAY[t]}={np.median(energy_j[run.tier == t]) * 1e6:.2f}"
            for t in TIER_DISPLAY
            if (run.tier == t).any()
        )
    )


if __name__ == "__main__":
    main()
