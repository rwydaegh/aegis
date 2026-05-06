"""Compare baseline vs low-rank ECBF solver wall time.

Synthesises rank-3 Q matrices matching plaza_run's empirical structure,
then times solve_multibody_ecbf in three modes:
    full           - legacy O(B M^2 K) per-body abs
    lowrank-r3     - decompose Q internally to rank 3
    lowrank-pre    - factor pre-computed by caller

Prints median + p10 + p90 ms per call.
"""

from __future__ import annotations

import sys
import time

import numpy as np

from aegis.coherent.multibody_ecbf import (
    solve_multibody_ecbf,
)


def _build(M: int, B: int, K: int, seed: int = 42):
    rng = np.random.default_rng(seed)
    Q_list = []
    U_arr = np.empty((B, M, 3), dtype=complex)
    D_arr = np.empty((B, 3), dtype=float)
    for b in range(B):
        U = (rng.standard_normal((M, 3)) + 1j * rng.standard_normal((M, 3))) / np.sqrt(2)
        d = np.abs(rng.standard_normal(3)) + 0.1
        Q = U @ np.diag(d) @ U.conj().T
        Q = 0.5 * (Q + Q.conj().T)
        Q_list.append(Q)
        # Reconstruct via eigh (consistent with what _decompose_lowrank does).
        evals, evecs = np.linalg.eigh(Q)
        D_arr[b] = np.maximum(evals[-3:][::-1], 0.0)
        U_arr[b] = evecs[:, -3:][:, ::-1]

    H = (rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))) / np.sqrt(2)
    W_mrt = (1.0 / np.sqrt(K)) * H.conj().T / np.linalg.norm(H.conj().T, axis=0, keepdims=True)
    p_mrt = np.array([float(np.real(np.trace(W_mrt.conj().T @ Q @ W_mrt))) for Q in Q_list])
    L_list = list(0.5 * p_mrt)
    return H, Q_list, L_list, U_arr, D_arr


def _bench(H, Q_list, L_list, *, mode: str, runs: int, U_arr=None, D_arr=None, lambda_init=None) -> dict:
    kwargs = dict(P=1.0, noise_power=1e-2, max_outer=8, lambda_init=lambda_init)
    if mode == "lowrank-r3":
        kwargs["lowrank_rank"] = 3
    elif mode == "lowrank-pre":
        kwargs["lowrank_factor"] = (U_arr, D_arr)

    # Warmup
    for _ in range(2):
        solve_multibody_ecbf(H, Q_list, L_list, **kwargs)

    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        solve_multibody_ecbf(H, Q_list, L_list, **kwargs)
        times.append(time.perf_counter() - t0)
    times = np.array(times) * 1e3
    return {
        "med": float(np.median(times)),
        "p10": float(np.percentile(times, 10)),
        "p90": float(np.percentile(times, 90)),
    }


def main() -> None:
    print("# Solver wall time: baseline vs low-rank")
    print(f"#  {'M':>4s} {'B':>3s} {'K':>3s} {'mode':<14s} {'med_ms':>8s} {'p10':>7s} {'p90':>7s}  warm?")
    for M, B, K in [(64, 50, 25), (256, 50, 25)]:
        H, Q_list, L_list, U_arr, D_arr = _build(M, B, K)

        # Determine warm-start lambdas via first solve.
        _, diag = solve_multibody_ecbf(
            H, Q_list, L_list, P=1.0, noise_power=1e-2, max_outer=20, return_diagnostics=True
        )
        lam_warm = np.asarray(diag.lambdas)

        runs = 30 if M == 64 else 8
        for mode in ("full", "lowrank-r3", "lowrank-pre"):
            for warm_label, lam in (("cold", None), ("warm", lam_warm)):
                r = _bench(H, Q_list, L_list, mode=mode, runs=runs, U_arr=U_arr, D_arr=D_arr, lambda_init=lam)
                print(
                    f"   {M:>4d} {B:>3d} {K:>3d} {mode:<14s} {r['med']:>8.2f} "
                    f"{r['p10']:>7.2f} {r['p90']:>7.2f}  {warm_label}"
                )
        sys.stdout.flush()


if __name__ == "__main__":
    main()
