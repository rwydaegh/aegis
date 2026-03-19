"""Field channel matrix G(r) construction from propagation paths.

G(r) = [g_1(r), ..., g_M(r)] in C^{3 x M_ant} where
g_j(r) = sum_{n: j(n)=j} psi_n * exp(-i*k0 * k_hat_n . r)

The total electric field at surface point r is E(r) = G(r) @ x.

Monograph: Definition in sec:field-channel, eq:G-def.
"""

from __future__ import annotations

import numpy as np

from aegis.constants import C_0


def compute_field_channel(
    centroids: np.ndarray,
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    freq_hz: float,
    n_elements: int,
) -> np.ndarray:
    """Build the field channel matrix G(r) at each triangle centroid.

    Parameters
    ----------
    centroids : (M, 3)
        Triangle centroid positions [m].
    k_hat : (N, 3)
        Unit directions of arrival.
    psi : (N, 3)
        Complex polarisation-amplitude vectors.
    element_index : (N,)
        Antenna element index j(n) for each path.
    freq_hz : float
        Frequency [Hz].
    n_elements : int
        Total number of antenna elements M_ant.

    Returns
    -------
    G : (M_tri, 3, M_ant)
        Field channel matrix at each triangle centroid.
    """
    M = centroids.shape[0]
    k0 = 2 * np.pi * freq_hz / C_0

    # Phase: exp(-i*k0 * k_hat_n . r_m) for each (m, n)
    # centroids: (M, 3), k_hat: (N, 3) -> dot: (M, N)
    phase_arg = -k0 * (centroids @ k_hat.T)  # (M, N)
    phase = np.exp(1j * phase_arg)  # (M, N)

    # psi_n * phase_mn: (M, N, 3) = phase[:,:,None] * psi[None,:,:]
    weighted = phase[:, :, np.newaxis] * psi[np.newaxis, :, :]  # (M, N, 3)

    # Accumulate by element: g_j(r_m) = sum_{n: j(n)=j} weighted[m, n, :]
    G = np.zeros((M, 3, n_elements), dtype=complex)
    for j in range(n_elements):
        mask = element_index == j
        if np.any(mask):
            G[:, :, j] = np.sum(weighted[:, mask, :], axis=1)

    return G
