"""Level 1: Aggregate absorbed power via directivity."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import xp
from aegis.geometry.directivity import eval_sh, spherical_angles_from_k_hat


def level1_aggregate(
    total_area: float,
    A_ab: float,
    k_hat: NDArray[np.floating],
    power: NDArray[np.floating],
    T0: float,
    n_triangles: int,
    sh_coeffs: NDArray[np.number] | None = None,
    sh_L: int = 4,
    D_table: NDArray[np.floating] | None = None,
    D_dirs: NDArray[np.floating] | None = None,
) -> tuple[NDArray[np.floating], float]:
    """Compute aggregate absorbed power via directivity."""
    n_paths: int = int(k_hat.shape[0])

    directivity: NDArray[np.floating]
    if sh_coeffs is not None:
        theta, phi = spherical_angles_from_k_hat(np.asarray(k_hat))
        directivity = eval_sh(sh_coeffs, theta, phi, sh_L)
    elif D_table is not None and D_dirs is not None:
        dots = xp.asarray(k_hat) @ xp.asarray(D_dirs).T
        nearest = xp.argmax(dots, axis=1)
        directivity = xp.asarray(D_table)[nearest]
    else:
        directivity = np.ones(n_paths)

    p_abs = T0 * (A_ab / 4.0) * float(xp.sum(np.asarray(power) * directivity))

    sab_uniform = p_abs / total_area if total_area > 0 else 0.0
    sab = xp.full(n_triangles, sab_uniform)
    return sab, p_abs
