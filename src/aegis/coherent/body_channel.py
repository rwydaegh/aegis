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


def compute_body_channel_factored(
    normals,
    centroids,
    center_k_hat,
    center_psi,
    element_psi,
    element_index,
    n_tilde,
    sigma,
    freq_hz,
    n_elements,
):
    """Build G_tilde using factored Fresnel for array-expanded paths.

    When paths are expanded from N_center center paths to N_center*M_elements
    per-element paths (via expand_paths_to_array), the k_hat directions repeat
    across elements. This function computes the expensive Fresnel operator and
    depth coupling only for the N_center unique directions, then applies the
    per-element psi vectors. For a 4x4 UPA this is 16x less Fresnel work.

    Parameters
    ----------
    normals : (M, 3)
    centroids : (M, 3)
    center_k_hat : (N_center, 3)
        Unique propagation directions (before array expansion).
    center_psi : (N_center, 3)
        Center-path psi (before element gain/phase, used only for shape).
    element_psi : (N_total, 3)
        Per-element psi vectors from expand_paths_to_array.
    element_index : (N_total,)
        Element index for each expanded path.
    n_tilde, sigma, freq_hz, n_elements : same as compute_body_channel.

    Returns
    -------
    G_tilde : (M, 3, n_elements) complex
    """
    M = normals.shape[0]
    N_center = center_k_hat.shape[0]
    N_total = element_psi.shape[0]
    M_elem = N_total // N_center  # paths per center direction

    element_index = np.asarray(element_index)
    if element_index.size > 0:
        idx_min, idx_max = int(element_index.min()), int(element_index.max())
        if idx_min < 0 or idx_max >= n_elements:
            raise ValueError(f"element_index values must be in [0, {n_elements}), got range [{idx_min}, {idx_max}]")

    k0 = 2 * xp.pi * freq_hz / C_0

    # Compute Fresnel for N_center directions only (not N_total)
    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, center_k_hat, n_tilde)

    # Depth coupling per (M, N_center)
    xi = xi_from_mu(xp.asarray(mu).ravel(), n_tilde).reshape(mu.shape)
    k0_xi = k0 * xi
    alpha = -xp.imag(k0_xi)
    alpha = xp.maximum(alpha, NUMERICAL_FLOOR)
    depth_weight = xp.sqrt(sigma / (4 * alpha))  # (M, N_center)

    # Phase per (M, N_center)
    phase_arg = -k0 * (centroids @ center_k_hat.T)
    phase = xp.exp(1j * phase_arg)  # (M, N_center)

    # Precomputed scalar factor per (M, N_center)
    scalar = depth_weight * phase  # (M, N_center)

    # For each expanded path, apply F @ psi_n using precomputed Fresnel components
    # element_psi is laid out as [elem0_path0..N, elem1_path0..N, ...] (element-major)
    # so expanded path (j * N_center + c) maps to center path c
    G = xp.zeros((M, 3, n_elements), dtype=complex)

    for c in range(N_center):
        # Fresnel-filtered psi for each element at center direction c
        # t_s[:, c], t_p[:, c]: (M,) coefficients
        # e_s[:, c, :], e_p[:, c, :]: (M, 3) basis vectors
        # scalar[:, c]: (M,) combined depth*phase weight
        t_s_c = t_s[:, c]  # (M,)
        t_p_c = t_p[:, c]  # (M,)
        e_s_c = e_s[:, c, :]  # (M, 3)
        e_p_c = e_p[:, c, :]  # (M, 3)
        sc = scalar[:, c]  # (M,)

        # Gather all element psi vectors for this center direction
        # element_psi layout is element-major: elem j has indices [j*N_center : (j+1)*N_center]
        elem_psi_c = element_psi[c::N_center]  # (M_elem, 3) - psi for each element at direction c

        # Project each element's psi onto TE/TM basis
        # e_s_c: (M,3), elem_psi_c: (M_elem,3) -> dot products
        proj_s = xp.sum(e_s_c[None, :, :] * elem_psi_c[:, None, :], axis=2)  # (M_elem, M)
        proj_p = xp.sum(e_p_c[None, :, :] * elem_psi_c[:, None, :], axis=2)  # (M_elem, M)

        # F @ psi for each element: (M_elem, M, 3)
        F_psi_elems = (t_s_c[None, :] * proj_s)[:, :, None] * e_s_c[None, :, :] + (t_p_c[None, :] * proj_p)[
            :, :, None
        ] * e_p_c[None, :, :]  # (M_elem, M, 3)

        # Apply depth*phase weight and accumulate into G
        weighted_elems = sc[None, :, None] * F_psi_elems  # (M_elem, M, 3)

        # Each element's index for this center path
        elem_indices = element_index[c::N_center]  # (M_elem,)
        for j_local in range(M_elem):
            G[:, :, elem_indices[j_local]] += weighted_elems[j_local]

    return G
