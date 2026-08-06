"""Coherent free-space field synthesis on arbitrary point sets.

The reconstruction model is the same local plane-wave expansion that the
coherent operator itself is built on (paper Sec. 3): each ray-traced path n
arrives as a plane wave with complex polarisation-amplitude vector psi_n
(referenced to the world origin) and direction k_hat_n, so for a precoder x

    E(r) = sum_n x_{j(n)} psi_n exp(-i k0 k_hat_n . r).

Performance comes from collapsing the element sum before touching the grid.
With the precoder fixed, paths sharing an arrival direction (the synthetic
array layout repeats the same k_hat for all 64 elements) merge into a single
weighted plane wave

    E(r) = sum_u w_u exp(-i k0 k_hat_u . r),
    w_u  = sum_{n: k_hat_n = k_hat_u} x_{j(n)} psi_n,

which turns a (P x N_paths) problem into a (P x N_unique) one, a 64x saving
for the 8x8 URA. The grid matmul is chunked so peak memory stays bounded.
"""

from __future__ import annotations

import numpy as np

from aegis.constants import C_0, Z_0


def collapse_paths(
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Fold the precoder into per-direction plane-wave weights.

    Parameters
    ----------
    k_hat : (N, 3)
        Unit arrival directions, one per path.
    psi : (N, 3) complex
        Polarisation-amplitude vectors referenced to the world origin.
    element_index : (N,)
        Originating antenna element per path.
    x : (M_ant,) complex
        Precoder, ||x||^2 = P.

    Returns
    -------
    k_unique : (U, 3)
        Deduplicated arrival directions.
    weights : (U, 3) complex
        Coherent plane-wave weights w_u (precoder already applied).
    """
    k_hat = np.asarray(k_hat, dtype=float)
    psi = np.asarray(psi)
    element_index = np.asarray(element_index)
    x = np.asarray(x)

    weighted = psi * x[element_index][:, None]  # (N, 3)

    # Group paths by identical arrival direction. Quantise to float32 bit
    # patterns: synthetic-array layouts repeat k_hat exactly, generic layouts
    # simply do not collapse (every direction stays its own group).
    keys = (
        np.ascontiguousarray(k_hat.astype(np.float32))
        .view([("kx", np.float32), ("ky", np.float32), ("kz", np.float32)])
        .ravel()
    )
    k_unique_keys, inverse = np.unique(keys, return_inverse=True)
    n_unique = k_unique_keys.shape[0]

    weights = np.zeros((n_unique, 3), dtype=complex)
    np.add.at(weights, inverse, weighted)

    # Representative full-precision direction per group (first occurrence)
    first = np.full(n_unique, -1, dtype=np.intp)
    seen = np.zeros(n_unique, dtype=bool)
    order = np.arange(k_hat.shape[0])
    # first occurrence per group without a Python loop
    rev = order[::-1]
    first[inverse[rev]] = rev
    del seen
    k_unique = k_hat[first]

    return k_unique, weights


def synthesize_field(
    points: np.ndarray,
    k_unique: np.ndarray,
    weights: np.ndarray,
    freq_hz: float,
    *,
    chunk_size: int = 1 << 17,
    dtype=np.complex64,
) -> np.ndarray:
    """Evaluate E(r) = sum_u w_u exp(-i k0 k_hat_u . r) on a point set.

    Parameters
    ----------
    points : (P, 3)
        World-frame sample positions [m].
    k_unique : (U, 3)
        Plane-wave directions.
    weights : (U, 3) complex
        Plane-wave weights (precoder folded in).
    freq_hz : float
        Carrier frequency [Hz].
    chunk_size : int
        Points per matmul chunk (bounds peak memory at
        chunk_size * U * 8 bytes for the phase block).
    dtype : numpy dtype
        complex64 keeps the phase block half the size of complex128 and is
        ample for visualisation dynamic range.

    Returns
    -------
    E : (P, 3) complex
        Complex E-field phasor at each point [V/m].
    """
    points = np.asarray(points, dtype=float)
    k_unique = np.asarray(k_unique, dtype=float)
    w = np.asarray(weights).astype(dtype)

    k0 = 2 * np.pi * freq_hz / C_0
    P = points.shape[0]
    E = np.empty((P, 3), dtype=dtype)
    # complex64 keeps the phase block small for visualisation; complex128
    # callers (tests, quantitative metrics) get full-precision phase.
    real_dtype = np.float64 if np.dtype(dtype) == np.complex128 else np.float32

    for start in range(0, P, chunk_size):
        stop = min(start + chunk_size, P)
        block = points[start:stop]  # (B, 3)
        phase_arg = (-k0 * (block @ k_unique.T)).astype(real_dtype)  # (B, U)
        phase = np.exp(1j * phase_arg).astype(dtype)
        E[start:stop] = phase @ w  # (B, 3)

    return E


def field_on(
    grid,
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    x: np.ndarray,
    freq_hz: float,
    **kwargs,
) -> np.ndarray:
    """Reconstruct E on a SlicePlane or FieldVolume, shaped like the grid.

    Returns an array of shape ``grid.shape + (3,)`` complex.
    """
    k_unique, weights = collapse_paths(k_hat, psi, element_index, x)
    E_flat = synthesize_field(grid.points, k_unique, weights, freq_hz, **kwargs)
    return grid.reshape(E_flat)


def channel_at(
    points: np.ndarray,
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    freq_hz: float,
    n_elements: int,
    *,
    rx_polarisation: np.ndarray | None = None,
    rx_response=None,
) -> np.ndarray:
    """Per-element scalar channel h(r) at one or more points.

    h_j(r) = sum_{n: j(n)=j} a_n exp(-i k0 k_hat_n . r),
    a_n = C_R(k_hat_n)^H psi_n,

    the monograph signal-branch channel (eq. h-def): each path's 3D
    polarisation-amplitude vector psi_n is projected onto the UE receive
    antenna response C_R(k). Conjugating h gives the MRT precoder that focuses
    at r. The base-station transmit pattern is already inside psi; this is the
    only place the *UE* antenna enters, exactly as in AEGIS MIMO mode.

    Parameters
    ----------
    points : (3,) or (P, 3)
        Focus point(s).
    rx_response : callable ``k_hat -> (N, 3) complex`` optional
        The UE antenna response C_R per arrival direction (see
        ``aegis.hotspot.antenna.make_rx_response``). When given it takes
        precedence and the channel is fully antenna-aware.
    rx_polarisation : (3,) optional
        Legacy fixed receive polarisation reference (unit-gain, no directivity).
        Default vertical, matching ``channel_h_from_paths`` in paperC_simulate.
        Ignored if ``rx_response`` is provided.

    Returns
    -------
    h : (M_ant,) or (P, M_ant) complex
    """
    pts = np.atleast_2d(np.asarray(points, dtype=float))
    k_hat = np.asarray(k_hat, dtype=float)
    psi = np.asarray(psi)
    element_index = np.asarray(element_index)

    if rx_response is not None:
        c_r = np.asarray(rx_response(k_hat))  # (N, 3) complex C_R(k)
        scalar = np.einsum("nj,nj->n", np.conj(c_r), psi)  # a_n = C_R^H psi_n
    else:
        ref = np.array([0.0, 0.0, 1.0]) if rx_polarisation is None else _unit_vec(rx_polarisation)
        # e_pol per path: ref minus its k_hat component, normalised
        proj = ref[None, :] - (k_hat @ ref)[:, None] * k_hat  # (N, 3)
        norms = np.linalg.norm(proj, axis=1, keepdims=True)
        fallback = np.array([1.0, 0.0, 0.0])
        e_pol = np.where(norms > 1e-12, proj / np.where(norms > 0, norms, 1.0), fallback)
        scalar = np.einsum("nj,nj->n", e_pol, psi)  # (N,) complex

    k0 = 2 * np.pi * freq_hz / C_0
    phase = np.exp(-1j * k0 * (pts @ k_hat.T))  # (P, N)
    contrib = phase * scalar[None, :]  # (P, N)

    h = np.zeros((pts.shape[0], n_elements), dtype=complex)
    np.add.at(h, (slice(None), element_index), contrib)

    return h[0] if np.asarray(points).ndim == 1 else h


def field_channel_at(
    point: np.ndarray,
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    freq_hz: float,
    n_elements: int,
) -> np.ndarray:
    """Vector free-space field channel G(r) in C^{3 x M_ant}: E(r) = G(r) x.

    Column j is the field that element j alone radiates to r,
    g_j(r) = sum_{n: j(n)=j} psi_n exp(-i k0 k_hat_n . r). The largest singular
    value of G(r) is the worst-case local field magnitude per unit precoder
    norm (the local exposure eigenvalue), and its right singular vector is the
    precoder that achieves it.
    """
    r = np.asarray(point, dtype=float)
    k_hat = np.asarray(k_hat, dtype=float)
    psi = np.asarray(psi)
    element_index = np.asarray(element_index)
    k0 = 2 * np.pi * freq_hz / C_0
    phase = np.exp(-1j * k0 * (k_hat @ r))  # (N,)
    contrib = psi * phase[:, None]  # (N, 3)
    G = np.zeros((3, n_elements), dtype=complex)
    np.add.at(G, (slice(None), element_index), contrib.T)
    return G


def power_density(E: np.ndarray) -> np.ndarray:
    """Free-space equivalent power density S = |E|^2 / (2 Z_0) [W/m^2]."""
    E = np.asarray(E)
    return np.sum(np.abs(E) ** 2, axis=-1) / (2 * Z_0)


def _unit_vec(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)
