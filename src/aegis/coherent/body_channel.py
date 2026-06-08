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


def _fock_gate_factors(mu, fock_R, freq_hz, q_F_s, q_F_h):
    """Polarization-resolved complex Fock gate factors ``(g_soft, g_hard)``.

    Builds the Fock detour parameter ``xi = m * theta`` from the incidence cosine
    ``mu`` (the value :func:`compute_fresnel_operator` already returns) and the
    in-incidence-plane radius ``fock_R``, then evaluates the complex uniform Fock
    gate separately for the soft (TE) and hard (TM) creeping constants. Deep lit
    both ``-> 1`` (the coherent field is unchanged, exact GO), with the penumbra
    rolloff and complex creeping tail near and past the terminator.

    ``fock_R`` is ``(M,)`` (per-triangle, broadcast across paths) or ``(M, N)``;
    ``q_F_s`` / ``q_F_h`` are scalar impedance parameters (``None`` for the PEC
    Fock gate). Returns two ``(M, N)`` complex arrays matching ``mu``.
    """
    # Lazy import: aegis.kernels.__init__ imports the coherent kernels (which
    # import this module), so a module-level import here is circular.
    from aegis.kernels.fock import fock_g, theta_from_mu

    R = xp.asarray(fock_R)
    if R.ndim == 1:
        R = R[:, None]  # (M, 1) -> broadcast across paths
    theta = theta_from_mu(mu)  # (M, N) signed terminator angle
    m = (xp.pi * freq_hz * R / C_0) ** (1.0 / 3.0)
    xi = m * theta  # (M, N) detour parameter
    g_soft = fock_g(xi, "soft", q_F_s)
    g_hard = fock_g(xi, "hard", q_F_h)
    return g_soft, g_hard


def _distal_amplitude(mu, clearance, R_occ, distal_d1, distal_d2, freq_hz, q_F_s, q_F_h):
    """Real distal-gate amplitude ``sqrt(G_d)`` per ``(M, N)``, 1.0 where ``mu <= 0``.

    The A3 coherent approximation (DECISIONS L9): the distal power gate ``G_d``
    attenuates the field amplitude by ``sqrt(G_d)`` on the lit response, leaving
    the plane-wave phase intact. Returns 1.0 on the back face so only the
    would-be-lit response is gated.
    """
    from aegis.kernels.fock import distal_gate

    g_d = distal_gate(
        clearance,
        R_occ,
        freq_hz,
        0.5,
        0.5,
        d1=distal_d1,
        d2=distal_d2,
        q_F_s=q_F_s,
        q_F_h=q_F_h,
        diffraction_model="fock",
    )
    amp = xp.sqrt(xp.maximum(g_d, 0.0))
    return xp.where(mu > 0.0, amp, 1.0)


def _apply_distal_amplitude(weighted, mu, clearance, R_occ, distal_d1, distal_d2, freq_hz, q_F_s, q_F_h):
    """Multiply the A3 distal amplitude into a ``(M, N, 3)`` weighted channel."""
    if clearance is None:
        return weighted
    amp = _distal_amplitude(mu, clearance, R_occ, distal_d1, distal_d2, freq_hz, q_F_s, q_F_h)
    return weighted * amp[:, :, None]


def compute_body_channel(
    normals: np.ndarray,
    centroids: np.ndarray,
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    n_tilde: complex | np.ndarray,
    sigma: float,
    freq_hz: float,
    n_elements: int,
    fock_R: np.ndarray | None = None,
    q_F_s: complex | None = None,
    q_F_h: complex | None = None,
    clearance: np.ndarray | None = None,
    R_occ: np.ndarray | None = None,
    distal_d1: np.ndarray | None = None,
    distal_d2: np.ndarray | None = None,
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
    fock_R : (M,) or (M, N) or None
        In-incidence-plane radius of curvature [m] for the Fock shadow gate.
        ``None`` (default) disables the gate, reproducing the ungated channel
        bit-for-bit (back-compat).
    q_F_s, q_F_h : complex or None
        Impedance-Fock parameters for the soft (TE) and hard (TM) creeping
        constants. ``None`` selects the PEC Fock gate.

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

    # F_n(r) @ psi_n for each (m, n): shape (M, N, 3). With the Fock gate the
    # soft/hard creeping constants fold into the TE/TM transmission coefficients
    # (a per-(m, n) scalar multiplier), so the canonical Fresnel operator applies
    # unchanged. This is identical to gating the combined output because the
    # projection is linear in t_s/t_p.
    if fock_R is None:
        F_psi = apply_fresnel_operator(psi, t_s, t_p, e_s, e_p)
    else:
        g_soft, g_hard = _fock_gate_factors(mu, fock_R, freq_hz, q_F_s, q_F_h)
        F_psi = apply_fresnel_operator(psi, g_soft * t_s, g_hard * t_p, e_s, e_p)

    # Depth coupling weight: sqrt(sigma / (4 * alpha_n))
    # alpha_n is the amplitude decay rate: k0*xi = beta - i*alpha, so alpha = -Im(k0*xi)
    # xi depends on incidence angle, so alpha varies per (m, n) pair
    # xi_from_mu is element-wise; pass (M, N) directly, no ravel needed
    xi = xi_from_mu(mu, n_tilde)
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

    # Distal self-shadowing (A3 approximation, DECISIONS L9 / sec_08): fold the
    # real amplitude sqrt(G_d) into the channel on the would-be-lit response
    # (mu > 0), keeping the existing plane-wave phase. Correct amplitude,
    # approximate interference phase; never overpredicts.
    weighted = _apply_distal_amplitude(weighted, mu, clearance, R_occ, distal_d1, distal_d2, freq_hz, q_F_s, q_F_h)

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
    fock_R=None,
    q_F_s=None,
    q_F_h=None,
    clearance=None,
    R_occ=None,
    distal_d1=None,
    distal_d2=None,
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
    fock_R, q_F_s, q_F_h : same as compute_body_channel. ``fock_R`` is keyed on
        the center directions, so it is ``(M,)`` or ``(M, N_center)``. ``None``
        disables the gate (back-compat).

    Returns
    -------
    G_tilde : (M, 3, n_elements) complex
    """
    M = normals.shape[0]
    N_center = center_k_hat.shape[0]

    element_index = np.asarray(element_index)
    if element_index.size > 0:
        idx_min, idx_max = int(element_index.min()), int(element_index.max())
        if idx_min < 0 or idx_max >= n_elements:
            raise ValueError(f"element_index values must be in [0, {n_elements}), got range [{idx_min}, {idx_max}]")

    k0 = 2 * xp.pi * freq_hz / C_0

    # Compute Fresnel for N_center directions only (not N_total)
    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, center_k_hat, n_tilde)

    # Depth coupling per (M, N_center)
    # xi_from_mu is element-wise; pass (M, N_center) directly, no ravel needed
    xi = xi_from_mu(mu, n_tilde)
    k0_xi = k0 * xi
    alpha = -xp.imag(k0_xi)
    alpha = xp.maximum(alpha, NUMERICAL_FLOOR)
    depth_weight = xp.sqrt(sigma / (4 * alpha))  # (M, N_center)

    # Phase per (M, N_center)
    phase_arg = -k0 * (centroids @ center_k_hat.T)
    phase = xp.exp(1j * phase_arg)  # (M, N_center)

    # Precomputed scalar factor per (M, N_center)
    scalar = depth_weight * phase  # (M, N_center)

    # Polarization-resolved Fock gate per (M, N_center). The soft/hard factors
    # fold into the TE/TM transmission coefficients per center direction, so the
    # factoring (one Fresnel solve per unique direction) is preserved.
    if fock_R is None:
        g_soft = g_hard = None
    else:
        g_soft, g_hard = _fock_gate_factors(mu, fock_R, freq_hz, q_F_s, q_F_h)

    # Distal self-shadowing amplitude per (M, N_center) (A3; 1.0 on the back face).
    distal_amp = None
    if clearance is not None:
        distal_amp = _distal_amplitude(mu, clearance, R_occ, distal_d1, distal_d2, freq_hz, q_F_s, q_F_h)

    # For each expanded path, apply F @ psi_n using precomputed Fresnel components
    # element_psi is laid out as [elem0_path0..N, elem1_path0..N, ...] (element-major)
    # so expanded path (j * N_center + c) maps to center path c
    # Accumulate in numpy (mutable) then convert to xp at the end.
    # JAX arrays are immutable and do not support in-place +=.
    G = np.zeros((M, 3, n_elements), dtype=complex)

    for c in range(N_center):
        # Fresnel-filtered psi for each element at center direction c
        # t_s[:, c], t_p[:, c]: (M,) coefficients
        # e_s[:, c, :], e_p[:, c, :]: (M, 3) basis vectors
        # scalar[:, c]: (M,) combined depth*phase weight
        t_s_c = t_s[:, c]  # (M,)
        t_p_c = t_p[:, c]  # (M,)
        if g_soft is not None:
            t_s_c = t_s_c * g_soft[:, c]  # gate the TE transmission
            t_p_c = t_p_c * g_hard[:, c]  # gate the TM transmission
        e_s_c = e_s[:, c, :]  # (M, 3)
        e_p_c = e_p[:, c, :]  # (M, 3)
        sc = scalar[:, c]  # (M,)
        if distal_amp is not None:
            sc = sc * distal_amp[:, c]  # A3 distal amplitude for this direction

        # Gather all element psi vectors for this center direction
        # element_psi layout is element-major: elem j has indices [j*N_center : (j+1)*N_center]
        elem_psi_c = element_psi[c::N_center]  # (M_elem, 3) - psi for each element at direction c

        # Project each element's psi onto TE/TM basis using einsum
        # Avoids creating (M_elem, M, 3) broadcast intermediate for the dot product
        proj_s = xp.einsum("mj,ej->em", e_s_c, elem_psi_c)  # (M_elem, M)
        proj_p = xp.einsum("mj,ej->em", e_p_c, elem_psi_c)  # (M_elem, M)

        # F @ psi for each element: (M_elem, M, 3)
        # t_s_c * proj_s: (M_elem, M), broadcast with e_s_c: (M, 3)
        F_psi_elems = (t_s_c[None, :] * proj_s)[:, :, None] * e_s_c[None, :, :] + (t_p_c[None, :] * proj_p)[
            :, :, None
        ] * e_p_c[None, :, :]  # (M_elem, M, 3)

        # Apply depth*phase weight and accumulate into G
        weighted_elems = np.asarray(sc[None, :, None] * F_psi_elems)  # (M_elem, M, 3)

        # Scatter-add all elements at once (vectorized, no Python for-loop)
        elem_indices = element_index[c::N_center]  # (M_elem,)
        np.add.at(G, (slice(None), slice(None), elem_indices), weighted_elems.transpose(1, 2, 0))

    return xp.asarray(G)
