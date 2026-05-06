"""Validate low-rank ECBF solver against full-rank baseline on real Q.

Loads the Q stack saved by ``profile_q.py`` (real plaza_run geometry)
and compares full-rank solve_multibody_ecbf vs lowrank_rank=3 across:

    - precoder W match (relative Frobenius)
    - per-body absorbed power (max relative error)
    - sum-rate (relative error)
    - solver convergence stability (n_outer, residual)

Acceptance: max p_abs error < 1% AND max sum-rate error < 1%.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from aegis.coherent.multibody_ecbf import solve_multibody_ecbf


def _sum_rate(W: np.ndarray, H: np.ndarray, sigma2: float) -> float:
    HW = H @ W
    sigp = np.abs(np.diag(HW)) ** 2
    interf = np.sum(np.abs(HW) ** 2, axis=1) - sigp
    sinr = sigp / (interf + sigma2)
    return float(np.sum(np.log2(1.0 + sinr)))


def _per_body_abs_full(W: np.ndarray, Q_arr: np.ndarray) -> np.ndarray:
    return np.real(np.einsum("ik,bij,jk->b", W.conj(), Q_arr, W, optimize=True))


def main() -> None:
    npz_path = Path("JSAC/code/experiments/plaza_run/outputs/profile_q.npz")
    if not npz_path.exists():
        raise SystemExit(f"Q dump not found: {npz_path}. Run profile_q.py first.")

    Q_arr = np.load(npz_path)["Q"].astype(complex)  # (B, M, M)
    B, M, _ = Q_arr.shape
    print(f"# Loaded Q shape: {Q_arr.shape}")

    rng = np.random.default_rng(42)
    K = 25  # served-user count to match plaza_run config
    sigma2 = 1e-2

    # Synthesise H consistent with the array size.
    H = (rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))) / np.sqrt(2)
    # Normalise channel rows to ~unit power per user.
    H = H / np.linalg.norm(H, axis=1, keepdims=True) * np.sqrt(M)

    # Build budgets that put us in a binding regime: 30% of MRT absorption.
    W_mrt = (1.0 / np.sqrt(K)) * H.conj().T / np.linalg.norm(H.conj().T, axis=0, keepdims=True)
    W_mrt = W_mrt * np.sqrt(1.0 / np.sum(np.abs(W_mrt) ** 2))
    p_mrt = _per_body_abs_full(W_mrt, Q_arr)
    L_list = list(0.30 * p_mrt + 1e-12)

    Q_list = [Q_arr[u] for u in range(B)]

    print(f"# B={B}  M={M}  K={K}  budget = 0.30 x MRT absorption (binding)")
    print()

    print("# Test 1: full-rank vs lowrank_rank=3")
    W_full, diag_full = solve_multibody_ecbf(
        H, Q_list, L_list, P=1.0, noise_power=sigma2, max_outer=20, return_diagnostics=True
    )
    W_lr3, diag_lr3 = solve_multibody_ecbf(
        H, Q_list, L_list, P=1.0, noise_power=sigma2, max_outer=20, return_diagnostics=True, lowrank_rank=3
    )

    W_full = np.asarray(W_full)
    W_lr3 = np.asarray(W_lr3)

    # Phase-aligned column distance: precoder columns are unique only up
    # to a per-column unimodular phase, so compare the per-column subspace
    # via the inner-product-magnitude metric, then compute aggregate.
    def _W_align_err(A: np.ndarray, B: np.ndarray) -> float:
        col_dot = np.sum(A.conj() * B, axis=0)
        return float(1.0 - np.mean(np.abs(col_dot) / (np.linalg.norm(A, axis=0) * np.linalg.norm(B, axis=0))))

    p_full = _per_body_abs_full(W_full, Q_arr)
    p_lr3 = _per_body_abs_full(W_lr3, Q_arr)
    sr_full = _sum_rate(W_full, H, sigma2)
    sr_lr3 = _sum_rate(W_lr3, H, sigma2)

    p_err = np.max(np.abs(p_lr3 - p_full) / np.maximum(p_full, 1e-30))
    sr_err = abs(sr_lr3 - sr_full) / max(abs(sr_full), 1e-30)
    W_err = _W_align_err(W_full, W_lr3)

    print(
        f"  full     n_outer={diag_full.n_outer:2d} method={diag_full.method:<16s} "
        f"resid={diag_full.residual:.2e} sumrate={sr_full:.4f}"
    )
    print(
        f"  lr3      n_outer={diag_lr3.n_outer:2d}  method={diag_lr3.method:<16s} "
        f"resid={diag_lr3.residual:.2e} sumrate={sr_lr3:.4f}"
    )
    print(f"  >> max relative p_abs error: {p_err:.3e}")
    print(f"  >> sum-rate relative error:  {sr_err:.3e}")
    print(f"  >> per-column 1-|<wf,wl>|:   {W_err:.3e}")

    print()
    print("# Test 2: across multiple seeds + budget tightness")
    errs = []
    for seed in [42, 43, 44, 45, 46]:
        rng2 = np.random.default_rng(seed)
        H2 = (rng2.standard_normal((K, M)) + 1j * rng2.standard_normal((K, M))) / np.sqrt(2)
        H2 = H2 / np.linalg.norm(H2, axis=1, keepdims=True) * np.sqrt(M)
        W_mrt2 = (1.0 / np.sqrt(K)) * H2.conj().T / np.linalg.norm(H2.conj().T, axis=0, keepdims=True)
        W_mrt2 = W_mrt2 * np.sqrt(1.0 / np.sum(np.abs(W_mrt2) ** 2))
        p_mrt2 = _per_body_abs_full(W_mrt2, Q_arr)
        for tightness in (0.10, 0.30, 0.60):
            L2 = list(tightness * p_mrt2 + 1e-12)
            W_a = np.asarray(solve_multibody_ecbf(H2, Q_list, L2, P=1.0, noise_power=sigma2, max_outer=15))
            W_b = np.asarray(
                solve_multibody_ecbf(H2, Q_list, L2, P=1.0, noise_power=sigma2, max_outer=15, lowrank_rank=3)
            )
            sr_a = _sum_rate(W_a, H2, sigma2)
            sr_b = _sum_rate(W_b, H2, sigma2)
            p_a = _per_body_abs_full(W_a, Q_arr)
            p_b = _per_body_abs_full(W_b, Q_arr)
            p_e = float(np.max(np.abs(p_b - p_a) / np.maximum(p_a, 1e-30)))
            sr_e = abs(sr_b - sr_a) / max(abs(sr_a), 1e-30)
            errs.append((seed, tightness, p_e, sr_e))
            print(
                f"  seed={seed} tightness={tightness:.2f}  p_err={p_e:.2e}  sr_err={sr_e:.2e}  "
                f"sr_a={sr_a:.3f} sr_b={sr_b:.3f}"
            )

    print()
    p_max = max(e[2] for e in errs)
    sr_max = max(e[3] for e in errs)
    print(f"# Worst-case across all configurations: p_err={p_max:.2e}  sr_err={sr_max:.2e}")
    if p_max < 0.01 and sr_max < 0.01:
        print("# RESULT: PASS (under 1% on both metrics)")
    else:
        print("# RESULT: REVIEW (exceeds 1% threshold; check if speed gain justifies)")


if __name__ == "__main__":
    main()
