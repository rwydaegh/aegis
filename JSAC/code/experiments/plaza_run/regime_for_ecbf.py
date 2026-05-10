"""Search for a regime where the multi-body ECBF actually beats ZF + primal projection.

The conjecture is that ECBF's value is in shaping away from non-served bodies
(tier B/C) when the panel has spare nulling DoF. In a regime with K=25 served
out of 50 bodies, most binding bodies are tier-A served users whose
constraints conflict with their own rate; ZF + primal projection just scales
down uniformly and is equivalent.

We test:
    - K = 10 served, B = 40 non-served
    - K = 5  served, B = 45 non-served
    - K = 25 served, B = 25 non-served (baseline)

Each at 600 slots, E_RL = 3 V/m, 43 dBm.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]


def run_one(*, label, k_served, b_coop, c_sense, n_slots=600):
    from JSAC.code.experiments.plaza_run import scenario as scn

    scn.TIER_COUNTS = {"A": k_served, "B": b_coop, "C": c_sense}

    # Reload modules that captured TIER_COUNTS at import time.
    for mod_name in [
        "JSAC.code.experiments.plaza_run.run",
    ]:
        if mod_name in sys.modules:
            del sys.modules[mod_name]
    from JSAC.code.experiments.plaza_run import run as run_mod  # noqa

    n_total = k_served + b_coop + c_sense
    argv = [
        "regime_test",
        "--seed", "42",
        "--n-bodies", str(n_total),
        "--n-slots", str(n_slots),
        "--dt-s", "0.0333",
        "--pose-period", "30", "--rt-period", "30",
        "--tx-power-dbm", "43", "--reference-level-vpm", "3.0",
        "--paths", "plaza_specular", "--phy", "shannon",
        "--pose-source", "oracle", "--noise-power", "1e-12",
        "--oracle-noise-power", "1e-12",
        "--solver-backend", "jax",
        "--label-suffix", f"_regimeK{k_served}_v7",
        "--progress-every", "200",
    ]
    print(f"\n=== {label} ===  K_served={k_served}  B_coop={b_coop}  C_sense={c_sense}  total={n_total}")
    sys.argv = argv
    t0 = time.perf_counter()
    run_mod.main()
    wall = time.perf_counter() - t0

    out = REPO / "JSAC/code/experiments/plaza_run/outputs"
    cands = list(out.glob(f"plaza_run_seed42_*regimeK{k_served}_v7.npz"))
    print(f"  wall: {wall:.0f}s")
    if not cands:
        return
    z = np.load(cands[0], allow_pickle=True)
    pn = [str(s) for s in z["precoder_names"]]
    budgets = z["body_budgets_w"]

    for n in ["mrt", "zf", "wc_backoff", "zf_proj", "zf_proj_proposed", "multibody_ecbf", "oracle"]:
        if n not in pn:
            continue
        i = pn.index(n)
        v = z["violation"][:, :, i].mean() * 100
        sr = z["sumrate"][:, i].mean() / 1e9
        p99_mw = float(np.percentile(z["p_abs"][:, :, i], 99)) * 1000
        print(f"  {n:18s} viol={v:5.2f}% sr={sr:6.2f}Gbps p99={p99_mw:.2f}mW")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n-slots", type=int, default=600)
    args = p.parse_args()

    regimes = [
        ("K25",  25, 15, 10),  # baseline (paper's current)
        ("K10",  10, 30, 10),  # fewer served, more bystanders
        ("K5",    5, 35, 10),  # very few served
    ]
    for r in regimes:
        try:
            run_one(label=r[0], k_served=r[1], b_coop=r[2], c_sense=r[3],
                    n_slots=args.n_slots)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            print(f"  FAILED: {exc}")


if __name__ == "__main__":
    main()
