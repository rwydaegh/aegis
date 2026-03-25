"""Expand center-of-array paths to per-element paths with phase steering.

Given N multipath directions generated from the array center and an
AntennaArray with M elements, produce N*M paths where each element's
paths carry the appropriate phase advance exp(+i*k0 * k_hat_n . offset_j).

This is the far-field phased array model (design doc section B3).
"""

from __future__ import annotations

import numpy as np

from aegis.constants import C_0
from aegis.mimo.array import AntennaArray
from aegis.paths import PropagationPaths


def expand_paths_to_array(
    center_paths: PropagationPaths,
    array: AntennaArray,
    freq_hz: float,
) -> PropagationPaths:
    """Expand center-of-array paths to per-element paths.

    Parameters
    ----------
    center_paths : PropagationPaths
        N paths generated from the array center (any channel model).
    array : AntennaArray
        Antenna array geometry.
    freq_hz : float
        Carrier frequency [Hz].

    Returns
    -------
    PropagationPaths
        N * M paths with per-element phase steering baked into psi
        and element_index set to the originating element.
    """
    N = center_paths.n_paths
    M = array.n_elements

    if N == 0:
        empty3 = np.empty((0, 3), dtype=np.float64)
        return PropagationPaths(
            k_hat=empty3,
            psi=empty3.astype(complex),
            element_index=np.empty(0, dtype=np.intp),
            delay=np.empty(0, dtype=np.float64),
            is_los=np.empty(0, dtype=bool),
        )

    k0 = 2 * np.pi * freq_hz / C_0
    offsets = array.element_positions - array.reference_position

    per_element = []
    for j in range(M):
        phase = np.exp(1j * k0 * (center_paths.k_hat @ offsets[j]))
        psi_j = center_paths.psi * phase[:, None]

        paths_j = PropagationPaths(
            k_hat=center_paths.k_hat.copy(),
            psi=psi_j,
            element_index=np.full(N, j, dtype=np.intp),
            delay=center_paths.delay.copy(),
            is_los=center_paths.is_los.copy(),
        )
        per_element.append(paths_j)

    return PropagationPaths.concatenate(per_element, reindex_elements=False)
