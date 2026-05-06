"""Extract paper-ready numbers from the v6 binding-regime runs.

Loads:
    outputs/v6_aware/plaza_run_seed42_physhannon_poseaware_pathsdict_v6_aware.npz
    outputs/v6_ablate/plaza_run_seed42_physhannon_poseablate_pathsdict_v6_ablate.npz

Prints:
    - Per-precoder fallback rate (paper §VII.E)
    - Per-precoder violation rate over body-slots (paper §VII.D)
    - Per-precoder median p_abs / L_RL (paper §VII.D, §VII.E)
    - Per-precoder mean sum-rate (Mbps)
    - Pose-info delta sum-rate ECDF percentiles (paper §VII.E):
        median, p10/p90, mean, fraction in left/right modes
    - Cadence p10/p50/p90 per stage (paper tab:cadence)

Run:
    /home/user/aegis/.venv/bin/python -m JSAC.code.experiments.plaza_run.v6_analysis
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .figures._data import load_run

OUT = Path("JSAC/code/experiments/plaza_run/outputs")
AWARE_NPZ = OUT / "v6_aware" / "plaza_run_seed42_physhannon_poseaware_pathsdict_v6_aware.npz"
ABLATE_NPZ = OUT / "v6_ablate" / "plaza_run_seed42_physhannon_poseablate_pathsdict_v6_ablate.npz"

PRECODER_ORDER = ["mrt", "zf", "wc_backoff", "multibody_ecbf", "oracle"]


def main() -> None:
    if not AWARE_NPZ.exists():
        print(f"# AWARE not yet produced: {AWARE_NPZ}")
        return
    if not ABLATE_NPZ.exists():
        print(f"# ABLATE not yet produced: {ABLATE_NPZ}")
    aware = load_run(AWARE_NPZ, label="v6_aware")
    has_ablate = ABLATE_NPZ.exists()
    if has_ablate:
        ablate = load_run(ABLATE_NPZ, label="v6_ablate")

    L_med_w = float(np.median(aware.body_budgets_w))
    print(
        f"# v6 binding regime: tx={aware.tx_power_dbm:.0f} dBm, "
        f"freq={aware.freq_hz / 1e9:.2f} GHz, B={aware.n_bodies}, "
        f"slots={aware.n_slots}, L_RL median = {L_med_w * 1e3:.2f} mW/body"
    )
    print()

    print("# Aware - per-precoder summary")
    print(
        f"# {'precoder':<16} {'viol%':>7} {'infeas%':>8} {'med pa/L':>10} "
        f"{'mean SR Mbps':>13} {'mean SR Gbps':>13}"
    )
    for pname in PRECODER_ORDER:
        idx = aware.precoder_index(pname)
        viol_pct = aware.violation[..., idx].mean() * 100.0
        infeas_pct = aware.infeasible[:, idx].mean() * 100.0
        ratio_med = float(np.median(aware.p_abs[..., idx] / aware.body_budgets_w[None, :]))
        sr_mean_mbps = aware.sumrate[:, idx].mean() / 1e6
        print(
            f"  {pname:<16} {viol_pct:>7.2f} {infeas_pct:>8.2f} {ratio_med:>10.3f} "
            f"{sr_mean_mbps:>13.1f} {sr_mean_mbps / 1000:>13.2f}"
        )

    if has_ablate:
        print()
        print("# Ablate - per-precoder summary")
        print(f"# {'precoder':<16} {'viol%':>7} {'infeas%':>8} {'med pa/L':>10} {'mean SR Mbps':>13}")
        for pname in PRECODER_ORDER:
            idx = ablate.precoder_index(pname)
            viol_pct = ablate.violation[..., idx].mean() * 100.0
            infeas_pct = ablate.infeasible[:, idx].mean() * 100.0
            ratio_med = float(np.median(ablate.p_abs[..., idx] / ablate.body_budgets_w[None, :]))
            sr_mean_mbps = ablate.sumrate[:, idx].mean() / 1e6
            print(f"  {pname:<16} {viol_pct:>7.2f} {infeas_pct:>8.2f} {ratio_med:>10.3f} {sr_mean_mbps:>13.1f}")

        print()
        print("# Pose-info-gain (aware - ablate) per slot, per precoder")
        print(f"# {'precoder':<16} {'p10':>9} {'med':>9} {'p90':>9} {'mean':>9} {'min':>9} {'max':>9}  (Mbps)")
        for pname in PRECODER_ORDER:
            idx_a = aware.precoder_index(pname)
            idx_b = ablate.precoder_index(pname)
            d_mbps = (aware.sumrate[:, idx_a] - ablate.sumrate[:, idx_b]) / 1e6
            print(
                f"  {pname:<16} "
                f"{np.percentile(d_mbps, 10):>9.2f} "
                f"{np.median(d_mbps):>9.2f} "
                f"{np.percentile(d_mbps, 90):>9.2f} "
                f"{d_mbps.mean():>9.2f} "
                f"{d_mbps.min():>9.2f} "
                f"{d_mbps.max():>9.2f}"
            )

        print()
        print("# Bimodal trade-off: fraction of slots with |dSR| > 1 Gbps, by precoder")
        for pname in ("multibody_ecbf", "oracle"):
            idx_a = aware.precoder_index(pname)
            idx_b = ablate.precoder_index(pname)
            d = (aware.sumrate[:, idx_a] - ablate.sumrate[:, idx_b]) / 1e6
            n = len(d)
            left_pct = float(np.mean(d < -1000)) * 100  # aware much worse
            right_pct = float(np.mean(d > 1000)) * 100  # aware much better
            zero_pct = float(np.mean(np.abs(d) < 100)) * 100  # tied
            print(
                f"  {pname:<16} left (aware worse, dSR<-1Gbps): {left_pct:5.1f}%  "
                f"right (aware better, dSR>+1Gbps): {right_pct:5.1f}%  "
                f"|dSR|<100Mbps: {zero_pct:5.1f}%  N={n}"
            )

    print()
    print("# Cadence (paper tab:cadence)")
    stages = ["q_refresh", "precoder", "rt", "phy"]
    for i, name in enumerate(stages):
        col = aware.cadence_ms[:, i]
        print(
            f"  {name:<10} p10={np.percentile(col, 10):.1f} ms  "
            f"p50={np.percentile(col, 50):.1f} ms  "
            f"p90={np.percentile(col, 90):.1f} ms  "
            f"mean={np.mean(col):.1f} ms"
        )


if __name__ == "__main__":
    main()
