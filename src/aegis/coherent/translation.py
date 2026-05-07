"""Translation phasor identity for cheap per-slot Q refresh.

When a body translates rigidly by ``Δt`` (pose held fixed), the body-surface
channel ``G_tilde(r_0 + Δt)`` differs from ``G_tilde(r_0)`` only by a per-path
phase factor ``φ[c] = exp(-i k0 k_hat[c] · Δt)``. Equivalently, in the path-
correlation Gram form ``M(t) = Φ(t)^H M(0) Φ(t)`` of paper §III.C, with
``Φ(t) = diag(φ)``.

For Q this means
``Q(Δt) = sum_{c, d} conj(φ[c]) φ[d] · M_static[c, d, :, :]``
where ``M_static`` is precomputable once per (body, pose) and reusable for
arbitrary Δt at slot cadence (one ``N_c``-vector of complex exponentials and
one ``(N_c, N_c, M_ant, M_ant)`` einsum per body).

This file owns the static-cache build and the translate-only refresh; it
does not own the per-pose ``M_static`` storage policy. Callers decide
whether to keep it on device (fast slot refresh) or on host.

Reference: paper_v2.tex §III.C, eq:Mphase.
"""

from __future__ import annotations

import jax.numpy as jnp

from aegis.coherent.fresnel_operator import compute_fresnel_operator
from aegis.constants import C_0
from aegis.defaults import NUMERICAL_FLOOR
from aegis.tissue.fresnel import xi_from_mu


def compute_static_path_gram(
    normals,
    centroids_0,
    areas,
    center_k_hat,
    center_psi,
    array_offsets,
    n_tilde,
    sigma,
    freq_hz,
):
    """Build the static path-correlation Gram ``M_static[c, d, a, b]``.

    Caller is expected to invoke this once per (body geometry, pose,
    path-set) and reuse the result for every translation refresh until
    pose or geometry changes. The reference centroid set ``centroids_0``
    is the one for which Δt = 0.

    Parameters
    ----------
    normals : (M, 3)
    centroids_0 : (M, 3)
        Triangle centroids at the reference position. Translation refresh
        is relative to this.
    areas : (M,)
    center_k_hat : (N_c, 3)
    center_psi : (N_c, 3) complex
        Element-gain-folded center psi (matching ``compute_body_channel_factored_jax``).
    array_offsets : (M_ant, 3)
    n_tilde : complex
    sigma : float
    freq_hz : float

    Returns
    -------
    M_static : (N_c, N_c, M_ant, M_ant) complex
    """
    k0 = 2.0 * jnp.pi * freq_hz / C_0

    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, center_k_hat, n_tilde)

    xi = xi_from_mu(mu, n_tilde)
    alpha = -jnp.imag(k0 * xi)
    alpha = jnp.maximum(alpha, NUMERICAL_FLOOR)
    depth_weight = jnp.sqrt(sigma / (4.0 * alpha))  # (M, N_c)

    phase_pos = jnp.exp(-1j * k0 * (centroids_0 @ center_k_hat.T))  # (M, N_c)
    scalar = depth_weight * phase_pos  # (M, N_c)

    psi_s = jnp.einsum("mci,ci->mc", e_s, center_psi)
    psi_p = jnp.einsum("mci,ci->mc", e_p, center_psi)
    F_psi_center = (t_s * psi_s)[:, :, None] * e_s + (t_p * psi_p)[:, :, None] * e_p  # (M, N_c, 3)

    phase_advance = jnp.exp(1j * k0 * (center_k_hat @ array_offsets.T))  # (N_c, M_ant)

    # h[m, c, i, j] = scalar[m, c] * F_psi_center[m, c, i] * phase_advance[c, j]
    # area-weighted: a[m, c, i, j] = sqrt(area[m]) * h[m, c, i, j]
    # (split the area weight so the gram becomes a clean inner product)
    sqrt_area = jnp.sqrt(areas)
    a_weighted = (
        (sqrt_area[:, None] * scalar)[:, :, None, None] * F_psi_center[:, :, :, None] * phase_advance[None, :, None, :]
    )  # (M, N_c, 3, M_ant)

    # M_static[c, d, p, q] = sum_{m, i} conj(a_weighted[m, c, i, p]) * a_weighted[m, d, i, q]
    return jnp.einsum("mcip,mdiq->cdpq", jnp.conj(a_weighted), a_weighted)


def translation_phasor(center_k_hat, delta_t, freq_hz):
    """Per-direction phasor ``φ[c] = exp(-i k0 k_hat[c] · Δt)``.

    Parameters
    ----------
    center_k_hat : (N_c, 3)
    delta_t : (3,)
        Translation vector [m]; ``r = r_0 + Δt``.
    freq_hz : float

    Returns
    -------
    phi : (N_c,) complex
    """
    k0 = 2.0 * jnp.pi * freq_hz / C_0
    return jnp.exp(-1j * k0 * (center_k_hat @ delta_t))


def q_translate(M_static, phi):
    """Refresh Q under translation by sandwiching ``M_static`` with ``φ``.

    ``Q(Δt) = sum_{c,d} conj(phi[c]) * phi[d] * M_static[c, d, :, :]``

    Parameters
    ----------
    M_static : (N_c, N_c, M_ant, M_ant)
    phi : (N_c,)

    Returns
    -------
    Q : (M_ant, M_ant) Hermitian.
    """
    Q = jnp.einsum("c,d,cdpq->pq", jnp.conj(phi), phi, M_static)
    return 0.5 * (Q + jnp.conj(Q).T)


def q_translate_batch(M_static_b, phi_b):
    """Batched translation refresh.

    Parameters
    ----------
    M_static_b : (B, N_c, N_c, M_ant, M_ant)
    phi_b : (B, N_c)

    Returns
    -------
    Q_b : (B, M_ant, M_ant)
    """
    Q = jnp.einsum("bc,bd,bcdpq->bpq", jnp.conj(phi_b), phi_b, M_static_b)
    return 0.5 * (Q + jnp.conj(jnp.swapaxes(Q, -1, -2)))
