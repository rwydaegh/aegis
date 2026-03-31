"""Field channel matrix G(r) construction from propagation paths.

G(r) = [g_1(r), ..., g_M(r)] in C^{3 x M_ant} where
g_j(r) = sum_{n: j(n)=j} psi_n * exp(-i*k0 * k_hat_n . r)

The total electric field at surface point r is E(r) = G(r) @ x.

Monograph: Definition in sec:field-channel, eq:G-def.
"""

from __future__ import annotations

import numpy as np

from aegis._array_backend import xp
from aegis.coherent._accumulate import accumulate_by_element
from aegis.constants import C_0


def compute_field_channel(
    centroids,
    k_hat,
    psi,
    element_index,
    freq_hz,
    n_elements,
):
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

    # Validate element_index bounds to prevent silent data loss
    element_index = np.asarray(element_index)
    if element_index.size > 0:
        idx_min, idx_max = int(element_index.min()), int(element_index.max())
        if idx_min < 0 or idx_max >= n_elements:
            raise ValueError(f"element_index values must be in [0, {n_elements}), got range [{idx_min}, {idx_max}]")

    k0 = 2 * xp.pi * freq_hz / C_0

    # Phase: exp(-i*k0 * k_hat_n . r_m) for each (m, n)
    phase_arg = -k0 * (centroids @ k_hat.T)  # (M, N)
    phase = xp.exp(1j * phase_arg)  # (M, N)

    # psi_n * phase_mn: (M, N, 3) = phase[:,:,None] * psi[None,:,:]
    weighted = phase[:, :, None] * psi[None, :, :]  # (M, N, 3)

    # Accumulate by element: g_j(r_m) = sum_{n: j(n)=j} weighted[m, n, :]
    return accumulate_by_element(weighted, element_index, M, n_elements)
