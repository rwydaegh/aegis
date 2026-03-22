"""Unified spatial kernel with composable physics corrections.

Computes per-triangle S_ab from the general incoherent formula:

    S_ab = T(mu, q) * g(mu, sigma) @ power + T0 * (H/k) * g(mu, sigma)^2 @ power

where:
    T = T_avg + (q/2)*DeltaT  (with polarisation) or T_avg (without)
    g = GELU(mu, sigma)        (with diffraction)  or ReLU(mu) (without)
    curvature term present or absent

See theory/composability_analysis.md for derivation and limiting cases.
"""

from __future__ import annotations

from aegis._array_backend import jit, xp
from aegis.constants import C_0
from aegis.kernels._base import fresnel_weights, incidence_geometry, physical_gelu


@jit(static_argnames=("fresnel", "polarisation", "curvature", "diffraction"))
def spatial_kernel(
    normals,
    k_hat,
    power,
    n_tilde,
    T0,
    freq_hz,
    *,
    fresnel: bool = True,
    polarisation: bool = False,
    q: float = 0.0,
    curvature: bool = False,
    diffraction: bool = False,
    curvature_H=None,
):
    """Compute per-triangle S_ab with composable physics corrections.

    Parameters
    ----------
    normals : (M, 3) unit outward normals
    k_hat : (N, 3) incident directions
    power : (N,) per-path power density [W/m^2]
    n_tilde : complex refractive index
    T0 : normal-incidence transmission coefficient
    freq_hz : frequency [Hz]
    fresnel : use angle-dependent T_avg(mu) instead of constant T0
    polarisation : enable polarisation correction (requires fresnel=True)
    q : TM excess parameter (scalar or (N,) array), used if polarisation=True
    curvature : enable curvature correction (requires curvature_H)
    diffraction : enable diffraction smoothing (requires curvature_H)
    curvature_H : (M,) twice mean curvature per triangle [1/m]

    Returns
    -------
    sab : (M,) absorbed power density per triangle [W/m^2]
    """
    if (curvature or diffraction) and curvature_H is None:
        raise ValueError("curvature_H is required when curvature=True or diffraction=True")

    mu, mu_plus = incidence_geometry(normals, k_hat)

    # Fresnel factor
    if fresnel:
        T_s, T_p, T_avg = fresnel_weights(mu, n_tilde)
        if polarisation:
            DeltaT = T_p - T_s
            T = T_avg + 0.5 * q * DeltaT
        else:
            T = T_avg
    else:
        T = T0  # constant, broadcasts over (M, N)

    # Activation: ReLU or GELU (with diffraction)
    if diffraction:
        wavelength = C_0 / freq_hz
        H_safe = xp.maximum(curvature_H, 0.0)
        sigma = xp.sqrt(xp.maximum(wavelength * H_safe / (4.0 * xp.pi), 0.0))
        g = physical_gelu(mu, sigma)
    else:
        g = mu_plus

    sab = (T * g) @ power

    # Curvature correction: additive perturbative term
    if curvature:
        k = 2.0 * xp.pi * freq_hz / C_0
        H_for_curv = xp.maximum(curvature_H, 0.0) if not diffraction else H_safe
        g_sq = g**2
        sab_curvature = T0 * ((H_for_curv / k)[:, None] * g_sq) @ power
        sab = sab + sab_curvature

    if curvature or diffraction:
        sab = xp.maximum(sab, 0.0)

    return sab
