"""Hero figure for §VII.D — binding regime.

The nominal-load run shows precoder collapse (no constraint violations,
single sum-rate per path model). To expose the §IV multi-body QCQP, this
figure plots the *binding regime*: tx_power 43 dBm (macro mmWave) on a
post-2014 Brussels reference level (6 V/m), 8x8 panel, 9000 slots
(5 minutes at 30 fps). The 6 V/m reference is what the city of Brussels
held until 2014 and what Italy's outdoor "attention" level is today;
the 14.57 V/m current Brussels arrête is the slack regime where MRT is
feasible. In this regime MRT exceeds the RL budget on most body-slots,
WC back-off scales power down to comply, ZF natively achieves
compliance via interference suppression (M=64 ≫ K=25 leaves ample
nulling DOFs), and Multi-body ECBF returns the min-absorption fallback
on tier-C envelopes (Cauchy back-off is too pessimistic when the
constraint is binding) while the oracle's Newton converges most slots.

Two panels:
  (a) ECDF of p_abs / L_RL across body-slots, per precoder. MRT pushes
      past 1.0, WC back-off straddles it, ZF sits 2-3 orders below,
      ECBF/oracle near zero.
  (b) Pareto scatter — per-precoder mean sum-rate vs. violation rate,
      one dot per precoder. ZF dominates everything; MRT trades 66 %
      violations for 7 Gbps; ECBF/oracle live near (0, 0).

Two-column wide IEEE figure.

Run:
    python -m JSAC.code.experiments.plaza_run.figures.hero_binding
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from _data import PRECODER_DISPLAY, load_canonical
from _figstyle import apply_monograph_style, fig_size_ieee, save_both

FIG_DIR = Path(__file__).resolve().parent
PRECODER_ORDER = ["mrt", "zf", "wc_backoff", "multibody_ecbf", "oracle"]
PRECODER_COLORS = {
    "mrt": "#b2182b",
    "zf": "#ef8a62",
    "wc_backoff": "#fddbc7",
    "multibody_ecbf": "#2166ac",
    "oracle": "#67a9cf",
}
PRECODER_MARKERS = {
    "mrt": "o",
    "zf": "s",
    "wc_backoff": "D",
    "multibody_ecbf": "^",
    "oracle": "v",
}


def main() -> None:
    import os

    apply_monograph_style(mode="png")
    # Default to the v6 binding regime (43 dBm + 6 V/m + 8x8) once it has
    # been written; fall back to the older budget-multiplier-derived bind
    # NPZ for comparison while the v6 run is in flight.
    bind_key = os.environ.get("AEGIS_BIND_KEY", "specular_v6_aware")
    try:
        run = load_canonical(bind_key)
    except FileNotFoundError:
        run = load_canonical("specular_bind")

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.42))

    # Panel (a) — ECDF of p_abs / L_RL per precoder.
    for pname in PRECODER_ORDER:
        idx = run.precoder_index(pname)
        ratio = (run.p_abs[..., idx] / run.body_budgets_w[None, :]).reshape(-1)
        r = np.sort(ratio)
        f = np.arange(1, len(r) + 1) / len(r)
        ax_a.plot(
            r,
            f,
            lw=1.5,
            color=PRECODER_COLORS[pname],
            label=PRECODER_DISPLAY[pname],
        )
    ax_a.axvline(1.0, color="#404040", lw=1.0, ls=":", label="Brussels RL budget")
    ax_a.axvspan(1.0, 5.0, color="#b2182b", alpha=0.08)
    ax_a.set_xscale("log")
    ax_a.set_xlabel(r"$P_\mathrm{abs} / L_\mathrm{RL}$ per body-slot")
    ax_a.set_ylabel("ECDF over body-slots")
    ax_a.set_xlim(1e-4, 5.0)
    ax_a.set_ylim(0, 1)
    ax_a.legend(loc="upper left", framealpha=0.95, fontsize=7)
    ax_a.set_title("(a) Budget approach (binding regime)")

    # Panel (b) — Pareto scatter: violation rate vs. mean sum-rate.
    for pname in PRECODER_ORDER:
        idx = run.precoder_index(pname)
        viol_pct = run.violation[..., idx].mean() * 100.0
        sr_mbps = run.sumrate[:, idx].mean() / 1e6
        ax_b.scatter(
            viol_pct,
            sr_mbps,
            s=70,
            color=PRECODER_COLORS[pname],
            marker=PRECODER_MARKERS[pname],
            edgecolor="black",
            lw=0.5,
            zorder=3,
            label=PRECODER_DISPLAY[pname],
        )
    ax_b.set_xlabel("Violation rate over body-slots (%)")
    ax_b.set_ylabel("Mean sum-rate (Mbps)")
    ax_b.set_title("(b) Sum-rate vs. compliance Pareto")
    ax_b.legend(loc="best", framealpha=0.95, fontsize=7)
    ax_b.grid(True, alpha=0.3)

    fig.tight_layout()
    pdf, png = save_both(fig, FIG_DIR / "hero_binding")
    plt.close(fig)
    print(f"saved {pdf}")
    print(f"saved {png}")

    # Sanity print
    print(f"\nBinding regime: tx={run.tx_power_dbm} dBm, budget={run.body_budgets_w.mean() * 1e3:.2f} mW/body")
    for pname in PRECODER_ORDER:
        idx = run.precoder_index(pname)
        ratio = run.p_abs[..., idx] / run.body_budgets_w[None, :]
        viol_pct = run.violation[..., idx].mean() * 100.0
        sr_mbps = run.sumrate[:, idx].mean() / 1e6
        infeas_pct = run.infeasible[:, idx].mean() * 100.0
        print(
            f"  {PRECODER_DISPLAY[pname]:<18} median p_abs/L = {np.median(ratio):.3f}, "
            f"viol={viol_pct:.1f}%, sumrate={sr_mbps:.1f} Mbps, infeas={infeas_pct:.0f}%"
        )


if __name__ == "__main__":
    main()
