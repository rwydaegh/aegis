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

import os

from aegis.coherent.fresnel_operator import compute_fresnel_operator
from aegis.constants import C_0
from aegis.defaults import NUMERICAL_FLOOR
from aegis.tissue.fresnel import xi_from_mu

# The static gram's transient `a_weighted` tensor is (M_tri, N_c, 3, M_ant); at
# full phantom resolution with a diffraction-rich path set it reaches tens of GB
# and overflows a GPU. Process triangles in blocks sized so this tensor stays
# near this many elements. M_static contracts the triangle index, so the blocked
# sum is identical to the unchunked einsum. Override per device with
# AEGIS_GRAM_CHUNK_ELEMS.
_GRAM_CHUNK_ELEMS = int(os.environ.get("AEGIS_GRAM_CHUNK_ELEMS", 32_000_000))


def _gram_chunk(n_tri: int, n_c: int, m_ant: int) -> int:
    """Triangles per block so the (B, N_c, 3, M_ant) intermediate stays bounded."""
    per = max(1, n_c * 3 * m_ant)
    return max(1, min(max(1, n_tri), _GRAM_CHUNK_ELEMS // per))


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
    import jax.numpy as jnp

    k0 = 2.0 * jnp.pi * freq_hz / C_0

    normals = jnp.asarray(normals)
    centroids_0 = jnp.asarray(centroids_0)
    areas = jnp.asarray(areas)
    center_k_hat = jnp.asarray(center_k_hat)
    center_psi = jnp.asarray(center_psi)
    array_offsets = jnp.asarray(array_offsets)

    n_tri = normals.shape[0]
    n_c = center_k_hat.shape[0]
    m_ant = array_offsets.shape[0]

    # Block-independent: advance of each center direction across the array.
    phase_advance = jnp.exp(1j * k0 * (center_k_hat @ array_offsets.T))  # (N_c, M_ant)

    def _block_gram(sl: slice):
        nrm, cen, ar = normals[sl], centroids_0[sl], areas[sl]
        mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(nrm, center_k_hat, n_tilde)
        xi = xi_from_mu(mu, n_tilde)
        alpha = jnp.maximum(-jnp.imag(k0 * xi), NUMERICAL_FLOOR)
        depth_weight = jnp.sqrt(sigma / (4.0 * alpha))  # (B, N_c)
        phase_pos = jnp.exp(-1j * k0 * (cen @ center_k_hat.T))  # (B, N_c)
        scalar = depth_weight * phase_pos  # (B, N_c)
        psi_s = jnp.einsum("mci,ci->mc", e_s, center_psi)
        psi_p = jnp.einsum("mci,ci->mc", e_p, center_psi)
        f_psi = (t_s * psi_s)[:, :, None] * e_s + (t_p * psi_p)[:, :, None] * e_p  # (B, N_c, 3)
        # a[m, c, i, j] = sqrt(area[m]) * scalar[m, c] * f_psi[m, c, i] * phase_advance[c, j]
        sqrt_area = jnp.sqrt(ar)
        a_weighted = (
            (sqrt_area[:, None] * scalar)[:, :, None, None] * f_psi[:, :, :, None] * phase_advance[None, :, None, :]
        )  # (B, N_c, 3, M_ant)
        # M_static[c, d, p, q] = sum_{m, i} conj(a[m, c, i, p]) * a[m, d, i, q]
        return jnp.einsum("mcip,mdiq->cdpq", jnp.conj(a_weighted), a_weighted)

    # Triangles are independent and summed, so accumulate the gram block by block
    # to bound the (B, N_c, 3, M_ant) intermediate.
    chunk = _gram_chunk(n_tri, n_c, m_ant)
    m_static = jnp.zeros((n_c, n_c, m_ant, m_ant), dtype=complex)
    for start in range(0, n_tri, chunk):
        m_static = m_static + _block_gram(slice(start, start + chunk))
    return m_static


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
    import jax.numpy as jnp

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
    import jax.numpy as jnp

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
    import jax.numpy as jnp

    Q = jnp.einsum("bc,bd,bcdpq->bpq", jnp.conj(phi_b), phi_b, M_static_b)
    return 0.5 * (Q + jnp.conj(jnp.swapaxes(Q, -1, -2)))
