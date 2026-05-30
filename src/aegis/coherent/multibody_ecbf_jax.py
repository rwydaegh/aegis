"""GPU-accelerated multi-body ECBF inner solver via JAX.

This is a backend-equivalent drop-in for ``solve_multibody_ecbf`` that
moves the Newton-step compute kernels onto the GPU via ``jax.jit`` +
``jax.vmap``. The Newton scaffolding (active set, line search, fallback
detection) stays in NumPy; only the dense matrix work moves to device.

Why: at ``M = 256``, the FD Jacobian step does ``B`` dense
``M x M`` solves per Newton iteration. On CPU these are sequential
(~10 ms each, ~500 ms / iter at ``B = 50``). Under ``jax.vmap`` on a
4090 they fan out concurrently and run in ~13 ms total — roughly 70x
speedup on the dominant cost. Validated by
``JSAC/code/experiments/plaza_run/profile_jax_kernels.py``.

The accuracy vs the NumPy reference is at machine precision
(``|dp|_inf <= 7e-17`` per ``profile_jax_kernels``); the two solvers
should produce bit-equivalent results modulo eigh ordering.

Public entry: :func:`solve_multibody_ecbf_jax` with the same signature
shape as the NumPy reference (minus the lowrank kwargs — JAX path always
runs lowrank with a fixed rank baked in for jit compilation).
"""

from __future__ import annotations

import warnings
from functools import partial

import jax
import jax.numpy as jnp
import numpy as np

from aegis.coherent.multibody_ecbf import MultibodyECBFDiagnostics, _mrt, _per_body_abs
from aegis.defaults import NUMERICAL_FLOOR

# JAX double precision is required: the Newton sweep is sensitive to numerical
# error, and the dual lambdas can span 6+ orders of magnitude.
jax.config.update("jax_enable_x64", True)


# ----------------------------------------------------------------------
# JAX kernels
# ----------------------------------------------------------------------
@partial(jax.jit, static_argnames=("rank",))
def _decompose_lowrank_jax(Q_arr: jax.Array, rank: int):
    """Top-`rank` Hermitian eigendecomposition (B, M, M) -> (U, D) descending.

    JAX's ``jnp.linalg.eigh`` returns ascending eigenpairs; we take the
    last `rank` columns and reverse to get the dominant eigenpairs in
    descending order.
    """
    Q_h = 0.5 * (Q_arr + Q_arr.conj().transpose(0, 2, 1))
    evals, evecs = jnp.linalg.eigh(Q_h)
    # Top-r descending: take the last r entries and reverse.
    D = jnp.maximum(evals[:, -rank:][:, ::-1], 0.0)
    U = evecs[:, :, -rank:][:, :, ::-1]
    return U, D


def _step_kernel_jax_impl(lambdas, U_arr, D_arr, base_mat, I_scale, H_conj, P):
    """One inner step: build M_lam from lowrank V V^H, solve, eval p_abs.

    No active-set masking: ``lambdas[u] = 0`` zeros that body's
    contribution naturally, so the dense over-B form is correct and is
    what we want for jit (no dynamic slicing).
    """
    M = U_arr.shape[1]
    weights = jnp.sqrt(jnp.maximum(lambdas[:, None], 0.0) * D_arr)  # (B, r)
    V_blocks = U_arr * weights[:, None, :]  # (B, M, r)
    # Reshape to (M, B * r) so the rank update V @ V^H is one GEMM.
    V = V_blocks.transpose(1, 0, 2).reshape(M, -1)
    M_lam = base_mat + I_scale * jnp.eye(M, dtype=jnp.complex128) + V @ V.conj().T
    W_raw = jnp.linalg.solve(M_lam, H_conj)
    frob = jnp.linalg.norm(W_raw, ord="fro")
    W = jnp.sqrt(P) * W_raw / jnp.maximum(frob, NUMERICAL_FLOOR)
    V_w = jnp.einsum("bir,ik->brk", U_arr.conj(), W)
    abs2 = V_w.real**2 + V_w.imag**2
    p_abs = jnp.einsum("br,brk->b", D_arr, abs2)
    return W, p_abs


_step_kernel_jax = jax.jit(_step_kernel_jax_impl)


def _fd_jacobian_jax_impl(lambdas, h_vec, U_arr, D_arr, base_mat, I_scale, H_conj, P):
    """FD Jacobian of p_abs wrt lambda, vmapped over the perturbation index.

    Returns the (B, B) array ``p_abs_cols[v, u] = p_abs_u(lambda + h_v e_v)``.
    The caller subtracts the unperturbed ``p_abs(lambda)``, divides by
    ``h_vec[v]``, and slices to the active set.
    """
    B = lambdas.shape[0]

    def one_col(v_idx):
        lam_p = lambdas.at[v_idx].add(h_vec[v_idx])
        _, p_abs_p = _step_kernel_jax_impl(lam_p, U_arr, D_arr, base_mat, I_scale, H_conj, P)
        return p_abs_p

    return jax.vmap(one_col)(jnp.arange(B))


_fd_jacobian_jax = jax.jit(_fd_jacobian_jax_impl)


@partial(jax.jit, static_argnames=("K",))
def _min_absorption_jax(Q_arr, P, K: int):
    """Smallest-eigenvalue eigenvector of sum_u Q^{(u)}, replicated K-wise.

    Output ``W`` has rank-1 structure (every column = the same direction
    scaled by ``sqrt(P/K)``). This is the min-absorption fallback used
    when the body-aware Newton sweep fails to satisfy budgets. ``K`` is a
    static arg so that ``jnp.tile`` can use it as a shape parameter.
    """
    Q_sum = jnp.sum(Q_arr, axis=0)
    Q_sum = 0.5 * (Q_sum + Q_sum.conj().T)
    _, V = jnp.linalg.eigh(Q_sum)
    direction = V[:, 0]
    return jnp.tile(direction[:, None], (1, K)) * jnp.sqrt(P / K)


# ----------------------------------------------------------------------
# Solver entry point
# ----------------------------------------------------------------------
def solve_multibody_ecbf_jax(
    H: np.ndarray,
    Q_list,
    L_list,
    P: float,
    *,
    noise_power: float | None = None,
    max_outer: int = 30,
    tol: float = 1e-9,
    return_diagnostics: bool = False,
    lambda_init: np.ndarray | None = None,
    lowrank_rank: int = 3,
):
    """Same algorithm as ``solve_multibody_ecbf`` with JAX kernels.

    The lowrank rank is fixed at ``lowrank_rank`` (default 3) — the JAX
    kernel jit'd shapes need a static rank. The plaza-run Q's are rank
    3 to numerical precision so the truncation is exact.

    Returns
    -------
    W : (M, K) numpy complex
    diagnostics : MultibodyECBFDiagnostics, optional
    """
    H = np.asarray(H, dtype=complex)
    if H.ndim == 1:
        H = H.reshape(1, -1)
    K, M = H.shape
    if P <= 0:
        raise ValueError(f"Transmit power P must be positive, got {P}")
    if noise_power is not None and noise_power <= 0:
        raise ValueError(f"noise_power must be positive when provided, got {noise_power}")

    # Stack Q_list -> (B, M, M).
    if isinstance(Q_list, np.ndarray) and Q_list.ndim == 3:
        Q_arr = np.ascontiguousarray(Q_list, dtype=complex)
    else:
        Q_arr = np.stack([np.asarray(Q, dtype=complex) for Q in Q_list], axis=0)
    B = Q_arr.shape[0]
    if Q_arr.shape != (B, M, M):
        raise ValueError(f"Each Q^(u) must be ({M}, {M}); got stacked shape {Q_arr.shape}")

    L_arr = np.asarray(L_list, dtype=float)
    if L_arr.shape != (B,):
        raise ValueError(f"L_list shape {L_arr.shape} != (B={B},)")

    # MRT trial on host (one-shot, easy).
    W_mrt = _mrt(H, P)
    p_abs_mrt = _per_body_abs(W_mrt, Q_arr)
    if np.all(p_abs_mrt <= L_arr * (1.0 + tol)):
        diag = MultibodyECBFDiagnostics(
            lambdas=np.zeros(B),
            p_abs=p_abs_mrt,
            L=L_arr,
            method="mrt-feasible",
            converged=True,
            n_outer=0,
            n_active=0,
            residual=float(np.max(np.maximum(0.0, p_abs_mrt - L_arr) / L_arr, initial=0.0)),
        )
        return (W_mrt, diag) if return_diagnostics else W_mrt

    # MRT infeasible: enter Newton on the dual. Push to device.
    Q_dev = jnp.asarray(Q_arr)
    H_conj_dev = jnp.asarray(H.conj().T)
    if noise_power is None:
        base_mat_dev = jnp.zeros((M, M), dtype=jnp.complex128)
        I_scale = 1.0
    else:
        base_mat_dev = jnp.asarray(H.conj().T @ H)
        I_scale = float(noise_power)

    # Lowrank decomposition on device.
    U_dev, D_dev = _decompose_lowrank_jax(Q_dev, int(lowrank_rank))

    if lambda_init is None:
        lambdas = np.zeros(B)
    else:
        lambdas = np.asarray(lambda_init, dtype=float).copy()
        if lambdas.shape != (B,):
            raise ValueError(f"lambda_init shape {lambdas.shape} != (B={B},)")
        np.maximum(lambdas, 0.0, out=lambdas)

    converged = False
    n_outer = 0
    fd_step = 1e-5

    for outer_iter in range(max_outer):
        n_outer = outer_iter + 1
        lam_dev = jnp.asarray(lambdas)
        W_dev, p_abs_dev = _step_kernel_jax(lam_dev, U_dev, D_dev, base_mat_dev, I_scale, H_conj_dev, P)
        p_abs = np.asarray(p_abs_dev)
        gap = p_abs - L_arr
        rel_viol = np.max(np.maximum(0.0, gap) / L_arr, initial=0.0)
        if rel_viol < tol:
            converged = True
            break

        active = (gap > 0) | (lambdas > 0)
        idx = np.where(active)[0]
        if idx.size == 0:
            converged = True
            break

        h = fd_step * np.maximum(np.abs(lambdas), 1.0)
        # vmap over all B columns; slice the active subset on host.
        h_dev = jnp.asarray(h)
        p_cols_dev = _fd_jacobian_jax(lam_dev, h_dev, U_dev, D_dev, base_mat_dev, I_scale, H_conj_dev, P)
        p_cols = np.asarray(p_cols_dev)
        # J[u, v] = (p_abs_cols[v, u] - p_abs[u]) / h[v] for u, v in active.
        J = (p_cols[idx][:, idx] - p_abs[idx][None, :]).T / h[idx][None, :]
        gap_active = gap[idx]

        try:
            delta = np.linalg.solve(-J + 1e-12 * np.eye(idx.size), gap_active)
        except np.linalg.LinAlgError:
            delta = gap_active.copy()

        max_decrease = lambdas[idx]
        step_scale = 1.0
        too_negative = (delta < -max_decrease) & (max_decrease > 0)
        if np.any(too_negative):
            ratios = -max_decrease[too_negative] / delta[too_negative]
            step_scale = float(min(1.0, ratios.min() * 0.99))
        new_lambdas = lambdas.copy()
        new_lambdas[idx] = np.maximum(0.0, lambdas[idx] + step_scale * delta)
        denom = np.maximum(np.abs(lambdas), 1.0)
        rel_change = float(np.max(np.abs(new_lambdas - lambdas) / denom, initial=0.0))
        lambdas = new_lambdas
        if rel_change < tol and rel_viol < 10 * tol:
            converged = True
            break

    # Final precoder.
    lam_dev = jnp.asarray(lambdas)
    W_dev, _p_abs_dev_lr = _step_kernel_jax(lam_dev, U_dev, D_dev, base_mat_dev, I_scale, H_conj_dev, P)
    W = np.asarray(W_dev)
    # Always evaluate against the FULL-rank Q for honest residual reporting
    # and primal-projection scale, mirroring the NumPy multibody_ecbf path.
    # Project exactly to L (no extra cushion): p_abs_full is the exact
    # absorbed power under the full operator, so the exact projection alone
    # guarantees feasibility. A deliberate regulatory margin, if wanted,
    # belongs at the call site as L_target < L, not as a hidden constant.
    p_abs_full = _per_body_abs(W, Q_arr)
    margin = L_arr / np.maximum(p_abs_full, 1e-30)
    scale = float(np.sqrt(max(0.0, min(1.0, margin.min()))))
    method = "multibody-ecbf"
    converged_final = converged
    if scale < 1.0 - 1e-9:
        if scale > 1e-3:
            W = W * scale
            p_abs_full = _per_body_abs(W, Q_arr)
            method = "multibody-ecbf-projected"
            converged_final = True
        else:
            warnings.warn(
                f"Multi-body ECBF (jax): dual blow-up after {n_outer} sweeps; "
                f"projection scale {scale:.3e} too small. "
                "Falling back to min-absorption direction.",
                stacklevel=2,
            )
            W_fb_dev = _min_absorption_jax(Q_dev, P, int(K))
            W = np.asarray(W_fb_dev)
            p_abs_full = _per_body_abs(W, Q_arr)
            method = "min-absorption"
            converged_final = False
    residual = float(np.max(np.maximum(0.0, p_abs_full - L_arr) / L_arr, initial=0.0))
    diag = MultibodyECBFDiagnostics(
        lambdas=lambdas,
        p_abs=p_abs_full,
        L=L_arr,
        method=method,
        converged=converged_final,
        n_outer=n_outer,
        n_active=int(np.count_nonzero(lambdas > 0)),
        residual=residual,
    )
    return (W, diag) if return_diagnostics else W
