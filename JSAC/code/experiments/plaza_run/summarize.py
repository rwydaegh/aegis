"""Headline-numbers summary for one plaza_run NPZ.

Prints the per-precoder violation %, sum-rate, and infeasibility rate so the
hero numbers can be eyeballed before brief 09 turns them into PDFs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def summarize(npz_path: Path) -> None:
    f = np.load(npz_path, allow_pickle=False)
    p_abs = f["p_abs"]
    sumrate = f["sumrate"]
    violation = f["violation"]
    infeasible = f["infeasible"]
    tier = f["tier"]
    budgets = f["body_budgets_w"]
    names = [str(n) for n in f["precoder_names"]]
    cadence = f["cadence_ms"]

    print(f"=== {npz_path.name} ===")
    print(
        "scene={} phy={} pose={} paths={} bodies={} slots={}".format(
            str(f["scene_hash"]),
            str(f["phy_mode"]),
            str(f["pose_mode"]),
            str(f["paths_mode"]),
            int(f["n_bodies"]),
            int(f["n_slots"]),
        )
    )
    print(f"tier breakdown: A={int((tier == 0).sum())} B={int((tier == 1).sum())} C={int((tier == 2).sum())}")
    print(f"budget per body (median): {float(np.median(budgets)):.4f} W")
    print()
    print(f"{'precoder':16s} {'violation%':>10s} {'sumrate(Mbps)':>14s} {'p_abs/L median':>16s} {'infeas%':>9s}")
    for i, name in enumerate(names):
        v_pct = float(violation[..., i].mean()) * 100
        sr_mbps = float(sumrate[:, i].mean()) / 1e6
        ratio = float(np.median(p_abs[..., i] / budgets[None, :]))
        inf_pct = float(infeasible[:, i].mean()) * 100
        print(f"  {name:14s} {v_pct:9.2f}% {sr_mbps:13.1f} {ratio:15.2e} {inf_pct:8.1f}%")

    print()
    print("Cadence (ms) p10 / p50 / p90:")
    for i, stage in enumerate(("q_refresh", "precoder", "rt", "phy")):
        col = cadence[:, i]
        print(
            f"  {stage:10s} {float(np.percentile(col, 10)):6.1f} / "
            f"{float(np.percentile(col, 50)):6.1f} / "
            f"{float(np.percentile(col, 90)):6.1f}"
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("npz", nargs="+", type=Path)
    args = p.parse_args()
    for npz in args.npz:
        summarize(npz)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
