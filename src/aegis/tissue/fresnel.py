"""Fresnel power transmission coefficients for lossy dielectric half-spaces.

Numerically stable implementation using energy conservation: T = 1 - |r|^2.
The square-root branch for xi is selected so Re(xi) >= 0.
"""

from __future__ import annotations

import numpy as np

from aegis._array_backend import xp
from aegis.constants import EPS_0


def n_complex(eps_r: float, sigma: float, freq_hz: float) -> complex:
    """Complex refractive index. Scalar-only, not JIT-traced."""
    omega = 2 * np.pi * freq_hz
    eps_complex = eps_r - 1j * sigma / (omega * EPS_0)
    n_tilde = np.sqrt(eps_complex)
    if np.real(n_tilde) < 0:
        n_tilde = -n_tilde
    return n_tilde


def _fresnel_core(mu, n_tilde):
    """Core Fresnel computation on xp arrays. JIT-safe (no Python control flow).

    Parameters
    ----------
    mu : xp array, shape (...), complex dtype
        Cosine of incidence angle. Must already be an xp array.

    Returns
    -------
    r_s, r_p : complex arrays (amplitude reflection)
    T_s, T_p : real arrays (power transmission)
    t_s, t_p : complex arrays (amplitude transmission)
    """
    n2 = n_tilde**2
    xi = xp.sqrt(n2 - 1 + mu**2)
    xi = xp.where(xp.real(xi) < 0, -xi, xi)

    r_s = (mu - xi) / (mu + xi)
    r_p = (n2 * mu - xi) / (n2 * mu + xi)

    T_s = xp.real(1 - xp.abs(r_s) ** 2)
    T_p = xp.real(1 - xp.abs(r_p) ** 2)

    mu_real = xp.real(mu)
    T_s = xp.where(mu_real < 1e-10, 0.0, T_s)
    T_p = xp.where(mu_real < 1e-10, 0.0, T_p)

    t_s = 2 * mu / (mu + xi)
    t_p = 2 * n_tilde * mu / (n2 * mu + xi)

    return r_s, r_p, T_s, T_p, t_s, t_p


def fresnel_transmission(mu, n_tilde):
    """Fresnel power transmission for TE and TM polarizations.

    Convenience wrapper with scalar support. NOT called from JIT boundaries.
    JIT'd kernels use _fresnel_core via _base.py::fresnel_weights instead.
    """
    mu = np.asarray(mu, dtype=complex)
    scalar_input = mu.ndim == 0
    mu = np.atleast_1d(mu)

    _, _, T_s, T_p, _, _ = _fresnel_core(xp.asarray(mu), n_tilde)

    T_s = np.asarray(T_s)
    T_p = np.asarray(T_p)

    if scalar_input:
        return float(T_s[0]), float(T_p[0])
    return T_s, T_p


def fresnel_reflection(mu, n_tilde):
    """Fresnel amplitude reflection coefficients.

    Convenience wrapper with scalar support. NOT called from JIT boundaries.
    """
    mu = np.asarray(mu, dtype=complex)
    scalar_input = mu.ndim == 0
    mu = np.atleast_1d(mu)

    r_s, r_p, _, _, _, _ = _fresnel_core(xp.asarray(mu), n_tilde)

    r_s = np.asarray(r_s)
    r_p = np.asarray(r_p)

    if scalar_input:
        return complex(r_s[0]), complex(r_p[0])
    return r_s, r_p


def fresnel_amplitude(mu, n_tilde):
    """Fresnel amplitude transmission coefficients.

    Convenience wrapper with scalar support. NOT called from JIT boundaries.
    JIT'd coherent kernels call _fresnel_core or use the fresnel_operator module.
    """
    mu = np.asarray(mu, dtype=complex)
    scalar_input = mu.ndim == 0
    mu = np.atleast_1d(mu)

    _, _, _, _, t_s, t_p = _fresnel_core(xp.asarray(mu), n_tilde)

    t_s = np.asarray(t_s)
    t_p = np.asarray(t_p)

    if scalar_input:
        return complex(t_s[0]), complex(t_p[0])
    return t_s, t_p


def xi_from_mu(mu, n_tilde):
    """Normal wave-vector component in tissue. Uses xp, JIT-safe."""
    mu = xp.asarray(mu, dtype=complex)
    n2 = n_tilde**2
    xi = xp.sqrt(n2 - 1 + mu**2)
    xi = xp.where(xp.real(xi) < 0, -xi, xi)
    return xi


def T0(n_tilde: complex) -> float:
    """Normal-incidence power transmission."""
    denom = abs(1 + n_tilde) ** 2
    if denom == 0:
        raise ValueError(f"Cannot compute T0: |1 + n_tilde|^2 = 0 for n_tilde={n_tilde}")
    return float(4 * np.real(n_tilde) / denom)
