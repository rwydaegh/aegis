"""GPU-accelerated UE-anchored Kirchhoff render.

Drop-in equivalent of `kirchhoff.kirchhoff_h_body`, but with the per-path
Python loop replaced by vectorised jnp ops and a `jax.jit` wrap. Runs on
GPU when JAX is configured for CUDA.

Numerical agreement against the NumPy reference is enforced by
`tests/test_kirchhoff_jax_parity.py` to relative error <= 1e-5.
"""
from __future__ import annotations

import os
import numpy as np
import jax
import jax.numpy as jnp
from functools import partial

# JAX defaults to float32. We need float64 for phase accumulation across
# many wavelengths (mmWave + ~50 m baselines = O(10^4) phase rotations).
jax.config.update("jax_enable_x64", True)

C0 = 2.99792458e8
EPS_0 = 8.8541878128e-12


def _n_complex_jax(eps_r: float, sigma: float, freq_hz: float) -> complex:
    """Same as aegis.tissue.fresnel.n_complex, returns Python complex."""
    omega = 2.0 * np.pi * freq_hz
    eps_complex = eps_r - 1j * sigma / (omega * EPS_0)
    n_tilde = np.sqrt(eps_complex)
    if np.real(n_tilde) < 0:
        n_tilde = -n_tilde
    return complex(n_tilde)


@partial(jax.jit, static_argnames=("M",))
def _h_body_kernel(
    centroids: jnp.ndarray,    # (T, 3) float64  -- phone-visible triangles
    normals: jnp.ndarray,      # (T, 3) float64
    areas: jnp.ndarray,        # (T,)   float64
    r_phone: jnp.ndarray,      # (3,)   float64
    k_hat: jnp.ndarray,        # (P, 3) float64
    psi: jnp.ndarray,          # (P, 3) complex
    amp: jnp.ndarray,          # (P,)   complex
    j_idx: jnp.ndarray,        # (P,)   int32 in [0, M)
    n_tilde: jnp.ndarray,      # () complex
    k0: float,
    M: int,
) -> jnp.ndarray:
    """Compute h_body[j] in C^M as a fully vectorised, JIT-able kernel.

    Mirrors kirchhoff_h_body but the per-path loop becomes a (P, T) tensor
    contraction. h_body[j] = sum over (n, t) of contrib[n, t] * 1{j(n)=j}.
    """
    # ---- per-triangle phone-side geometry ---------------------------------
    delta = r_phone[None, :] - centroids                        # (T, 3)
    R = jnp.linalg.norm(delta, axis=1)                          # (T,)
    eta_hat = delta / jnp.maximum(R[:, None], 1e-12)            # (T, 3)
    green = jnp.exp(1j * k0 * R) / (4.0 * jnp.pi * jnp.maximum(R, 1e-9))  # (T,)

    # ---- per-(path, triangle) BS-side angle and lit gate ------------------
    # mu[n, t] = -k_hat[n] . normals[t]
    mu = -jnp.einsum("nj,tj->nt", k_hat, normals)               # (P, T) float
    lit = mu > 1e-3                                              # (P, T) bool

    # ---- pseudo-Brewster reflection r0 = (r_s + r_p) / 2 ------------------
    # Replace masked entries with mu=1 to keep sqrt/division finite, then mask.
    mu_c = jnp.where(lit, mu, 1.0).astype(jnp.complex128)
    n2 = n_tilde * n_tilde
    xi = jnp.sqrt(n2 - 1.0 + mu_c * mu_c)
    xi = jnp.where(jnp.real(xi) < 0, -xi, xi)
    r_s = (mu_c - xi) / (mu_c + xi)
    r_p = (n2 * mu_c - xi) / (n2 * mu_c + xi)
    r0 = 0.5 * (r_s + r_p)                                       # (P, T) complex

    # ---- polarization projection (I - eta eta^T) psi ----------------------
    # psi_eta[n, t, :] = psi[n, :] - eta_hat[t, :] * (psi[n, :] . eta_hat[t, :])
    psi_dot_eta = jnp.einsum("nj,tj->nt", psi, eta_hat.astype(psi.dtype))  # (P, T) complex
    # Take only the z-component (vertical-pol UE pickup); avoids materialising (P,T,3).
    g_UE_proj = psi[:, 2:3] - eta_hat[None, :, 2] * psi_dot_eta  # (P, T) complex

    # ---- incident phase factor exp(-i k0 k . r) ---------------------------
    phase_inc = jnp.exp(
        -1j * k0 * jnp.einsum("nj,tj->nt", k_hat, centroids)
    )                                                             # (P, T) complex

    # ---- assembly ---------------------------------------------------------
    K = 1j * k0 * r0                                              # (P, T)
    contrib = (
        amp[:, None]
        * K
        * g_UE_proj
        * green[None, :]
        * phase_inc
        * areas[None, :]
    )                                                             # (P, T)
    contrib = jnp.where(lit, contrib, 0.0 + 0.0j)

    # ---- scatter-add over BS element index --------------------------------
    # Sum over triangles first to get per-path element contribution
    per_path = contrib.sum(axis=1)                                # (P,) complex
    h = jnp.zeros(M, dtype=jnp.complex128)
    h = h.at[j_idx].add(per_path)                                 # (M,) complex
    return h


def kirchhoff_h_body_jax(
    body,
    paths,
    r_phone: np.ndarray,
    *,
    f_c: float = 28e9,
    M: int = 64,
    eps_r: float = 16.5,
    sigma: float = 25.8,
    bs_visible_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Drop-in for `kirchhoff.kirchhoff_h_body`. Returns h_body (M,) complex.

    Reads the same Body and BSPathDict objects, runs the JAX-jit kernel on
    GPU when available, and converts the result back to NumPy.
    """
    # Phone-side visibility (CPU; uses trimesh BVH or facing test).
    vis = body.visible_from(np.asarray(r_phone, dtype=np.float64))
    if not np.any(vis):
        return np.zeros(M, dtype=np.complex128)
    tri_idx = np.where(vis)[0]
    if bs_visible_mask is not None:
        tri_idx = tri_idx[bs_visible_mask[tri_idx]]
        if len(tri_idx) == 0:
            return np.zeros(M, dtype=np.complex128)

    centroids = jnp.asarray(body.centroids[tri_idx], dtype=jnp.float64)
    normals   = jnp.asarray(body.normals[tri_idx],   dtype=jnp.float64)
    areas     = jnp.asarray(body.areas[tri_idx],     dtype=jnp.float64)

    k_hat_j = jnp.asarray(paths.k_hat, dtype=jnp.float64)
    psi_j   = jnp.asarray(paths.psi,   dtype=jnp.complex128)
    amp_j   = jnp.asarray(paths.amp,   dtype=jnp.complex128)
    j_idx_j = jnp.asarray(paths.j_idx, dtype=jnp.int32)

    n_tilde = _n_complex_jax(eps_r, sigma, f_c)
    k0 = 2.0 * np.pi * f_c / C0

    h = _h_body_kernel(
        centroids, normals, areas,
        jnp.asarray(r_phone, dtype=jnp.float64),
        k_hat_j, psi_j, amp_j, j_idx_j,
        jnp.asarray(n_tilde, dtype=jnp.complex128),
        float(k0), int(M),
    )
    return np.asarray(h)
