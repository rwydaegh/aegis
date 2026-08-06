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
            polarised=center_paths.polarised,
        )

    k0 = 2 * np.pi * freq_hz / C_0
    offsets = array.element_positions - array.reference_position

    # Steering and element pattern act at the SOURCE, so they use the departure
    # direction when the tracer supplies it (a bounced path leaves the array
    # toward the reflector, not toward the body). k_hat (arrival) is exact for
    # LOS and stays the fallback for producers without departure angles.
    k_dep = center_paths.k_hat_tx if center_paths.k_hat_tx is not None else center_paths.k_hat

    # Element gain is the same for all elements (same pattern and broadside),
    # so compute once. This matches the gain baked into steering_matrix() for
    # the communication channel h, keeping G_tilde and h consistent.
    # Monograph eq. (4.4): psi_n includes the element pattern C_{T,j(n)}.
    gain = array.element_gain(k_dep)  # (N,)
    psi_gained = center_paths.psi * gain[:, None]  # (N, 3)

    # Phase advance for all elements at once: (N, M)
    phase_all = np.exp(1j * k0 * (k_dep @ offsets.T))

    # Tile shared arrays: repeat each path M times (element-major ordering)
    # Layout: [elem0_path0, elem0_path1, ..., elem0_pathN, elem1_path0, ...]
    k_hat_all = np.tile(center_paths.k_hat, (M, 1)) if M > 1 else center_paths.k_hat.copy()
    k_dep_all = np.tile(k_dep, (M, 1)) if M > 1 else k_dep.copy()
    delay_all = np.tile(center_paths.delay, M) if M > 1 else center_paths.delay.copy()
    is_los_all = np.tile(center_paths.is_los, M) if M > 1 else center_paths.is_los.copy()

    # Build psi for all N*M paths in element-major order to match tile layout
    # broadcast (N,1,3) * (N,M,1) -> (N,M,3), then transpose to (M,N,3) -> reshape
    psi_all = (psi_gained[:, np.newaxis, :] * phase_all[:, :, np.newaxis]).transpose(1, 0, 2).reshape(N * M, 3)

    # Element indices: [0,0,...,0, 1,1,...,1, ..., M-1,M-1,...,M-1]
    element_idx = np.repeat(np.arange(M, dtype=np.intp), N)

    return PropagationPaths(
        k_hat=k_hat_all,
        psi=psi_all,
        element_index=element_idx,
        delay=delay_all,
        is_los=is_los_all,
        polarised=center_paths.polarised,
        k_hat_tx=k_dep_all if center_paths.k_hat_tx is not None else None,
    )
