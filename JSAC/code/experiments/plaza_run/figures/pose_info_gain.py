"""Pose-info-gain ablation for §VII (binding regime).

Compare pose-aware tier-A/B telemetry vs pose-ablate (Cauchy worst-case
on tier-A/B) in the *binding* regime (43 dBm tx, ×0.1 budget multiplier
so L_RL = 16.3 mW). The slack regime version showed all curves
collapsed to zero — there pose telemetry doesn't bind because the
constraint is academic. The binding regime is where pose-coherent Q
shows its value: the Cauchy worst-case envelope is conservative enough
that it forces the constrained QCQP into min-absorption fallback far
more often, dropping sum-rate.

Two panels:
  (a) per-slot delta-sumrate ECDF (aware - ablate), one curve per
      precoder. Now non-zero — pose info translates to throughput
      headroom because the feasible set isn't being shrunk by Cauchy.
  (b) per-body P_abs CDF, aware vs ablate, multi-body ECBF only.

Run:
    python pose_info_gain.py
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
    import os

    apply_monograph_style(mode="png")
    # Default to the v6 binding regime once both aware + ablate runs land.
    # Falls back to the legacy `_bind5min` pair if v6 hasn't been built yet,
    # so the figure stays runnable during the rebuild.
    aware_key = os.environ.get("AEGIS_BIND_AWARE_KEY", "specular_v6_aware")
    ablate_key = os.environ.get("AEGIS_BIND_ABLATE_KEY", "specular_v6_ablate")
    try:
        aware = load_canonical(aware_key)
        ablate = load_canonical(ablate_key)
    except FileNotFoundError:
        aware = load_canonical("specular_bind")
        ablate = load_canonical("specular_bind_ablate")

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.45))

    # Panel (a): per-slot delta-sumrate ECDF
    medians: dict[str, float] = {}
    for pname in PRECODER_ORDER:
        idx_aw = aware.precoder_index(pname)
        idx_ab = ablate.precoder_index(pname)
        delta_mbps = (aware.sumrate[:, idx_aw] - ablate.sumrate[:, idx_ab]) / 1e6
        medians[pname] = float(np.median(delta_mbps))
        d = np.sort(delta_mbps)
        f = np.arange(1, len(d) + 1) / len(d)
        ax_a.plot(d, f, lw=1.6, label=PRECODER_DISPLAY[pname], color=PRECODER_COLORS[pname])
    ax_a.axvline(0.0, color="#404040", lw=0.9, ls=":")
    ax_a.set_xlabel(r"$\Delta$ sum-rate per slot (aware $-$ ablate, Mbps)")
    ax_a.set_ylabel("ECDF over slots")
    ax_a.set_ylim(0, 1)
    ax_a.legend(loc="upper left", framealpha=0.95, fontsize=7.5)
    ax_a.set_title("(a) Slot-level sum-rate gain (binding regime)")

    # Panel (b): per-body P_abs CDF, aware vs ablate, multi-body ECBF only
    p_idx_aw = aware.precoder_index("multibody_ecbf")
    p_idx_ab = ablate.precoder_index("multibody_ecbf")
    pabs_aware = aware.p_abs[..., p_idx_aw].reshape(-1) * 1e6  # uW
    pabs_ablate = ablate.p_abs[..., p_idx_ab].reshape(-1) * 1e6
    for arr, label, color, ls in [
        (pabs_aware, "Pose-aware", "#2166ac", "-"),
        (pabs_ablate, "Pose-ablate (Cauchy)", "#b2182b", "--"),
    ]:
        s = np.sort(arr)
        f = np.arange(1, len(s) + 1) / len(s)
        ax_b.plot(s, f, lw=1.7, label=label, color=color, ls=ls)
    # Mark per-body L_RL (median budget) for reference.
    L_med_uw = float(np.median(aware.body_budgets_w)) * 1e6
    ax_b.axvline(L_med_uw, color="#404040", lw=0.9, ls=":", label=r"$L_\mathrm{RL}$")
    ax_b.set_xscale("log")
    ax_b.set_xlabel(r"$P_\mathrm{abs}$ per body-slot ($\mu$W)")
    ax_b.set_ylabel("ECDF over body-slots")
    ax_b.set_ylim(0, 1)
    ax_b.legend(loc="lower right", framealpha=0.95, fontsize=7.5)
    ax_b.set_title("(b) Per-body absorbed power, multi-body ECBF")

    fig.tight_layout()
    pdf, png = save_both(fig, FIG_DIR / "pose_info_gain")
    plt.close(fig)
    print(f"saved {pdf}")
    print(f"saved {png}")
    print(f"binding regime: L_RL median = {L_med_uw:.1f} uW per body")
    for pname in PRECODER_ORDER:
        idx_aw = aware.precoder_index(pname)
        idx_ab = ablate.precoder_index(pname)
        d = (aware.sumrate[:, idx_aw] - ablate.sumrate[:, idx_ab]) / 1e6
        print(
            f"  {PRECODER_DISPLAY[pname]:>16s}: median dSR = {np.median(d):+.3f} Mbps, "
            f"mean dSR = {np.mean(d):+.3f} Mbps, max |dSR| = {np.abs(d).max():.3f} Mbps"
        )
    # Infeasibility comparison (where pose info changes the QCQP feasible set)
    for pname in ("multibody_ecbf", "oracle"):
        idx_aw = aware.precoder_index(pname)
        idx_ab = ablate.precoder_index(pname)
        infeas_aw = float(aware.infeasible[:, idx_aw].mean()) * 100
        infeas_ab = float(ablate.infeasible[:, idx_ab].mean()) * 100
        print(f"  {PRECODER_DISPLAY[pname]:>16s} infeasibility: aware {infeas_aw:.1f}%, ablate {infeas_ab:.1f}%")


if __name__ == "__main__":
    main()
