"""Level 4: Polarisation-aware Fresnel map.

Adds the polarisation correction to Level 3:
    T_eff = T_avg(theta) + q/2 * DeltaT(theta)

where:
    q = local TM excess in [-1, 1]
    DeltaT = T_p - T_s (polarisation splitting)

For unpolarised or circularly polarised sources, q=0 and this reduces
to Level 3. The correction matters for linearly polarised sources.

Cost: O(M * N), same as Level 3.
"""

from __future__ import annotations

import numpy as np

from aegis.kernels._base import fresnel_weights, incidence_geometry


def level4_polarisation(
    normals: np.ndarray,
    k_hat: np.ndarray,
    power: np.ndarray,
    n_tilde: complex,
    q: np.ndarray | float = 0.0,
) -> np.ndarray:
    """Compute per-triangle S_ab with polarisation correction.

    Parameters
    ----------
    normals : (M, 3) unit outward normals
    k_hat : (N, 3) incident directions
    power : (N,) per-path power density [W/m^2]
    n_tilde : complex refractive index
    q : (M, N) or scalar, local TM excess. Default 0 (unpolarised).

    Returns
    -------
    sab : (M,) absorbed power density per triangle [W/m^2]
    """
    mu, mu_plus = incidence_geometry(normals, k_hat)
    T_s, T_p, T_avg = fresnel_weights(mu, n_tilde)
    DeltaT = T_p - T_s  # (M, N)

    T_eff = T_avg + 0.5 * q * DeltaT  # (M, N)

    sab = (T_eff * mu_plus) @ power  # (M,)
    return sab
