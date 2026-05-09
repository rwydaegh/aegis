"""Binding-regime parameter sweep.

Patches scenario.py constants (BS height, body range) before invoking the
plaza_run main(), so we can search for a parameter combination where the
ZF baseline genuinely violates the per-body cap and the proposed ECBF
demonstrates value.

Run as:

    python -m JSAC.code.experiments.plaza_run.binding_sweep
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def run_one(*, label, bs_z, range_min, range_max, e_rl, n_bodies, tx_dbm,
            n_slots=600, k_per_side=8):
    import importlib

    from JSAC.code.experiments.plaza_run import scenario as scn

    # Patch scenario constants in-process. Re-import order matters because
    # downstream modules cache the BS_POSITION/range at import time, so we
    # delete the cache entries first and reimport.
    import numpy as np
    scn.BS_Z_M = float(bs_z)
    scn.BS_POSITION = np.array([scn.BS_X_M, scn.BS_Y_M, scn.BS_Z_M], dtype=np.float64)
    scn.RANGE_MIN_M = float(range_min)
    scn.RANGE_MAX_M = float(range_max)

    # Force reload of modules that captured these at import time.
    for mod_name in [
        "JSAC.code.experiments.plaza_run.paths",
        "JSAC.code.experiments.plaza_run.run",
    ]:
        if mod_name in sys.modules:
            del sys.modules[mod_name]
    from JSAC.code.experiments.plaza_run import run as run_mod  # noqa: E402

    # Build args.
    argv = [
        "binding_sweep",
        "--seed", "42",
        "--n-bodies", str(n_bodies),
        "--n-slots", str(n_slots),
        "--dt-s", "0.0333",
        "--pose-period", "30",
        "--rt-period", "30",
        "--tx-power-dbm", str(tx_dbm),
        "--reference-level-vpm", str(e_rl),
        "--paths", "plaza_specular",
        "--phy", "shannon",
        "--pose-source", "oracle",
        "--noise-power", "1e-3",
        "--solver-backend", "jax",
        "--n-array-per-side", str(k_per_side),
        "--label-suffix", f"_binding_{label}",
        "--progress-every", "200",
    ]
    print(f"\n=== {label} ===  BS_Z={bs_z}m  range=[{range_min},{range_max}]m  "
          f"E_RL={e_rl}V/m  N={n_bodies}  P_tx={tx_dbm}dBm")
    sys.argv = argv
    t0 = time.perf_counter()
    run_mod.main()
    wall = time.perf_counter() - t0

    # Read back the NPZ for per-precoder stats.
    out = REPO / "JSAC/code/experiments/plaza_run/outputs"
    cands = list(out.glob(f"plaza_run_seed42_*_binding_{label}.npz"))
    print(f"  wall: {wall:.0f}s")
    if cands:
        z = np.load(cands[0], allow_pickle=True)
        pn = [str(s) for s in z["precoder_names"]]
        for name in ["mrt", "zf", "wc_backoff", "multibody_ecbf", "oracle"]:
            if name not in pn:
                continue
            i = pn.index(name)
            v = float(z["violation"][:, :, i].mean()) * 100
            sr = float(z["sumrate"][:, i].mean()) / 1e9
            fb = float(z["infeasible"][:, i].mean()) * 100
            p99_mw = float(np.percentile(z["p_abs"][:, :, i], 99)) * 1000
            print(f"  {name:18s} viol={v:5.2f}% sr={sr:6.2f}Gbps fb={fb:4.1f}% p99={p99_mw:.1f}mW")
        # binding score: high ZF violation rate + low ECBF violation = good binding
        zf_v = float(z["violation"][:, :, pn.index("zf")].mean()) * 100
        ecbf_v = float(z["violation"][:, :, pn.index("multibody_ecbf")].mean()) * 100
        ecbf_sr = float(z["sumrate"][:, pn.index("multibody_ecbf")].mean()) / 1e9
        print(f"  >>> BINDING SCORE: ZF={zf_v:.2f}%  ECBF={ecbf_v:.2f}%  ECBF_SR={ecbf_sr:.2f}Gbps")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n-slots", type=int, default=600)
    args = p.parse_args()

    # Sweep grid: 5 regimes, ~3-5 min each at 600 slots.
    regimes = [
        # label,        bs_z, range_min, range_max, e_rl, n_bodies, tx_dbm
        ("A_baseline",  12.0, 5.0, 55.0,  6.0, 50, 43),
        ("B_lowBS",      4.0, 5.0, 55.0,  6.0, 50, 43),
        ("C_strict",    12.0, 5.0, 55.0,  3.0, 50, 43),
        ("D_combo",      4.0, 3.0, 25.0,  3.0, 50, 43),
        ("E_aggressive", 4.0, 3.0, 20.0,  3.0, 80, 43),
    ]
    for r in regimes:
        try:
            run_one(label=r[0], bs_z=r[1], range_min=r[2], range_max=r[3],
                    e_rl=r[4], n_bodies=r[5], tx_dbm=r[6], n_slots=args.n_slots)
        except Exception as exc:
            print(f"  FAILED: {exc}")


if __name__ == "__main__":
    main()
