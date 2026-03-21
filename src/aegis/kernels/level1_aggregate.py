"""Level 1: Aggregate absorbed power via directivity."""

from __future__ import annotations

import numpy as np

from aegis._array_backend import xp
from aegis.geometry.directivity import eval_sh, spherical_angles_from_k_hat


def level1_aggregate(
    total_area, A_ab, k_hat, power, T0, n_triangles, sh_coeffs=None, sh_L=4, D_table=None, D_dirs=None
):
    """Compute aggregate absorbed power via directivity."""
    N = k_hat.shape[0]

    if sh_coeffs is not None:
        theta, phi = spherical_angles_from_k_hat(np.asarray(k_hat))
        D = eval_sh(sh_coeffs, theta, phi, sh_L)
    elif D_table is not None and D_dirs is not None:
        dots = xp.asarray(k_hat) @ xp.asarray(D_dirs).T
        nearest = xp.argmax(dots, axis=1)
        D = xp.asarray(D_table)[nearest]
    else:
        D = xp.ones(N)

    p_abs = T0 * (A_ab / 4.0) * float(xp.sum(xp.asarray(power) * D))

    sab_uniform = p_abs / total_area if total_area > 0 else 0.0
    sab = np.full(n_triangles, sab_uniform)
    return sab, p_abs
