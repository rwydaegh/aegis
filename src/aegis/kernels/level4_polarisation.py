"""Level 4: Polarisation-aware Fresnel map."""

from __future__ import annotations

from aegis._array_backend import jit
from aegis.kernels._base import fresnel_weights, incidence_geometry


@jit
def level4_polarisation(normals, k_hat, power, n_tilde, q=0.0):
    """Compute per-triangle S_ab with polarisation correction."""
    mu, mu_plus = incidence_geometry(normals, k_hat)
    T_s, T_p, T_avg = fresnel_weights(mu, n_tilde)
    DeltaT = T_p - T_s
    T_eff = T_avg + 0.5 * q * DeltaT
    sab = (T_eff * mu_plus) @ power
    return sab
