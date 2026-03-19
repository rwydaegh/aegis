"""Level 3: Exact Fresnel spatial map.

Replaces the constant T_0 with angle-dependent T_avg(theta):
    S_ab_j = sum_i S_i * T_avg(mu_ji) * [mu_ji]_+

where T_avg = (T_s + T_p) / 2 is the unpolarised average transmission.

Cost: O(M * N), same as Level 2 but with per-element Fresnel evaluation.
"""

from __future__ import annotations

import numpy as np

from aegis.kernels._base import fresnel_weights, incidence_geometry


def level3_fresnel(
    normals: np.ndarray,
    k_hat: np.ndarray,
    power: np.ndarray,
    n_tilde: complex,
) -> np.ndarray:
    """Compute per-triangle S_ab with angle-dependent Fresnel transmission.

    Parameters
    ----------
    normals : (M, 3) unit outward normals
    k_hat : (N, 3) incident directions
    power : (N,) per-path power density [W/m^2]
    n_tilde : complex refractive index of the tissue

    Returns
    -------
    sab : (M,) absorbed power density per triangle [W/m^2]
    """
    mu, mu_plus = incidence_geometry(normals, k_hat)
    _T_s, _T_p, T_avg = fresnel_weights(mu, n_tilde)

    # S_ab_j = sum_i S_i * T_avg(mu_ji) * [mu_ji]_+
    sab = (T_avg * mu_plus) @ power  # (M,)
    return sab
