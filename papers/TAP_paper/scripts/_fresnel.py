"""
Shared Fresnel / material helpers used across TAP paper scripts.

This module is intentionally dependency-light and self-contained so the
PaperMaker instance can regenerate its figures without importing code from
outside this directory.
"""

from __future__ import annotations

import sqlite3
import struct
from pathlib import Path
from typing import Tuple

import numpy as np


EPS_0 = 8.854187817e-12
C_0 = 299792458.0


def find_itis_database() -> Path:
    """Return the local IT'IS v5 database bundled with this paper instance."""
    for path in (
        Path(__file__).resolve().parent.parent / "data" / "itis_v5.db",
        Path(__file__).resolve().parent / "itis_v5.db",
    ):
        if path.exists():
            return path
    raise FileNotFoundError(
        "Could not find local itis_v5.db in TAP_paper/data or TAP_paper/scripts"
    )


def get_gabriel_params(tissue_name: str = "Skin") -> dict | None:
    """Extract Gabriel 4-Cole-Cole parameters from the local IT'IS database."""
    conn = sqlite3.connect(str(find_itis_database()))
    cur = conn.cursor()
    cur.execute("SELECT prop_id FROM properties WHERE name = ?", ("Gabriel Parameters",))
    prop_result = cur.fetchone()
    if not prop_result:
        conn.close()
        return None

    cur.execute(
        """
        SELECT m.mat_id, v.vals
        FROM materials m
        JOIN vectors v ON m.mat_id = v.mat_id
        WHERE m.name = ? AND v.prop_id = ?
        LIMIT 1
        """,
        (tissue_name, prop_result[0]),
    )
    result = cur.fetchone()
    conn.close()
    if not result:
        return None

    blob = result[1]
    if len(blob) < 14 * 8:
        return None
    values = struct.unpack("d" * 14, blob[: 14 * 8])
    return {
        "ef": values[0],
        "del1": values[1],
        "tau1": values[2],
        "alf1": values[3],
        "del2": values[4],
        "tau2": values[5],
        "alf2": values[6],
        "del3": values[7],
        "tau3": values[8],
        "alf3": values[9],
        "del4": values[10],
        "tau4": values[11],
        "alf4": values[12],
        "sig": values[13],
    }


def cole_cole_permittivity(freq_hz, params: dict):
    """Complex relative permittivity from IT'IS Gabriel parameters."""
    freq_hz = np.asarray(freq_hz, dtype=float)
    omega = 2 * np.pi * freq_hz
    eps = np.asarray(params["ef"], dtype=complex) + np.zeros_like(freq_hz, dtype=complex)
    tau_units = [1e-12, 1e-9, 1e-6, 1e-3]
    for i, tau_unit in enumerate(tau_units, start=1):
        delta = params[f"del{i}"]
        tau = params[f"tau{i}"] * tau_unit
        alpha = params[f"alf{i}"]
        if delta != 0 and tau != 0:
            eps += delta / (1 + (1j * omega * tau) ** (1 - alpha))
    eps -= 1j * params["sig"] / (omega * EPS_0)
    return eps


def get_tissue_spectrum(tissue_name: str, freqs_hz) -> dict[str, np.ndarray]:
    """Return local IT'IS-derived n, kappa, and T0 arrays for a tissue."""
    freqs = np.asarray(freqs_hz, dtype=float)
    params = get_gabriel_params(tissue_name)
    if params is None:
        raise ValueError(f"Missing Gabriel parameters for {tissue_name!r}")

    eps = cole_cole_permittivity(freqs, params)
    n_tilde = np.sqrt(eps)
    n_tilde = np.where(np.real(n_tilde) < 0, -n_tilde, n_tilde)
    n = np.real(n_tilde)
    kappa = -np.imag(n_tilde)
    T0 = 4 * n / ((1 + n) ** 2 + kappa ** 2)
    return {"n": n, "kappa": kappa, "T0": T0}


def n_complex(eps_r: float, sigma: float, freq_hz: float) -> complex:
    """Complex refractive index for a lossy non-magnetic medium."""
    omega = 2 * np.pi * freq_hz
    eps_complex = eps_r - 1j * sigma / (omega * EPS_0)
    n_tilde = np.sqrt(eps_complex)
    if np.real(n_tilde) < 0:
        n_tilde = -n_tilde
    return n_tilde


def fresnel_transmission(mu: np.ndarray, n_tilde: complex) -> Tuple[np.ndarray, np.ndarray]:
    """Fresnel power transmission for TE/TM, using ``T = 1 - |r|^2``."""
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

    mu_real = np.real(mu)
    T_s = np.where(mu_real < 1e-10, 0.0, T_s)
    T_p = np.where(mu_real < 1e-10, 0.0, T_p)

    if scalar_input:
        return float(T_s[0]), float(T_p[0])
    return T_s, T_p
