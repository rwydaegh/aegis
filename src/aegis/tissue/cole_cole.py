"""4-pole Cole-Cole model for complex permittivity of biological tissues.

Implements the Gabriel (1996) parametric model used in the IT'IS v5.0 database.
Each tissue is described by 14 parameters: ef (high-frequency permittivity),
4 x (delta, tau, alpha) dispersion poles, and static conductivity sig.
"""

from __future__ import annotations

import numpy as np

from aegis.constants import EPS_0

# Tau unit multipliers for the four poles: ps, ns, us, ms
_TAU_UNITS = (1e-12, 1e-9, 1e-6, 1e-3)


def cole_cole_permittivity(freq_hz: float | np.ndarray, params: dict) -> complex:
    """Complex permittivity from the 4-pole Cole-Cole model.

    Parameters
    ----------
    freq_hz
        Frequency in Hz. Scalar or array.
    params
        Gabriel model parameters with keys:
        ef, del1..del4, tau1..tau4, alf1..alf4, sig.

    Returns
    -------
    Complex permittivity (eps_r - j*sigma/(omega*eps_0) combined).
    """
    omega = 2 * np.pi * freq_hz

    eps = complex(params["ef"], 0)

    for i in range(4):
        delta = params[f"del{i + 1}"]
        tau = params[f"tau{i + 1}"] * _TAU_UNITS[i]
        alpha = params[f"alf{i + 1}"]

        if delta != 0 and tau != 0:
            denom = 1 + (1j * omega * tau) ** (1 - alpha)
            eps += delta / denom

    if params["sig"] != 0 and omega != 0:
        eps -= 1j * params["sig"] / (omega * EPS_0)

    return eps


def debye_permittivity(
    freq_hz: float | np.ndarray,
    eps_inf: float,
    eps_static: float,
    sigma: float,
    tau_s: float,
) -> complex | np.ndarray:
    """Single-pole Debye permittivity model.

    Parameters
    ----------
    freq_hz : frequency in Hz (scalar or array)
    eps_inf : high-frequency permittivity limit
    eps_static : static (DC) permittivity
    sigma : static conductivity in S/m
    tau_s : relaxation time in seconds
    """
    omega = 2 * np.pi * np.asarray(freq_hz, dtype=np.float64)
    eps = eps_inf + (eps_static - eps_inf) / (1 + 1j * omega * tau_s)
    if sigma != 0:
        eps = eps - 1j * sigma / (omega * EPS_0)
    return eps
