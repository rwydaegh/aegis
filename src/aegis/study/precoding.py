"""User channel reduction and the fixed MRT precoder.

The ray tracer returns per-element *paths*, not a single channel vector. To form
the served-user MRT beam we reduce a sector's per-element paths to one complex
coefficient per element: project each path's complex polarization vector onto a
copolar axis and coherently sum within each element. The copolar axis defaults
to the dominant polarization direction across all paths.
"""

from __future__ import annotations

import numpy as np

from aegis.precoder import Precoder


def _dominant_axis(psi: np.ndarray) -> np.ndarray:
    """Unit real direction capturing the most polarization energy.

    Principal right singular vector of the stacked real/imaginary parts.
    """
    stacked = np.vstack([psi.real, psi.imag])  # (2N, 3)
    if not np.any(stacked):
        return np.array([0.0, 0.0, 1.0])
    _, _, vh = np.linalg.svd(stacked, full_matrices=False)
    return vh[0]


def user_channel_vector(paths, m_ant, copol_axis=None) -> np.ndarray:
    """Reduce per-element paths to an (m_ant,) complex channel vector.

    Each path's complex psi is projected onto ``copol_axis``; contributions are
    summed within each element index. Elements with no paths get zero.
    """
    psi = np.asarray(paths.psi, dtype=complex)
    elem = np.asarray(paths.element_index, dtype=int)
    if copol_axis is None:
        copol_axis = _dominant_axis(psi)
    axis = np.asarray(copol_axis, dtype=float)
    axis = axis / np.linalg.norm(axis)

    proj = psi @ axis  # (N,) complex, projection onto the real copolar axis
    h = np.zeros(m_ant, dtype=complex)
    np.add.at(h, elem, proj)
    return h


def mrt_for_user(h, power_w=1.0) -> Precoder:
    """Fixed MRT precoder toward the served-user channel h."""
    return Precoder.mrt(np.asarray(h, dtype=complex), P=power_w)
