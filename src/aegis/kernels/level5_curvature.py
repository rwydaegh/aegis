"""Level 5: Curvature correction."""

from __future__ import annotations

from aegis._array_backend import jit, xp
from aegis.constants import C_0
from aegis.kernels._base import fresnel_weights, incidence_geometry


@jit
def level5_curvature(normals, k_hat, power, n_tilde, T0, curvature_H, freq_hz):
    """Compute per-triangle S_ab with Fresnel + curvature correction."""
    # Floor k to avoid division by near-zero at very low frequencies
    k = xp.maximum(2.0 * xp.pi * freq_hz / C_0, 1e-6)

    mu, mu_plus = incidence_geometry(normals, k_hat)
    _T_s, _T_p, T_avg = fresnel_weights(mu, n_tilde)
    sab_base = (T_avg * mu_plus) @ power

    mu_plus_sq = mu_plus**2
    sab_curvature = T0 * ((curvature_H / k)[:, None] * mu_plus_sq) @ power

    return xp.maximum(sab_base + sab_curvature, 0.0)
