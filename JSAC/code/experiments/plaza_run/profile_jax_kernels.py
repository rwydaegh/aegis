"""Microbench: JAX vs numpy for the ECBF inner-step + FD Jacobian kernel.

The solver's hot path at M=256 is ~50 dense complex 256x256 solves per
Newton iteration (one per active body, FD column). On CPU these are
sequential (~10 ms each = 500 ms/iter). On GPU under jax.vmap they should
run concurrently bound only by VRAM bandwidth.

This script measures:
  - Single inner step (build M_lam from lowrank V V^H, solve, eval p_abs)
  - FD Jacobian batch (B perturbations, vmapped)
  - Full Newton-style sweep (8 outer * (1 trial + B FD cols))

against numpy reference. Goal: confirm >= 10x speedup at M=256 before
embarking on the full slot_loop integration.

Run: AEGIS_ARRAY_BACKEND=jax .venv/bin/python -m JSAC.code.experiments.plaza_run.profile_jax_kernels
"""

from __future__ import annotations

import os
import time

# Force jax x64 before importing.
os.environ.setdefault("JAX_ENABLE_X64", "1")

import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402
import numpy as np  # noqa: E402

print("jax devices:", jax.devices(), "backend:", jax.default_backend())


# ------------------------------------------------------------------
# Synthetic problem
# ------------------------------------------------------------------
def make_problem(B: int = 50, M: int = 256, K: int = 25, r: int = 3, seed: int = 0):
    rng = np.random.default_rng(seed)
    # Each body's Q is a true rank-r PSD. U random unitary cols, D random positive.
    U = rng.standard_normal((B, M, r)) + 1j * rng.standard_normal((B, M, r))
    # Orthogonalise per body (cheap; just for realism).
    for b in range(B):
        Q, _ = np.linalg.qr(U[b])
        U[b] = Q
    D = rng.uniform(0.01, 1.0, size=(B, r))
    H = (rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))) / np.sqrt(M)
    P = 1.0
    noise_power = 1e-2
    base_mat = H.conj().T @ H
    H_conj = H.conj().T
    return U, D, H_conj, base_mat, noise_power, P


# ------------------------------------------------------------------
# Numpy reference (taken from multibody_ecbf._solve_W_factored + _per_body_abs_lowrank)
# ------------------------------------------------------------------
def step_np(lambdas, U_arr, D_arr, base_mat, I_scale, H_conj, P):
    M = U_arr.shape[1]
    M_lam = base_mat + I_scale * np.eye(M, dtype=complex)
    active = lambdas > 0
    if np.any(active):
        idx = np.where(active)[0]
        weights = np.sqrt(lambdas[idx, None] * D_arr[idx])
        V_blocks = U_arr[idx] * weights[:, None, :]
        V = V_blocks.transpose(1, 0, 2).reshape(M, -1)
        M_lam = M_lam + V @ V.conj().T
    W_raw = np.linalg.solve(M_lam, H_conj)
    frob = np.linalg.norm(W_raw, "fro")
    W = np.sqrt(P) * W_raw / max(frob, 1e-30)
    V_w = np.einsum("bir,ik->brk", U_arr.conj(), W)
    abs2 = V_w.real**2 + V_w.imag**2
    p_abs = np.einsum("br,brk->b", D_arr, abs2)
    return W, p_abs


# ------------------------------------------------------------------
# JAX kernel (jit'd, no active-set masking; dense over B since lambdas[u]=0 just zeros the term)
# ------------------------------------------------------------------
def step_kernel_jax(lambdas, U_arr, D_arr, base_mat, I_scale, H_conj, P):
    M = U_arr.shape[1]
    # No active masking: lambdas[u] = 0 zeros the contribution naturally.
    weights = jnp.sqrt(jnp.maximum(lambdas[:, None], 0.0) * D_arr)  # (B, r)
    V_blocks = U_arr * weights[:, None, :]  # (B, M, r)
    V = V_blocks.transpose(1, 0, 2).reshape(M, -1)
    M_lam = base_mat + I_scale * jnp.eye(M, dtype=jnp.complex128) + V @ V.conj().T
    W_raw = jnp.linalg.solve(M_lam, H_conj)
    frob = jnp.linalg.norm(W_raw, ord="fro")
    W = jnp.sqrt(P) * W_raw / jnp.maximum(frob, 1e-30)
    V_w = jnp.einsum("bir,ik->brk", U_arr.conj(), W)
    abs2 = V_w.real**2 + V_w.imag**2
    p_abs = jnp.einsum("br,brk->b", D_arr, abs2)
    return W, p_abs


step_kernel_jax_jit = jax.jit(step_kernel_jax, static_argnames=("I_scale", "P"))


# ------------------------------------------------------------------
# FD Jacobian batch: for each body v, perturb lambda[v] += h, return p_abs
# vmap over body index.
# ------------------------------------------------------------------
def fd_jacobian_jax(lambdas, h_vec, U_arr, D_arr, base_mat, I_scale, H_conj, P):
    B = lambdas.shape[0]

    def one_col(v_idx):
        h = h_vec[v_idx]
        lam_p = lambdas.at[v_idx].add(h)
        _, p_abs_p = step_kernel_jax(lam_p, U_arr, D_arr, base_mat, I_scale, H_conj, P)
        return p_abs_p

    return jax.vmap(one_col)(jnp.arange(B))


fd_jacobian_jax_jit = jax.jit(fd_jacobian_jax, static_argnames=("I_scale", "P"))


# ------------------------------------------------------------------
# Numpy FD Jacobian (sequential)
# ------------------------------------------------------------------
def fd_jacobian_np(lambdas, h_vec, U_arr, D_arr, base_mat, I_scale, H_conj, P):
    B = lambdas.shape[0]
    p_abs_cols = np.zeros((B, B), dtype=float)
    for v in range(B):
        lam_p = lambdas.copy()
        lam_p[v] += h_vec[v]
        _, p_abs_p = step_np(lam_p, U_arr, D_arr, base_mat, I_scale, H_conj, P)
        p_abs_cols[v] = p_abs_p
    return p_abs_cols


# ------------------------------------------------------------------
# Bench
# ------------------------------------------------------------------
def bench(name, M):
    print(f"\n=== M={M} ===")
    U, D, H_conj, base_mat, noise_power, P = make_problem(M=M)
    B = U.shape[0]
    rng = np.random.default_rng(42)
    lambdas_np = rng.uniform(0, 0.5, size=B)
    h_vec_np = 1e-5 * np.maximum(np.abs(lambdas_np), 1.0)

    # Push to device.
    U_d = jnp.asarray(U)
    D_d = jnp.asarray(D)
    base_d = jnp.asarray(base_mat)
    H_conj_d = jnp.asarray(H_conj)
    lambdas_d = jnp.asarray(lambdas_np)
    h_vec_d = jnp.asarray(h_vec_np)

    # ---- Single step ----
    W_np, p_np = step_np(lambdas_np, U, D, base_mat, noise_power, H_conj, P)

    # Warm jit.
    W_j, p_j = step_kernel_jax_jit(lambdas_d, U_d, D_d, base_d, noise_power, H_conj_d, P)
    W_j.block_until_ready()

    # Compare numerics.
    W_jnp = np.asarray(W_j)
    p_jnp = np.asarray(p_j)
    print(
        f"  step accuracy: |dW|_F = {np.linalg.norm(W_np - W_jnp):.2e}, |dp|_inf = {np.max(np.abs(p_np - p_jnp)):.2e}"
    )

    # Time.
    n_iter = 50
    t0 = time.perf_counter()
    for _ in range(n_iter):
        W_np, p_np = step_np(lambdas_np, U, D, base_mat, noise_power, H_conj, P)
    t_np = (time.perf_counter() - t0) / n_iter * 1e3

    t0 = time.perf_counter()
    for _ in range(n_iter):
        W_j, p_j = step_kernel_jax_jit(lambdas_d, U_d, D_d, base_d, noise_power, H_conj_d, P)
        W_j.block_until_ready()
    t_jax = (time.perf_counter() - t0) / n_iter * 1e3
    print(f"  step:        np={t_np:.2f} ms, jax={t_jax:.2f} ms, speedup={t_np / t_jax:.1f}x")

    # ---- FD Jacobian (B columns) ----
    pcols_np = fd_jacobian_np(lambdas_np, h_vec_np, U, D, base_mat, noise_power, H_conj, P)
    pcols_j = fd_jacobian_jax_jit(lambdas_d, h_vec_d, U_d, D_d, base_d, noise_power, H_conj_d, P)
    pcols_j.block_until_ready()
    pcols_jnp = np.asarray(pcols_j)
    print(f"  fd accuracy: |dp_cols|_inf = {np.max(np.abs(pcols_np - pcols_jnp)):.2e}")

    n_iter_fd = 10
    t0 = time.perf_counter()
    for _ in range(n_iter_fd):
        _ = fd_jacobian_np(lambdas_np, h_vec_np, U, D, base_mat, noise_power, H_conj, P)
    t_np_fd = (time.perf_counter() - t0) / n_iter_fd * 1e3

    t0 = time.perf_counter()
    for _ in range(n_iter_fd):
        out = fd_jacobian_jax_jit(lambdas_d, h_vec_d, U_d, D_d, base_d, noise_power, H_conj_d, P)
        out.block_until_ready()
    t_jax_fd = (time.perf_counter() - t0) / n_iter_fd * 1e3
    print(f"  FD Jacobian (B={B} cols): np={t_np_fd:.1f} ms, jax={t_jax_fd:.1f} ms, speedup={t_np_fd / t_jax_fd:.1f}x")

    # Estimate per-slot solver cost:
    # 8 outer iters, each iter = 1 step + 1 FD batch.
    per_slot_np = 8 * (t_np + t_np_fd) * 2  # x2 for proposed + oracle calls
    per_slot_jax = 8 * (t_jax + t_jax_fd) * 2
    print(f"  estimated solver per-slot: np={per_slot_np:.0f} ms, jax={per_slot_jax:.0f} ms")
    return {"M": M, "step_np_ms": t_np, "step_jax_ms": t_jax, "fd_np_ms": t_np_fd, "fd_jax_ms": t_jax_fd}


if __name__ == "__main__":
    bench("M64", M=64)
    bench("M128", M=128)
    bench("M256", M=256)
