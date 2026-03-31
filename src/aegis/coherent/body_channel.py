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

from aegis._array_backend import xp
from aegis.coherent._accumulate import accumulate_by_element
from aegis.coherent.fresnel_operator import (
    apply_fresnel_operator,
    compute_fresnel_operator,
)
from aegis.constants import C_0
from aegis.defaults import NUMERICAL_FLOOR
from aegis.tissue.fresnel import xi_from_mu


def compute_body_channel(
    normals,
    centroids,
    k_hat,
    psi,
    element_index,
    n_tilde,
    sigma,
    freq_hz,
    n_elements,
):
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

    # Validate element_index bounds to prevent silent data loss
    element_index = np.asarray(element_index)
    if element_index.size > 0:
        idx_min, idx_max = int(element_index.min()), int(element_index.max())
        if idx_min < 0 or idx_max >= n_elements:
            raise ValueError(f"element_index values must be in [0, {n_elements}), got range [{idx_min}, {idx_max}]")

    k0 = 2 * xp.pi * freq_hz / C_0

    # Fresnel operator components
    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, k_hat, n_tilde)

    # F_n(r) @ psi_n for each (m, n): shape (M, N, 3)
    F_psi = apply_fresnel_operator(psi, t_s, t_p, e_s, e_p)

    # Depth coupling weight: sqrt(sigma / (4 * alpha_n))
    # alpha_n is the amplitude decay rate: k0*xi = beta - i*alpha, so alpha = -Im(k0*xi)
    # xi depends on incidence angle, so alpha varies per (m, n) pair
    xi = xi_from_mu(xp.asarray(mu).ravel(), n_tilde).reshape(mu.shape)
    k0_xi = k0 * xi
    alpha = -xp.imag(k0_xi)  # (M, N), amplitude decay rate [1/m]
    alpha = xp.maximum(alpha, NUMERICAL_FLOOR)  # avoid division by zero

    depth_weight = xp.sqrt(sigma / (4 * alpha))  # (M, N)

    # Phase: exp(-i*k0 * k_hat_n . r_m)
    phase_arg = -k0 * (centroids @ k_hat.T)  # (M, N)
    phase = xp.exp(1j * phase_arg)

    # Weighted contribution per (m, n):
    # w_{m,n} = depth_weight * F_psi * phase
    weighted = depth_weight[:, :, None] * F_psi * phase[:, :, None]
    # weighted: (M, N, 3) complex

    # Accumulate by element
    return accumulate_by_element(weighted, element_index, M, n_elements)
