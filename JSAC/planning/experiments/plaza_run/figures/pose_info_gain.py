"""Pose-info-gain ablation for §VII.

Compare pose-aware tier-A/B telemetry vs pose-ablate (Cauchy worst-case
on tier-A/B). Same seed, same path model (plaza-specular). The headline
sum-rate is identical at this load (the budget gap is too generous for
pose info to bind), so the figure shows the slot-level distributions to
make that "no measurable gain" finding explicit.

Two panels:
  (a) per-slot delta-sumrate ECDF (aware - ablate), one curve per
      precoder. Centred on zero = honest finding of no gain.
  (b) per-body p_abs CDF, aware vs ablate, multi-body ECBF only.

Run:
    python -m JSAC.planning.experiments.plaza_run.figures.pose_info_gain
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from _data import PRECODER_DISPLAY, load_canonical
from _figstyle import apply_monograph_style, fig_size_ieee, save_both

FIG_DIR = Path(__file__).resolve().parent
PRECODER_ORDER = ["mrt", "wc_backoff", "multibody_ecbf", "oracle"]  # drop ZF (singular noise)
PRECODER_COLORS = {
    "mrt": "#2166ac",
    "wc_backoff": "#7f3b08",
    "multibody_ecbf": "#b2182b",
    "oracle": "#404040",
}


def main() -> None:
    apply_monograph_style(mode="png")
    aware = load_canonical("specular_aware")
    ablate = load_canonical("specular_ablate")

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.45))

    # Panel (a): per-slot delta-sumrate ECDF
    for pname in PRECODER_ORDER:
        idx = aware.precoder_index(pname)
        delta_mbps = (aware.sumrate[:, idx] - ablate.sumrate[:, idx]) / 1e6
        d = np.sort(delta_mbps)
        f = np.arange(1, len(d) + 1) / len(d)
        ax_a.plot(d, f, lw=1.6, label=PRECODER_DISPLAY[pname], color=PRECODER_COLORS[pname])
    ax_a.axvline(0.0, color="#404040", lw=0.9, ls=":")
    ax_a.set_xlabel(r"$\Delta$ sum-rate per slot (aware $-$ ablate, Mbps)")
    ax_a.set_ylabel("ECDF over slots")
    ax_a.set_ylim(0, 1)
    ax_a.set_xlim(-0.06, 0.06)
    ax_a.legend(loc="upper left", framealpha=0.95, fontsize=7.5)
    ax_a.set_title("(a) Slot-level sum-rate gain")
    ax_a.text(
        0.0,
        0.55,
        "All precoders: $\\Delta=0$\nat this load (budget slack\n$\\sim$ 4 orders of magnitude)",
        fontsize=7.5,
        ha="center",
        va="center",
        bbox=dict(facecolor="white", edgecolor="#888888", boxstyle="round,pad=0.3", alpha=0.95),
    )

    # Panel (b): per-body P_abs CDF, aware vs ablate, multi-body ECBF only
    p_idx = aware.precoder_index("multibody_ecbf")
    pabs_aware = aware.p_abs[..., p_idx].reshape(-1) * 1e6  # uW
    pabs_ablate = ablate.p_abs[..., p_idx].reshape(-1) * 1e6
    for arr, label, color, ls in [
        (pabs_aware, "Pose-aware", "#2166ac", "-"),
        (pabs_ablate, "Pose-ablate", "#b2182b", "--"),
    ]:
        s = np.sort(arr)
        f = np.arange(1, len(s) + 1) / len(s)
        ax_b.plot(s, f, lw=1.7, label=label, color=color, ls=ls)
    ax_b.set_xscale("log")
    ax_b.set_xlabel(r"$P_\mathrm{abs}$ per body-slot ($\mu$W)")
    ax_b.set_ylabel("ECDF over body-slots")
    ax_b.set_ylim(0, 1)
    ax_b.legend(loc="lower right", framealpha=0.95, fontsize=7.5)
    ax_b.set_title("(b) Per-body absorbed power, multi-body ECBF")
    ax_b.text(
        0.04,
        0.93,
        "Curves overlap to float32:\npose telemetry does not\naffect P$_{abs}$ at this load",
        transform=ax_b.transAxes,
        fontsize=7.5,
        ha="left",
        va="top",
        bbox=dict(facecolor="white", edgecolor="#888888", boxstyle="round,pad=0.3", alpha=0.95),
    )

    fig.tight_layout()
    pdf, png = save_both(fig, FIG_DIR / "pose_info_gain")
    plt.close(fig)
    print(f"saved {pdf}")
    print(f"saved {png}")
    for pname in PRECODER_ORDER:
        idx = aware.precoder_index(pname)
        d = (aware.sumrate[:, idx] - ablate.sumrate[:, idx]) / 1e6
        print(
            f"  {PRECODER_DISPLAY[pname]:>16s}: median dSR = {np.median(d):+.3f} Mbps, "
            f"max |dSR| = {np.abs(d).max():.3f} Mbps"
        )


if __name__ == "__main__":
    main()
