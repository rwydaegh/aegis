"""Level 3: Exact Fresnel spatial map."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import jit
from aegis.kernels._base import fresnel_weights, incidence_geometry


@jit
def level3_fresnel(
    normals: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    power: NDArray[np.floating],
    n_tilde: complex | NDArray[np.complexfloating],
) -> NDArray[np.floating]:
    """Compute per-triangle S_ab with angle-dependent Fresnel transmission."""
    mu, mu_plus = incidence_geometry(normals, k_hat)
    _T_s, _T_p, T_avg = fresnel_weights(mu, n_tilde)
    sab = (T_avg * mu_plus) @ power
    return sab
