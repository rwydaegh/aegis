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

    Returns
    -------
    G_tilde : (M, 3, M_ant) complex
    """
    k0 = 2.0 * jnp.pi * freq_hz / C_0

    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, center_k_hat, n_tilde)

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
):
    """Single-body Q via the factored body channel.

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

    Returns
    -------
    Q_b : (B, M_ant, M_ant) complex
    """
    in_axes = (0, 0, 0, 0, 0, None, None, None, None)
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
    )
