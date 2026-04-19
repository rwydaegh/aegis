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

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import JAX_AVAILABLE, jit, xp
from aegis.constants import C_0
from aegis.kernels._base import fresnel_weights, incidence_geometry, physical_gelu

# Maximum number of (M, N) float64 elements before we split paths into chunks.
# 50M elements ~ 400 MB per intermediate array. With ~4 live intermediates
# (mu, T, g, T*g) the peak is ~1.6 GB, which fits comfortably in 4+ GB RAM.
# Below this threshold the kernel runs unchunked (zero overhead).
_MAX_MN_ELEMENTS = 50_000_000


@jit(static_argnames=("fresnel", "polarisation", "curvature", "diffraction"))
def _spatial_kernel_unbatched(
    normals: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    power: NDArray[np.floating],
    n_tilde: complex | NDArray[np.complexfloating],
    T0: float,
    freq_hz: float,
    *,
    fresnel: bool = True,
    polarisation: bool = False,
    q: float | NDArray[np.floating] = 0.0,
    curvature: bool = False,
    diffraction: bool = False,
    curvature_H: NDArray[np.floating] | None = None,
) -> NDArray[np.floating]:
    """Core spatial kernel operating on all paths at once.

    This is the inner computation. For large M*N, use ``spatial_kernel``
    which automatically chunks over paths to bound memory usage.
    """
    mu, mu_plus = incidence_geometry(normals, k_hat)

    # Fresnel factor
    t_factor: float | NDArray[np.floating]
    if fresnel:
        T_s, T_p, T_avg = fresnel_weights(mu, n_tilde)
        if polarisation:
            DeltaT = T_p - T_s
            t_factor = T_avg + 0.5 * q * DeltaT
        else:
            t_factor = T_avg
    else:
        t_factor = T0  # constant, broadcasts over (M, N)

    # Activation: ReLU or GELU (with diffraction)
    H_safe: NDArray[np.floating] | None = None
    if diffraction:
        wavelength = C_0 / freq_hz
        assert curvature_H is not None, "diffraction=True requires curvature_H"
        H_safe = xp.maximum(curvature_H, 0.0)
        sigma = xp.sqrt(xp.maximum(wavelength * H_safe / (4.0 * xp.pi), 1e-20))
        g = physical_gelu(mu, sigma)
    else:
        g = mu_plus

    sab = (t_factor * g) @ power

    # Curvature correction: additive perturbative term
    if curvature:
        k = xp.maximum(2.0 * xp.pi * freq_hz / C_0, 1e-6)
        if diffraction:
            assert H_safe is not None
            H_for_curv = H_safe
        else:
            assert curvature_H is not None, "curvature=True requires curvature_H"
            H_for_curv = xp.maximum(curvature_H, 0.0)
        # einsum avoids two (M, N) intermediates (g**2 and H-scaled g**2)
        g_sq_power = xp.einsum("mn,mn,n->m", g, g, power)
        sab_curvature = T0 * (H_for_curv / k) * g_sq_power
        sab = sab + sab_curvature

    return sab


def spatial_kernel(
    normals: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    power: NDArray[np.floating],
    n_tilde: complex | NDArray[np.complexfloating],
    T0: float,
    freq_hz: float,
    *,
    fresnel: bool = True,
    polarisation: bool = False,
    q: float | NDArray[np.floating] = 0.0,
    curvature: bool = False,
    diffraction: bool = False,
    curvature_H: NDArray[np.floating] | None = None,
) -> NDArray[np.floating]:
    """Compute per-triangle S_ab with composable physics corrections.

    Automatically chunks over paths (N dimension) when M*N exceeds
    ``_MAX_MN_ELEMENTS`` to prevent out-of-memory on large scenes.
    The result is mathematically identical to the unchunked version
    because both the main term ``(T * g) @ power`` and the curvature
    einsum decompose as sums over independent path subsets.

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
    if polarisation and not fresnel:
        raise ValueError("polarisation correction requires fresnel=True")
    if (curvature or diffraction) and curvature_H is None:
        raise ValueError("curvature_H is required when curvature=True or diffraction=True")

    M = normals.shape[0]
    N = k_hat.shape[0]

    # Fast path: small enough to run in one shot
    if M * N <= _MAX_MN_ELEMENTS or JAX_AVAILABLE:
        sab = _spatial_kernel_unbatched(
            normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            fresnel=fresnel,
            polarisation=polarisation,
            q=q,
            curvature=curvature,
            diffraction=diffraction,
            curvature_H=curvature_H,
        )
    else:
        # Chunked path: split along N to bound peak memory
        chunk_size = max(_MAX_MN_ELEMENTS // M, 1)
        sab = np.zeros(M, dtype=np.float64)

        for start in range(0, N, chunk_size):
            end = min(start + chunk_size, N)
            k_chunk = k_hat[start:end]
            p_chunk = power[start:end]
            q_chunk: float | NDArray[np.floating] = q[start:end] if isinstance(q, np.ndarray) and q.ndim > 0 else q

            chunk_sab = _spatial_kernel_unbatched(
                normals,
                k_chunk,
                p_chunk,
                n_tilde,
                T0,
                freq_hz,
                fresnel=fresnel,
                polarisation=polarisation,
                q=q_chunk,
                curvature=curvature,
                diffraction=diffraction,
                curvature_H=curvature_H,
            )
            sab = sab + chunk_sab

    # Clamp the final summed result. Clamping per-chunk would produce
    # chunk-size-dependent answers because partial sums can be negative while
    # the full sum is positive (or vice versa).
    if curvature or diffraction:
        sab = xp.maximum(sab, 0.0)

    return sab
