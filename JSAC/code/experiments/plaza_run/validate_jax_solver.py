"""End-to-end validation: solve_multibody_ecbf vs solve_multibody_ecbf_jax.

Generates synthetic problems matching plaza-run scale (B=50, M=64 and M=256,
K=25, rank-3 Q), runs both solvers from cold start, compares:
  - returned W (Frobenius distance)
  - p_abs vector
  - method (mrt-feasible / multibody-ecbf / min-absorption)
  - residual + n_outer

Both solvers run identical Newton scaffolding so a divergence indicates
a kernel bug, not algorithm drift.

Run: AEGIS_ARRAY_BACKEND=jax .venv/bin/python -m JSAC.code.experiments.plaza_run.validate_jax_solver
"""

from __future__ import annotations

import os
import time

os.environ.setdefault("JAX_ENABLE_X64", "1")

import numpy as np

from aegis.coherent.multibody_ecbf import solve_multibody_ecbf
from aegis.coherent.multibody_ecbf_jax import solve_multibody_ecbf_jax


def make_problem(B=50, M=256, K=25, r=3, seed=0, budget_factor=0.3):
    """Synthetic plaza-like problem.

    The Q matrices are rank-r PSD with random orthonormal U and positive D;
    budgets are scaled so that MRT is infeasible (~budget_factor * MRT abs).
    """
    rng = np.random.default_rng(seed)
    U = rng.standard_normal((B, M, r)) + 1j * rng.standard_normal((B, M, r))
    for b in range(B):
        Q, _ = np.linalg.qr(U[b])
        U[b] = Q
    D = rng.uniform(0.01, 1.0, size=(B, r))
    # Q[b] = U[b] diag(D[b]) U[b]^H
    Q_arr = np.einsum("bir,br,bjr->bij", U, D.astype(complex), U.conj())
    Q_arr = 0.5 * (Q_arr + Q_arr.conj().transpose(0, 2, 1))

    H = (rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))) / np.sqrt(M)
    P = 1.0
    # Compute MRT abs to set budgets.
    W_mrt_norm = H.conj().T / np.linalg.norm(H.conj().T, axis=0, keepdims=True)
    W_mrt = np.sqrt(P / K) * W_mrt_norm
    p_abs_mrt = np.real(np.einsum("ik,bij,jk->b", W_mrt.conj(), Q_arr, W_mrt))
    L = budget_factor * p_abs_mrt
    return H, Q_arr, L, P


def compare(name, H, Q_arr, L, P, noise_power, **kwargs):
    print(f"\n=== {name} (M={Q_arr.shape[1]}, B={Q_arr.shape[0]}, noise={noise_power}) ===")

    t0 = time.perf_counter()
    W_np, diag_np = solve_multibody_ecbf(
        H, Q_arr, L, P, noise_power=noise_power, return_diagnostics=True, lowrank_rank=3, **kwargs
    )
    t_np = time.perf_counter() - t0

    t0 = time.perf_counter()
    W_jax, diag_jax = solve_multibody_ecbf_jax(
        H, Q_arr, L, P, noise_power=noise_power, return_diagnostics=True, lowrank_rank=3, **kwargs
    )
    t_jax = time.perf_counter() - t0

    print(
        f"  np : method={diag_np.method:18s} n_outer={diag_np.n_outer:2d}  resid={diag_np.residual:.3e}  time={t_np * 1000:6.1f} ms"
    )
    print(
        f"  jax: method={diag_jax.method:18s} n_outer={diag_jax.n_outer:2d}  resid={diag_jax.residual:.3e}  time={t_jax * 1000:6.1f} ms"
    )

    # Numerical comparison.
    # W is determined up to a per-column phase (gauge freedom in eigh).
    # Compare |W^H W| (gauge-invariant) and the absorbed-power vectors.
    Gnp = np.abs(W_np.conj().T @ W_np)
    Gjax = np.abs(W_jax.conj().T @ W_jax)
    dG = np.linalg.norm(Gnp - Gjax) / max(np.linalg.norm(Gnp), 1e-30)
    dp = np.max(np.abs(diag_np.p_abs - diag_jax.p_abs))
    method_match = diag_np.method == diag_jax.method

    print(f"  |W^H W|: rel diff = {dG:.2e}    p_abs max diff = {dp:.2e}    method match: {method_match}")

    return {
        "name": name,
        "M": Q_arr.shape[1],
        "method_np": diag_np.method,
        "method_jax": diag_jax.method,
        "method_match": method_match,
        "dG": dG,
        "dp": dp,
        "t_np_ms": t_np * 1000,
        "t_jax_ms": t_jax * 1000,
    }


if __name__ == "__main__":
    results = []
    for seed in range(3):
        for M in [64, 256]:
            for noise_power in [None, 1e-2]:
                H, Q_arr, L, P = make_problem(B=50, M=M, K=25, r=3, seed=seed, budget_factor=0.3)
                results.append(compare(f"seed{seed}_M{M}", H, Q_arr, L, P, noise_power))

    print("\n=== SUMMARY ===")
    print(
        f"{'name':16s} {'M':4s} {'method match':14s} {'|G| rel':10s} {'p_abs':10s} {'np ms':8s} {'jax ms':8s} {'speedup':8s}"
    )
    for r in results:
        print(
            f"{r['name']:16s} {r['M']:<4d} {str(r['method_match']):14s} {r['dG']:10.2e} {r['dp']:10.2e} "
            f"{r['t_np_ms']:8.1f} {r['t_jax_ms']:8.1f} {r['t_np_ms'] / r['t_jax_ms']:8.1f}x"
        )
