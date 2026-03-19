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

from aegis.tissue.fresnel import fresnel_amplitude


def te_tm_basis(
    k_hat: np.ndarray,
    normals: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
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
    cross = np.cross(k_hat[np.newaxis, :, :], normals[:, np.newaxis, :])
    cross_norm = np.linalg.norm(cross, axis=2, keepdims=True)

    # At normal incidence (k_hat parallel to n), cross product is zero.
    # Use an arbitrary perpendicular direction as fallback.
    small = cross_norm < 1e-12
    # Fallback: pick axis least aligned with k_hat
    fallback = np.zeros((1, N, 3))
    abs_k = np.abs(k_hat)
    min_ax = np.argmin(abs_k, axis=1)
    for i in range(N):
        ref = np.zeros(3)
        ref[min_ax[i]] = 1.0
        fb = np.cross(k_hat[i], ref)
        fb_norm = np.linalg.norm(fb)
        if fb_norm > 0:
            fb /= fb_norm
        fallback[0, i, :] = fb

    e_s = np.where(small, np.broadcast_to(fallback, (M, N, 3)), cross)
    e_s_norm = np.linalg.norm(e_s, axis=2, keepdims=True)
    e_s = e_s / np.where(e_s_norm > 0, e_s_norm, 1.0)

    # e_p = e_s x k_hat (incident TM direction, Approximation 1)
    e_p = np.cross(e_s, k_hat[np.newaxis, :, :])
    e_p_norm = np.linalg.norm(e_p, axis=2, keepdims=True)
    e_p = e_p / np.where(e_p_norm > 0, e_p_norm, 1.0)

    return e_s, e_p


def compute_fresnel_operator(
    normals: np.ndarray,
    k_hat: np.ndarray,
    n_tilde: complex,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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
    mu_flat = mu.ravel()
    t_s_flat, t_p_flat = fresnel_amplitude(mu_flat, n_tilde)
    t_s_out = t_s_flat.reshape(mu.shape)
    t_p_out = t_p_flat.reshape(mu.shape)

    # Heaviside gate: zero for back-facing paths
    mask = mu > 0
    t_s_out = np.where(mask, t_s_out, 0.0)
    t_p_out = np.where(mask, t_p_out, 0.0)

    # TE/TM basis vectors
    e_s, e_p = te_tm_basis(k_hat, normals)

    return mu, t_s_out, t_p_out, e_s, e_p


def apply_fresnel_operator(
    psi: np.ndarray,
    t_s: np.ndarray,
    t_p: np.ndarray,
    e_s: np.ndarray,
    e_p: np.ndarray,
) -> np.ndarray:
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
    # psi: (1, N, 3), e_s: (M, N, 3) -> dot over axis 2
    psi_s = np.sum(e_s * psi[np.newaxis, :, :], axis=2)  # (M, N)
    psi_p = np.sum(e_p * psi[np.newaxis, :, :], axis=2)  # (M, N)

    # F @ psi = t_s * psi_s * e_s + t_p * psi_p * e_p
    F_psi = (t_s * psi_s)[:, :, np.newaxis] * e_s + (t_p * psi_p)[:, :, np.newaxis] * e_p

    return F_psi
