"""Level 4: Polarisation-aware Fresnel map."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import jit
from aegis.kernels._base import fresnel_weights, incidence_geometry, te_tm_power_weights


@jit
def level4_polarisation(
    normals: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    power: NDArray[np.floating],
    n_tilde: complex | NDArray[np.complexfloating],
    q: float | NDArray[np.floating] = 0.0,
    psi: NDArray[np.complexfloating] | None = None,
) -> NDArray[np.floating]:
    """Compute per-triangle S_ab with polarisation correction.

    When ``psi`` is given the physical per-(triangle, path) TE/TM split is used
    (``T_eff = w_s*T_s + w_p*T_p``); otherwise the legacy scalar/array ``q``
    knob applies (``T_eff = T_avg + (q/2) DeltaT``).
    """
    mu, mu_plus = incidence_geometry(normals, k_hat)
    T_s, T_p, T_avg = fresnel_weights(mu, n_tilde)
    if psi is not None:
        w_s, w_p = te_tm_power_weights(normals, k_hat, psi)
        T_eff = w_s * T_s + w_p * T_p
    else:
        DeltaT = T_p - T_s
        T_eff = T_avg + 0.5 * q * DeltaT
    sab = (T_eff * mu_plus) @ power
    return sab
