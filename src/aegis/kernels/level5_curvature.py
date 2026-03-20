"""Level 5: Curvature correction.

Adds the first-order Physical Optics curvature correction to Level 3:
    S_ab_j = sum_i S_i * T_avg(mu_ji) * [mu_ji]_+
           + sum_i S_i * T_0 * (H_j / k) * [mu_ji]_+^2

where H_j = 1/R1 + 1/R2 is twice the mean curvature at triangle j,
and k = 2*pi*f/c is the free-space wavenumber.

The ReLU^2 term corrects for surface curvature. At 28 GHz the correction
is < 0.4% for torso/head, ~2% for fingers, ~8% for ear edges.

Cost: O(M * N), same as Level 3 but needs per-triangle curvature.
"""

from __future__ import annotations

import numpy as np

from aegis.constants import C_0
from aegis.kernels._base import fresnel_weights, incidence_geometry


def level5_curvature(
    normals: np.ndarray,
    k_hat: np.ndarray,
    power: np.ndarray,
    n_tilde: complex,
    T0: float,
    curvature_H: np.ndarray,
    freq_hz: float,
) -> np.ndarray:
    """Compute per-triangle S_ab with Fresnel + curvature correction.

    Parameters
    ----------
    normals : (M, 3) unit outward normals
    k_hat : (N, 3) incident directions
    power : (N,) per-path power density [W/m^2]
    n_tilde : complex refractive index
    T0 : normal-incidence transmission
    curvature_H : (M,) twice mean curvature H = 1/R1 + 1/R2 [1/m]
    freq_hz : frequency [Hz]

    Returns
    -------
    sab : (M,) absorbed power density per triangle [W/m^2]
    """
    k = 2.0 * np.pi * freq_hz / C_0

    mu, mu_plus = incidence_geometry(normals, k_hat)
    _T_s, _T_p, T_avg = fresnel_weights(mu, n_tilde)
    sab_base = (T_avg * mu_plus) @ power  # (M,)

    # Curvature correction: T_0 * (H_j / k) * ReLU(mu)^2
    mu_plus_sq = mu_plus**2  # (M, N)
    sab_curvature = T0 * ((curvature_H / k)[:, np.newaxis] * mu_plus_sq) @ power

    return np.maximum(sab_base + sab_curvature, 0.0)
