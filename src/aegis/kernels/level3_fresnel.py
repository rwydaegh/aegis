"""Level 3: Exact Fresnel spatial map."""

from __future__ import annotations

from aegis._array_backend import jit
from aegis.kernels._base import fresnel_weights, incidence_geometry


@jit
def level3_fresnel(normals, k_hat, power, n_tilde):
    """Compute per-triangle S_ab with angle-dependent Fresnel transmission."""
    mu, mu_plus = incidence_geometry(normals, k_hat)
    _T_s, _T_p, T_avg = fresnel_weights(mu, n_tilde)
    sab = (T_avg * mu_plus) @ power
    return sab
