"""Level 6: Diffraction smoothing (ReLU -> physical GELU)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import jit, xp
from aegis.constants import C_0
from aegis.kernels._base import fresnel_weights, physical_gelu


@jit
def level6_diffraction(
    normals: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    power: NDArray[np.floating],
    n_tilde: complex | NDArray[np.complexfloating],
    T0: float,
    curvature_H: NDArray[np.floating],
    freq_hz: float,
) -> NDArray[np.floating]:
    """Compute per-triangle S_ab with Fresnel + curvature + diffraction."""
    wavelength = C_0 / freq_hz
    # Floor k to avoid division by near-zero at very low frequencies
    k = xp.maximum(2.0 * xp.pi / wavelength, 1e-6)

    mu = normals @ (-k_hat).T

    H_safe = xp.maximum(curvature_H, 0.0)
    # Floor sigma to avoid derivative discontinuity at H=0 (for autodiff)
    sigma = xp.sqrt(xp.maximum(wavelength * H_safe / (4.0 * xp.pi), 1e-20))

    mu_gelu = physical_gelu(mu, sigma)

    _T_s, _T_p, T_avg = fresnel_weights(mu, n_tilde)

    sab_base = (T_avg * mu_gelu) @ power

    gelu_sq = mu_gelu**2
    sab_curvature = T0 * ((H_safe / k)[:, None] * gelu_sq) @ power

    return xp.maximum(sab_base + sab_curvature, 0.0)
