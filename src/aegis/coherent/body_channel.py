"""Body-surface channel G_tilde(r) with Fresnel filtering and depth coupling.

G_tilde(r) = [g_tilde_1(r), ..., g_tilde_M(r)] in C^{3 x M_ant} where
g_tilde_j(r) = sum_{n: j(n)=j} sqrt(sigma/(4*alpha_n)) * F_n(r) @ psi_n * exp(-i*k0*k_hat_n.r)

S_ab(r) = ||G_tilde(r) @ x||^2  (Theorem 4.1, coherent absorption law)

Uses Approximation 2: depth coupling factors Gamma_{nn'} ~ 1 (error < 0.44%
for skin at 28 GHz), which allows the double sum to factor into a squared norm.

Monograph: eq:Gtilde-def, thm:coherent-law.
"""

from __future__ import annotations

import numpy as np

from aegis.coherent.fresnel_operator import (
    apply_fresnel_operator,
    compute_fresnel_operator,
)
from aegis.constants import C_0
from aegis.tissue.fresnel import xi_from_mu


def compute_body_channel(
    normals: np.ndarray,
    centroids: np.ndarray,
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    n_tilde: complex,
    sigma: float,
    freq_hz: float,
    n_elements: int,
) -> np.ndarray:
    """Build the body-surface channel G_tilde(r) at each triangle centroid.

    Parameters
    ----------
    normals : (M, 3)
        Unit outward normals.
    centroids : (M, 3)
        Triangle centroid positions [m].
    k_hat : (N, 3)
        Unit directions of arrival.
    psi : (N, 3)
        Complex polarisation-amplitude vectors.
    element_index : (N,)
        Antenna element index j(n) for each path.
    n_tilde : complex
        Complex refractive index of tissue.
    sigma : float
        Tissue conductivity [S/m].
    freq_hz : float
        Frequency [Hz].
    n_elements : int
        Total number of antenna elements M_ant.

    Returns
    -------
    G_tilde : (M_tri, 3, M_ant)
        Body-surface channel matrix at each triangle centroid.
    """
    M = normals.shape[0]
    k0 = 2 * np.pi * freq_hz / C_0

    # Fresnel operator components
    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, k_hat, n_tilde)

    # F_n(r) @ psi_n for each (m, n): shape (M, N, 3)
    F_psi = apply_fresnel_operator(psi, t_s, t_p, e_s, e_p)

    # Depth coupling weight: sqrt(sigma / (4 * alpha_n))
    # alpha_n is the amplitude decay rate: k0*xi = beta - i*alpha, so alpha = -Im(k0*xi)
    # xi depends on incidence angle, so alpha varies per (m, n) pair
    xi = xi_from_mu(mu.ravel(), n_tilde).reshape(mu.shape)
    k0_xi = k0 * xi
    alpha = -np.imag(k0_xi)  # (M, N), amplitude decay rate [1/m]
    alpha = np.maximum(alpha, 1e-30)  # avoid division by zero

    depth_weight = np.sqrt(sigma / (4 * alpha))  # (M, N)

    # Phase: exp(-i*k0 * k_hat_n . r_m)
    phase_arg = -k0 * (centroids @ k_hat.T)  # (M, N)
    phase = np.exp(1j * phase_arg)

    # Weighted contribution per (m, n):
    # w_{m,n} = depth_weight * F_psi * phase
    weighted = depth_weight[:, :, np.newaxis] * F_psi * phase[:, :, np.newaxis]
    # weighted: (M, N, 3) complex

    # Accumulate by element
    G_tilde = np.zeros((M, 3, n_elements), dtype=complex)
    for j in range(n_elements):
        mask = element_index == j
        if np.any(mask):
            G_tilde[:, :, j] = np.sum(weighted[:, mask, :], axis=1)

    return G_tilde
