"""Bystander-binding regime: where the multi-body QCQP could earn its keep.

Hypothesis: ZF nulls served users but does NOT null non-served bystanders.
Cross-stream interference at a bystander body can bind their per-body cap when
the bystander is close to the BS while served users are far. In this regime
primal projection scales the WHOLE precoder down (rate hit), but the QCQP /
null-augmented precoding can null specifically at the binding bystander
(tiny rate hit per nulled bystander, with M=64 elements and ~10 active
bystanders we have plenty of spare DoF).

Setup:
    - tier A (served): K=10 bodies at FAR range 30-50 m from BS
    - tier B (cooperative): 25 bodies at NEAR range 3-8 m from BS  (bystanders)
    - tier C (sensed):       10 bodies at NEAR range 3-8 m from BS  (bystanders)
    - total 45 bodies, 600 slots, E_RL=3 V/m, 43 dBm, 8x8 panel.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]


def _patched_assign_bodies(scn, near_tiers=("B", "C"), far_tiers=("A",),
                           near_range=(5.0, 12.0), far_range=(25.0, 50.0)):
    """Build a replacement assign_bodies with per-tier range bands."""
    import random as _random
    from JSAC.code.experiments.plaza_run.scenario import Body, BS_X_M, BS_Y_M, PLAZA_HALF_WIDTH_M, TIER_COUNTS

    def assign_bodies(n_bodies, rng, pose_paths):
        if n_bodies != sum(TIER_COUNTS.values()):
            raise ValueError(f"n_bodies={n_bodies} != tier sum {TIER_COUNTS}")
        tiers = []
        for t, c in TIER_COUNTS.items():
            tiers.extend([t] * c)
        rng.shuffle(tiers)

        available = list(pose_paths)
        rng.shuffle(available)
        picks = available[:n_bodies]

        out = []
        for i, (tier, pose_path) in enumerate(zip(tiers, picks, strict=True)):
            r_min, r_max = (near_range if tier in near_tiers else far_range)
            for _ in range(200):
                x = rng.uniform(-PLAZA_HALF_WIDTH_M, PLAZA_HALF_WIDTH_M)
                y_local = rng.uniform(-30.0, 30.0)
                r = float(np.linalg.norm([x - BS_X_M, y_local - BS_Y_M]))
                if r_min <= r <= r_max:
                    spawn = np.array([x, y_local], dtype=np.float64)
                    break
            else:
                # Fallback: place on broadside ray at mid-range.
                r_mid = 0.5 * (r_min + r_max)
                spawn = np.array([0.0, BS_Y_M + r_mid], dtype=np.float64)
            heading = rng.uniform(-np.pi, np.pi)
            out.append(Body(index=i, tier=tier, pose_path=pose_path,
                            spawn_xy=spawn, initial_heading_rad=heading))
        return out

    return assign_bodies


def main():
    from JSAC.code.experiments.plaza_run import scenario as scn

    # Tier counts: 10 served far, 25 bystanders near, 10 sensed near.
    scn.TIER_COUNTS = {"A": 10, "B": 25, "C": 10}
    # Allow the ENTIRE near range; the patched assigner re-bands per tier.
    scn.RANGE_MIN_M = 3.0
    scn.RANGE_MAX_M = 50.0
    # Loosen plaza walk so near bystanders don't immediately bounce out.
    scn.assign_bodies = _patched_assign_bodies(scn)

    for mod_name in [
        "JSAC.code.experiments.plaza_run.run",
        "JSAC.code.experiments.plaza_run.paths",
    ]:
        if mod_name in sys.modules:
            del sys.modules[mod_name]
    from JSAC.code.experiments.plaza_run import run as run_mod  # noqa

    n_total = sum(scn.TIER_COUNTS.values())
    argv = [
        "bystander_binding",
        "--seed", "42",
        "--n-bodies", str(n_total),
        "--n-slots", "600",
        "--dt-s", "0.0333",
        "--pose-period", "30",
        "--rt-period", "30",
        "--tx-power-dbm", "43",
        "--reference-level-vpm", "3.0",
        "--paths", "plaza_specular",
        "--phy", "shannon",
        "--pose-source", "oracle",
        "--noise-power", "1e-12",
        "--oracle-noise-power", "1e-12",
        "--solver-backend", "jax",
        "--label-suffix", "_bystander_v7",
        "--progress-every", "200",
    ]
    print(f"\n=== bystander-binding regime ===  K_served={scn.TIER_COUNTS['A']}  "
          f"B_coop={scn.TIER_COUNTS['B']}  C_sense={scn.TIER_COUNTS['C']}  "
          f"served@FAR=25-50m  bystanders@NEAR=5-12m")
    sys.argv = argv
    t0 = time.perf_counter()
    run_mod.main()
    wall = time.perf_counter() - t0

    # Read back stats.
    out = REPO / "JSAC/code/experiments/plaza_run/outputs"
    cands = list(out.glob("plaza_run_seed42_*_bystander_v7.npz"))
    print(f"  wall: {wall:.0f}s")
    if not cands:
        print("  NO NPZ written"); return
    z = np.load(cands[0], allow_pickle=True)
    pn = [str(s) for s in z["precoder_names"]]
    print(f"  precoders: {pn}")
    body_tier = z.get("body_tier", None)
    for n in ["mrt", "zf", "wc_backoff", "zf_proj", "multibody_ecbf", "oracle"]:
        if n not in pn:
            continue
        i = pn.index(n)
        v = z["violation"][:, :, i].mean() * 100
        sr = z["sumrate"][:, i].mean() / 1e9
        p99 = float(np.percentile(z["p_abs"][:, :, i], 99)) * 1000
        pmax = float(z["p_abs"][:, :, i].max()) * 1000
        print(f"  {n:18s}  viol={v:5.2f}%  sr={sr:6.2f} Gbps  p99={p99:6.2f} mW  pmax={pmax:6.2f} mW")
        # Per-tier violation breakdown.
        if body_tier is not None:
            tiers = np.array([str(t) for t in body_tier])
            for tier_name in ["A", "B", "C"]:
                mask = tiers == tier_name
                if mask.sum() == 0: continue
                vt = z["violation"][:, mask, i].mean() * 100
                pmaxt = float(z["p_abs"][:, mask, i].max()) * 1000
                print(f"    tier-{tier_name} (n={mask.sum()}): viol={vt:5.2f}%  pmax={pmaxt:6.2f} mW")


if __name__ == "__main__":
    main()
