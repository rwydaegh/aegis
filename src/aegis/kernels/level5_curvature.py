"""Level 5: Curvature correction."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import jit, xp
from aegis.constants import C_0
from aegis.kernels._base import fresnel_weights, incidence_geometry


@jit
def level5_curvature(
    normals: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    power: NDArray[np.floating],
    n_tilde: complex | NDArray[np.complexfloating],
    T0: float,
    curvature_H: NDArray[np.floating],
    freq_hz: float,
) -> NDArray[np.floating]:
    """Compute per-triangle S_ab with Fresnel + curvature correction."""
    # Floor k to avoid division by near-zero at very low frequencies
    k = xp.maximum(2.0 * xp.pi * freq_hz / C_0, 1e-6)

    mu, mu_plus = incidence_geometry(normals, k_hat)
    _T_s, _T_p, T_avg = fresnel_weights(mu, n_tilde)
    sab_base = (T_avg * mu_plus) @ power

    H_safe = xp.maximum(curvature_H, 0.0)
    sab_curvature = T0 * (H_safe / k) * xp.einsum("mn,mn,n->m", mu_plus, mu_plus, power)

    return xp.maximum(sab_base + sab_curvature, 0.0)
