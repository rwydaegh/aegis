"""Frequency-domain visualization helpers."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from aegis.compliance import ICNIRP_2020
from aegis.tissue.database import get_tissue_spectrum


def plot_frequency_sweep(
    freqs_hz: np.ndarray | list[float],
    peak_sab_values: np.ndarray | list[float],
    *,
    limit: float = ICNIRP_2020.sab_peak,
) -> Any:
    """Plot peak S_ab versus frequency with ICNIRP limit reference.

    Parameters
    ----------
    freqs_hz
        Frequencies in Hz.
    peak_sab_values
        Peak S_ab at each frequency [W/m^2].
    limit
        Reference limit [W/m^2], drawn as a horizontal dashed line.
    """
    f_hz = np.asarray(freqs_hz, dtype=float)
    sab = np.asarray(peak_sab_values, dtype=float)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(f_hz * 1e-9, sab, color="C0", marker="o", markersize=3, linewidth=1.2)
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel(r"Peak $S_{\mathrm{ab}}$ (W/m$^2$)")
    ax.set_yscale("log")
    ax.axhline(limit, color="red", linestyle="--", linewidth=1.0, label=f"Limit ({limit:g} W/m²)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    return fig


def plot_tissue_spectrum(
    tissue_name: str,
    freq_min_hz: float,
    freq_max_hz: float,
    *,
    n_points: int = 200,
) -> Any:
    """Plot relative permittivity and conductivity versus frequency (Cole-Cole via IT'IS).

    Requires ``itis_v5.db`` at runtime (see ``aegis.tissue.database.find_database``).

    Parameters
    ----------
    tissue_name
        IT'IS tissue name (e.g. "Skin", "Muscle").
    freq_min_hz, freq_max_hz
        Frequency band in Hz.
    n_points
        Number of samples along the frequency axis.
    """
    freqs = np.linspace(freq_min_hz, freq_max_hz, n_points, dtype=float)
    spectrum = get_tissue_spectrum(tissue_name, freqs)
    eps_r = spectrum["eps_r"]
    sigma = spectrum["sigma"]

    fig, ax_left = plt.subplots(figsize=(8, 4.5))
    ax_left.plot(freqs * 1e-9, eps_r, color="C0", label=r"$\varepsilon_r'$")
    ax_left.set_xlabel("Frequency (GHz)")
    ax_left.set_ylabel(r"$\varepsilon_r'$", color="C0")
    ax_left.tick_params(axis="y", labelcolor="C0")

    ax_right = ax_left.twinx()
    ax_right.plot(freqs * 1e-9, sigma, color="C1", label=r"$\sigma$ (S/m)")
    ax_right.set_ylabel(r"$\sigma$ (S/m)", color="C1")
    ax_right.tick_params(axis="y", labelcolor="C1")

    fig.suptitle(f"{tissue_name}: dielectric spectrum")
    fig.tight_layout()
    return fig
