"""Factored Fresnel + vmap path for batched coherent Q construction.

Speedup over ``compute_body_channel`` on element-expanded paths comes from
two structural facts:

1. ``compute_fresnel_operator`` and ``apply_fresnel_operator`` only depend on
   the center-of-array directions ``k_hat`` (one direction per ray), not on
   the per-element expanded paths. Computing them at ``N_center`` directions
   and folding the per-element steering phase into the final einsum saves a
   factor of ``M_ant`` of Fresnel work.

2. With (1) in hand, the per-body kernel becomes a closed pure-JAX function
   of ``(normals, centroids, areas, center_k_hat, center_psi, offsets)`` with
   no Python-side loops or scatter-add. ``jax.vmap`` over a leading body axis
   collapses 50 device dispatches into one.

The output of ``compute_body_channel_factored_jax`` is bit-equivalent (up to
floating-point round-off) to ``compute_body_channel`` on the same paths
expanded via ``expand_paths_to_array``. See
``tests/test_coherent_fast.py`` for the equivalence check.

This module is private (leading underscore): the public coherent API is
``body_channel.compute_body_channel`` and ``exposure_operator``.
"""

from __future__ import annotations

import jax
import jax.numpy as jnp

from aegis.coherent.body_channel import _fock_gate_factors
from aegis.coherent.fresnel_operator import compute_fresnel_operator
from aegis.constants import C_0
from aegis.defaults import NUMERICAL_FLOOR
from aegis.tissue.fresnel import xi_from_mu


def compute_body_channel_factored_jax(
    normals,
    centroids,
    center_k_hat,
    center_psi,
    array_offsets,
    n_tilde,
    sigma,
    freq_hz,
    fock_R=None,
    q_F_s=None,
    q_F_h=None,
):
    """Build G_tilde(r) for a single body using factored Fresnel.

    Equivalent to ``compute_body_channel(...)`` evaluated on the path set
    produced by ``expand_paths_to_array(center_paths, array, freq_hz)``,
    but keeps the Fresnel work at ``N_center`` directions and folds the
    per-element steering into the final tensor contraction.

    Parameters
    ----------
    normals : (M, 3)
        Unit outward normals.
    centroids : (M, 3)
        Triangle centroid positions [m].
    center_k_hat : (N_center, 3)
        Unit directions of arrival at the array center.
    center_psi : (N_center, 3) complex
        Per-direction polarisation-amplitude vectors with element pattern
        gain already folded in (matching what ``expand_paths_to_array``
        applies via ``array.element_gain``).
    array_offsets : (M_ant, 3)
        Element positions relative to the array reference position.
    n_tilde : complex
        Complex tissue refractive index.
    sigma : float
        Tissue conductivity [S/m].
    freq_hz : float
        Carrier frequency [Hz].
    fock_R : (M,) or (M, N_center) or None
        In-incidence-plane radius of curvature [m] for the Fock shadow gate,
        keyed on the center directions. ``None`` (default) disables the gate,
        reproducing the ungated channel bit-for-bit (back-compat). This mirrors
        the NumPy reference ``compute_body_channel_factored``.
    q_F_s, q_F_h : complex or None
        Impedance-Fock parameters for the soft (TE) and hard (TM) creeping
        constants. ``None`` selects the PEC Fock gate. These are static scalar
        constants (the Airy/Leontovich eigenvalue solve runs in numpy/scipy
        outside the traced region inside :func:`_fock_gate_factors`), so they
        must be passed as Python scalars, not traced arrays.

    Returns
    -------
    G_tilde : (M, 3, M_ant) complex
    """
    k0 = 2.0 * jnp.pi * freq_hz / C_0

    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, center_k_hat, n_tilde)

    # Polarization-resolved Fock gate folds into the TE/TM transmission
    # coefficients per center direction, identical to the NumPy reference
    # ``apply_fresnel_operator(psi, g_soft*t_s, g_hard*t_p, e_s, e_p)``. The
    # factoring (one Fresnel solve per unique direction) is preserved because
    # the gate is a per-(triangle, direction) scalar multiplier on t_s / t_p.
    if fock_R is not None:
        g_soft, g_hard = _fock_gate_factors(mu, fock_R, freq_hz, q_F_s, q_F_h)
        t_s = g_soft * t_s
        t_p = g_hard * t_p

    xi = xi_from_mu(mu, n_tilde)
    alpha = -jnp.imag(k0 * xi)
    alpha = jnp.maximum(alpha, NUMERICAL_FLOOR)
    depth_weight = jnp.sqrt(sigma / (4.0 * alpha))  # (M, N_c)

    phase_pos = jnp.exp(-1j * k0 * (centroids @ center_k_hat.T))  # (M, N_c)

    # Fresnel-projected center psi at every triangle: (M, N_c, 3).
    psi_s = jnp.einsum("mci,ci->mc", e_s, center_psi)
    psi_p = jnp.einsum("mci,ci->mc", e_p, center_psi)
    F_psi_center = (t_s * psi_s)[:, :, None] * e_s + (t_p * psi_p)[:, :, None] * e_p

    # Per-(triangle, direction) static scalar combining depth and centroid phase.
    scalar = depth_weight * phase_pos  # (M, N_c) complex

    # Per-element steering phase: exp(+i k0 k_hat[c] . offset[j]).
    # Matches expand_paths_to_array's per-element phase advance.
    phase_advance = jnp.exp(1j * k0 * (center_k_hat @ array_offsets.T))  # (N_c, M_ant)

    # G_tilde[m, i, j] = sum_c scalar[m,c] * F_psi_center[m,c,i] * phase_advance[c,j]
    return jnp.einsum("mc,mci,cj->mij", scalar, F_psi_center, phase_advance)


def compute_q_for_body(
    normals,
    centroids,
    areas,
    center_k_hat,
    center_psi,
    array_offsets,
    n_tilde,
    sigma,
    freq_hz,
    fock_R=None,
    q_F_s=None,
    q_F_h=None,
):
    """Single-body Q via the factored body channel.

    ``fock_R`` / ``q_F_s`` / ``q_F_h`` thread the Fock shadow gate through the
    factored channel (see :func:`compute_body_channel_factored_jax`). ``None``
    disables the gate.

    Returns
    -------
    Q : (M_ant, M_ant) Hermitian PSD.
    """
    G_tilde = compute_body_channel_factored_jax(
        normals,
        centroids,
        center_k_hat,
        center_psi,
        array_offsets,
        n_tilde,
        sigma,
        freq_hz,
        fock_R=fock_R,
        q_F_s=q_F_s,
        q_F_h=q_F_h,
    )
    Q = jnp.einsum("m,mia,mib->ab", areas, jnp.conj(G_tilde), G_tilde)
    return 0.5 * (Q + jnp.conj(Q).T)


def compute_q_batch_vmap(
    normals_b,
    centroids_b,
    areas_b,
    center_k_hat_b,
    center_psi_b,
    array_offsets,
    n_tilde,
    sigma,
    freq_hz,
    fock_R_b=None,
    q_F_s=None,
    q_F_h=None,
):
    """Batched (over bodies) Q construction via ``jax.vmap``.

    All per-body inputs share their leading axis (``B`` = number of bodies).
    Triangles per body and paths per body are assumed equal across the batch
    (pad / decimate to a common shape upstream when they differ).

    Parameters
    ----------
    normals_b : (B, M, 3)
    centroids_b : (B, M, 3)
    areas_b : (B, M)
    center_k_hat_b : (B, N_c, 3)
    center_psi_b : (B, N_c, 3) complex
    array_offsets : (M_ant, 3) -- shared across bodies
    n_tilde, sigma, freq_hz : same as ``compute_body_channel``.
    fock_R_b : (B, M) or (B, M, N_c) or None
        Per-body Fock radius (mapped over the leading body axis). ``None``
        disables the gate for the whole batch, matching the ungated behavior
        bit-for-bit.
    q_F_s, q_F_h : complex or None
        Shared (non-mapped) impedance-Fock scalar parameters. Passed as Python
        scalars so the eigenvalue solve stays a numpy/scipy constant outside the
        traced region (see :func:`compute_body_channel_factored_jax`).

    Returns
    -------
    Q_b : (B, M_ant, M_ant) complex
    """
    # ``fock_R`` is per-body (mapped); ``q_F_s`` / ``q_F_h`` are shared static
    # scalars (not mapped). When the gate is off, ``fock_R_b`` is ``None`` and is
    # broadcast (in_axes None) so every body runs the ungated path.
    fock_axis = None if fock_R_b is None else 0
    in_axes = (0, 0, 0, 0, 0, None, None, None, None, fock_axis, None, None)
    return jax.vmap(compute_q_for_body, in_axes=in_axes)(
        normals_b,
        centroids_b,
        areas_b,
        center_k_hat_b,
        center_psi_b,
        array_offsets,
        n_tilde,
        sigma,
        freq_hz,
        fock_R_b,
        q_F_s,
        q_F_h,
    )
