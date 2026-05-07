"""
Shared Fresnel / material helpers used across scripts.

This module is intentionally tiny and numerically stable. It mirrors the
"correctness anchor" implementation in `scripts/verify_fresnel.py`:

  - Fresnel power transmission is computed via energy conservation:
        T = 1 - |r|^2
  - The square-root branch for xi is selected so Re(xi) >= 0.

Keep this module dependency-light: numpy only.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

# Physical constant: vacuum permittivity (F/m)
EPS_0 = 8.854187817e-12


def n_complex(eps_r: float, sigma: float, freq_hz: float) -> complex:
    """
    Complex refractive index for a (potentially lossy) non-magnetic medium.

    Matches `get_n_complex()` in `scripts/verify_fresnel.py`.
    """
    omega = 2 * np.pi * freq_hz
    eps_complex = eps_r - 1j * sigma / (omega * EPS_0)
    n_tilde = np.sqrt(eps_complex)
    if np.real(n_tilde) < 0:
        n_tilde = -n_tilde
    return n_tilde


def fresnel_transmission(mu: np.ndarray, n_tilde: complex) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fresnel *power* transmission for TE/TM, using T = 1 - |r|^2.

    Parameters
    ----------
    mu
        cos(theta_i). Can be scalar or array-like.
    n_tilde
        Complex refractive index.

    Returns
    -------
    T_s, T_p
        TE/TM power transmission coefficients (real-valued).
    """
    mu = np.asarray(mu, dtype=complex)
    scalar_input = mu.ndim == 0
    mu = np.atleast_1d(mu)

    n2 = n_tilde**2
    xi = np.sqrt(n2 - 1 + mu**2)
    xi = np.where(np.real(xi) < 0, -xi, xi)

    r_s = (mu - xi) / (mu + xi)
    r_p = (n2 * mu - xi) / (n2 * mu + xi)

    T_s = 1 - np.abs(r_s) ** 2
    T_p = 1 - np.abs(r_p) ** 2

    # Real-valued power transmission
    T_s = np.real(T_s)
    T_p = np.real(T_p)

    # Grazing-incidence safeguard (keeps behavior consistent with APD scripts)
    mu_real = np.real(mu)
    T_s = np.where(mu_real < 1e-10, 0.0, T_s)
    T_p = np.where(mu_real < 1e-10, 0.0, T_p)

    if scalar_input:
        return float(T_s[0]), float(T_p[0])
    return T_s, T_p

