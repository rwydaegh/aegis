"""Level 6: Diffraction smoothing (ReLU -> physical GELU -> Fock)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import jit, xp
from aegis.constants import C_0
from aegis.kernels._base import fresnel_weights, physical_gelu
from aegis.kernels.fock import fock_local
from aegis.kernels.spatial import _resolve_diffraction_model


@jit(static_argnames=("diffraction_model", "q_F_s", "q_F_h"))
def level6_diffraction(
    normals: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    power: NDArray[np.floating],
    n_tilde: complex | NDArray[np.complexfloating],
    T0: float,
    curvature_H: NDArray[np.floating],
    freq_hz: float,
    *,
    diffraction_model: str | None = None,
    fock_R: NDArray[np.floating] | None = None,
    q_F_s: complex | None = None,
    q_F_h: complex | None = None,
) -> NDArray[np.floating]:
    """Compute per-triangle S_ab with Fresnel + curvature + diffraction.

    The shadow-edge gate is selected by ``diffraction_model``: ``"none"`` is
    exact ReLU, ``"gelu"`` is the legacy physical-GELU smoothing (the historical
    default), ``"fock"`` is the smooth-convex-body (Fock) gate (requires
    ``fock_R`` from ``geometry.curvature.fock_radius``). When
    ``diffraction_model`` is ``None`` the gate defaults to ``"gelu"`` to preserve
    the pre-selector behaviour of this kernel.
    """
    # This kernel has always applied the GELU gate, so the legacy default is
    # "gelu" (diffraction=True), mirroring spatial.py's bool mapping.
    model = _resolve_diffraction_model(True, diffraction_model)

    wavelength = C_0 / freq_hz
    # Floor k to avoid division by near-zero at very low frequencies
    k = xp.maximum(2.0 * xp.pi / wavelength, 1e-6)

    mu = normals @ (-k_hat).T

    H_safe = xp.maximum(curvature_H, 0.0)

    # Activation gate: ReLU ("none"), GELU smoothing ("gelu"), or Fock ("fock").
    if model == "none":
        g = xp.maximum(mu, 0.0)
    elif model == "gelu":
        # Floor sigma to avoid derivative discontinuity at H=0 (for autodiff)
        sigma = xp.sqrt(xp.maximum(wavelength * H_safe / (4.0 * xp.pi), 1e-20))
        g = physical_gelu(mu, sigma)
    else:  # "fock"
        if fock_R is None:
            raise ValueError("fock_R is required when diffraction_model='fock'")
        # Incoherent, no incident polarisation state: equal TE/TM power split.
        R = fock_R[:, None] if fock_R.ndim == 1 else fock_R
        g = fock_local(mu, R, freq_hz, 0.5, 0.5, q_F_s, q_F_h)

    _T_s, _T_p, T_avg = fresnel_weights(mu, n_tilde)

    sab_base = (T_avg * g) @ power

    g_sq = g**2
    sab_curvature = T0 * ((H_safe / k)[:, None] * g_sq) @ power

    return xp.maximum(sab_base + sab_curvature, 0.0)
