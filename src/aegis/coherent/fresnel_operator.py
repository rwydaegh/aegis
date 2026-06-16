"""Fresnel transmission operator F_n(r) for coherent dosimetry.

Each path n at each surface point r has a rank-2 operator that projects the
incident polarisation-amplitude vector onto TE/TM components and scales by
the complex Fresnel transmission coefficients t_s, t_p.

    F_n(r) = t_s * e_s @ e_s^T + t_p * e_p @ e_p^T     (front-facing)
    F_n(r) = 0                                            (back-facing)

Monograph: Definition in sec:fresnel-operator, Approximation 1 applied.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import JAX_AVAILABLE, xp
from aegis.tissue.fresnel import _fresnel_core


def te_tm_basis(
    k_hat: NDArray[np.floating],
    normals: NDArray[np.floating],
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Compute TE and TM basis vectors for each (path, triangle) pair.

    Parameters
    ----------
    k_hat : (N, 3)
        Unit directions of arrival.
    normals : (M, 3)
        Unit outward normals per triangle.

    Returns
    -------
    e_s : (M, N, 3)
        TE (s-polarisation) unit vectors.
    e_p : (M, N, 3)
        TM (p-polarisation) unit vectors.
    """
    M = normals.shape[0]
    N = k_hat.shape[0]

    # e_s = k_hat x n / |k_hat x n|  for each (m, n) pair
    # normals: (M, 1, 3), k_hat: (1, N, 3) -> cross: (M, N, 3)
    cross = xp.cross(k_hat[None, :, :], normals[:, None, :])
    cross_norm = xp.linalg.norm(cross, axis=2, keepdims=True)

    # At normal incidence (k_hat parallel to n), cross product is zero.
    # Use an arbitrary perpendicular direction as fallback.
    abs_k = xp.abs(k_hat)
    min_ax = xp.argmin(abs_k, axis=1)
    if JAX_AVAILABLE:
        ref = xp.zeros((N, 3))
        ref = ref.at[xp.arange(N), min_ax].set(1.0)
    else:
        ref = _set_ref_numpy(N, min_ax)
    fb = xp.cross(k_hat, ref)
    fb_norm = xp.linalg.norm(fb, axis=1, keepdims=True)
    fb = fb / xp.where(fb_norm > 0, fb_norm, 1.0)
    fallback = fb[None, :, :]

    small = cross_norm < 1e-12
    e_s = xp.where(small, xp.broadcast_to(fallback, (M, N, 3)), cross)
    e_s_norm = xp.linalg.norm(e_s, axis=2, keepdims=True)
    e_s = e_s / xp.where(e_s_norm > 0, e_s_norm, 1.0)

    # e_p = e_s x k_hat (incident TM direction, Approximation 1)
    e_p = xp.cross(e_s, k_hat[None, :, :])
    e_p_norm = xp.linalg.norm(e_p, axis=2, keepdims=True)
    e_p = e_p / xp.where(e_p_norm > 0, e_p_norm, 1.0)

    return e_s, e_p


def _set_ref_numpy(N, min_ax):
    """NumPy fallback for building reference vectors."""
    ref = np.zeros((N, 3))
    ref[np.arange(N), min_ax] = 1.0
    return ref


def fresnel_coeffs_from_mu(mu, n_tilde):
    """TE/TM transmission amplitudes from a precomputed incidence cosine.

    The frequency- and tissue-dependent half of :func:`compute_fresnel_operator`:
    given ``mu = n_hat . (-k_hat)`` (pure geometry, freq-invariant) and the
    complex refractive index ``n_tilde``, returns the gated ``(t_s, t_p)``. Split
    out so a multi-frequency sweep over fixed geometry can reuse ``mu`` (and the
    TE/TM basis) and recompute only this part per frequency.

    Returns ``(t_s, t_p)`` each shaped like ``mu``, zero for back-facing paths.
    """
    # _fresnel_core is element-wise; pass (M, N) directly, no ravel needed
    mu_complex = xp.asarray(mu, dtype=complex)
    _, _, _, _, t_s_out, t_p_out = _fresnel_core(mu_complex, n_tilde)

    # Heaviside gate: zero for back-facing paths
    mask = mu > 0
    t_s_out = xp.where(mask, t_s_out, 0.0 + 0j)
    t_p_out = xp.where(mask, t_p_out, 0.0 + 0j)
    return t_s_out, t_p_out


def compute_fresnel_operator(
    normals,
    k_hat,
    n_tilde,
):
    """Compute Fresnel operator components for each (triangle, path) pair.

    Returns the ingredients needed to build F_n(r) * psi_n for each pair.

    Parameters
    ----------
    normals : (M, 3)
        Unit outward normals.
    k_hat : (N, 3)
        Unit directions of arrival.
    n_tilde : complex
        Complex refractive index.

    Returns
    -------
    mu : (M, N)
        Incidence cosine n_hat . (-k_hat). Negative for back-facing.
    t_s : (M, N)
        Complex TE transmission amplitude. Zero where mu <= 0.
    t_p : (M, N)
        Complex TM transmission amplitude. Zero where mu <= 0.
    e_s : (M, N, 3)
        TE basis vectors.
    e_p : (M, N, 3)
        TM basis vectors.
    """
    # mu = n_hat . (-k_hat), shape (M, N)
    mu = normals @ (-k_hat).T

    # Fresnel amplitude coefficients (vectorised over all M*N pairs)
    t_s_out, t_p_out = fresnel_coeffs_from_mu(mu, n_tilde)

    # TE/TM basis vectors
    e_s, e_p = te_tm_basis(k_hat, normals)

    return mu, t_s_out, t_p_out, e_s, e_p


def apply_fresnel_operator(
    psi,
    t_s,
    t_p,
    e_s,
    e_p,
):
    """Apply Fresnel operator: F_n(r) @ psi_n for each (triangle, path) pair.

    F_n @ psi = t_s * (e_s . psi) * e_s + t_p * (e_p . psi) * e_p

    Parameters
    ----------
    psi : (N, 3)
        Complex polarisation-amplitude vectors.
    t_s : (M, N)
        TE amplitude coefficients.
    t_p : (M, N)
        TM amplitude coefficients.
    e_s : (M, N, 3)
        TE basis vectors.
    e_p : (M, N, 3)
        TM basis vectors.

    Returns
    -------
    F_psi : (M, N, 3)
        Fresnel-transmitted field component per (triangle, path).
    """
    # psi_s = e_s . psi, psi_p = e_p . psi  (scalar projections)
    # einsum avoids creating (M, N, 3) broadcast intermediate
    psi_s = xp.einsum("mnj,nj->mn", e_s, psi)  # (M, N)
    psi_p = xp.einsum("mnj,nj->mn", e_p, psi)  # (M, N)

    # F @ psi = t_s * psi_s * e_s + t_p * psi_p * e_p
    F_psi = (t_s * psi_s)[:, :, None] * e_s + (t_p * psi_p)[:, :, None] * e_p

    return F_psi
