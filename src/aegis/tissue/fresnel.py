"""Fresnel power transmission coefficients for lossy dielectric half-spaces.

Numerically stable implementation using energy conservation: T = 1 - |r|^2.
The square-root branch for xi is selected so Re(xi) >= 0.
"""

from __future__ import annotations

import numpy as np

from aegis.constants import EPS_0


def n_complex(eps_r: float, sigma: float, freq_hz: float) -> complex:
    """Complex refractive index for a lossy non-magnetic medium.

    Parameters
    ----------
    eps_r
        Relative permittivity.
    sigma
        Conductivity (S/m).
    freq_hz
        Frequency (Hz).
    """
    omega = 2 * np.pi * freq_hz
    eps_complex = eps_r - 1j * sigma / (omega * EPS_0)
    n_tilde = np.sqrt(eps_complex)
    if np.real(n_tilde) < 0:
        n_tilde = -n_tilde
    return n_tilde


def fresnel_transmission(mu: np.ndarray, n_tilde: complex) -> tuple[np.ndarray, np.ndarray]:
    """Fresnel power transmission for TE (s) and TM (p) polarizations.

    Uses T = 1 - |r|^2 for numerical stability with lossy media.

    Parameters
    ----------
    mu
        cos(theta_i), the cosine of the incidence angle. Scalar or array.
    n_tilde
        Complex refractive index of the medium.

    Returns
    -------
    T_s, T_p
        TE and TM power transmission coefficients (real-valued).
    """
    mu = np.asarray(mu, dtype=complex)
    scalar_input = mu.ndim == 0
    mu = np.atleast_1d(mu)

    n2 = n_tilde**2
    xi = np.sqrt(n2 - 1 + mu**2)
    xi = np.where(np.real(xi) < 0, -xi, xi)

    r_s = (mu - xi) / (mu + xi)
    r_p = (n2 * mu - xi) / (n2 * mu + xi)

    T_s = np.real(1 - np.abs(r_s) ** 2)
    T_p = np.real(1 - np.abs(r_p) ** 2)

    # Grazing-incidence safeguard
    mu_real = np.real(mu)
    T_s = np.where(mu_real < 1e-10, 0.0, T_s)
    T_p = np.where(mu_real < 1e-10, 0.0, T_p)

    if scalar_input:
        return float(T_s[0]), float(T_p[0])
    return T_s, T_p


def fresnel_amplitude(mu: np.ndarray, n_tilde: complex) -> tuple[np.ndarray, np.ndarray]:
    """Fresnel amplitude transmission coefficients for TE (s) and TM (p).

    Returns complex coefficients t_s and t_p (not power).
    Used by the coherent dosimetry pipeline (Levels 7-8).

    Parameters
    ----------
    mu
        cos(theta_i), the cosine of the incidence angle. Scalar or array.
    n_tilde
        Complex refractive index of the medium.

    Returns
    -------
    t_s, t_p
        Complex TE and TM amplitude transmission coefficients.
    """
    mu = np.asarray(mu, dtype=complex)
    scalar_input = mu.ndim == 0
    mu = np.atleast_1d(mu)

    n2 = n_tilde**2
    xi = np.sqrt(n2 - 1 + mu**2)
    xi = np.where(np.real(xi) < 0, -xi, xi)

    t_s = 2 * mu / (mu + xi)
    t_p = 2 * n_tilde * mu / (n2 * mu + xi)

    if scalar_input:
        return complex(t_s[0]), complex(t_p[0])
    return t_s, t_p


def xi_from_mu(mu: np.ndarray, n_tilde: complex) -> np.ndarray:
    """Normal wave-vector component in tissue: xi = sqrt(n_tilde^2 - 1 + mu^2).

    Branch selected so Re(xi) >= 0. Returns k0*xi = beta - i*alpha,
    where alpha is the amplitude decay rate and beta the phase rate.

    Parameters
    ----------
    mu
        cos(theta_i). Scalar or array.
    n_tilde
        Complex refractive index.

    Returns
    -------
    xi
        Complex, same shape as mu.
    """
    mu = np.asarray(mu, dtype=complex)
    n2 = n_tilde**2
    xi = np.sqrt(n2 - 1 + mu**2)
    xi = np.where(np.real(xi) < 0, -xi, xi)
    return xi


def T0(n_tilde: complex) -> float:
    """Normal-incidence power transmission coefficient.

    T_0 = 4 Re(n) / |1 + n|^2
    """
    return float(4 * np.real(n_tilde) / abs(1 + n_tilde) ** 2)
