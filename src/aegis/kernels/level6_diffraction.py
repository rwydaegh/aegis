"""Level 6: Diffraction smoothing (ReLU -> physical GELU)."""

from __future__ import annotations

from aegis._array_backend import jit, xp
from aegis.constants import C_0
from aegis.kernels._base import fresnel_weights, physical_gelu


@jit
def level6_diffraction(normals, k_hat, power, n_tilde, T0, curvature_H, freq_hz):
    """Compute per-triangle S_ab with Fresnel + curvature + diffraction."""
    wavelength = C_0 / freq_hz
    k = 2.0 * xp.pi / wavelength

    mu = normals @ (-k_hat).T

    H_safe = xp.maximum(curvature_H, 0.0)
    sigma = xp.sqrt(xp.maximum(wavelength * H_safe / (4.0 * xp.pi), 0.0))

    mu_gelu = physical_gelu(mu, sigma)

    _T_s, _T_p, T_avg = fresnel_weights(mu, n_tilde)

    sab_base = (T_avg * mu_gelu) @ power

    gelu_sq = mu_gelu**2
    sab_curvature = T0 * ((H_safe / k)[:, None] * gelu_sq) @ power

    return xp.maximum(sab_base + sab_curvature, 0.0)
