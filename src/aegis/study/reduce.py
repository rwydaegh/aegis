"""Exposure reduction and the population CDF.

The headline per-person random variable is the time-averaged exposure over the
walk, expressed as a fraction of the ICNIRP 2020 limit. Above 6 GHz the relevant
basic restriction is the absorbed power density averaged over 4 cm^2 (sab_4cm2),
so the ICNIRP fraction takes a 4 cm^2-averaged S_ab density in W/m^2 (for example
``DosimetryResult.peak_sab_averaged``).
"""

from __future__ import annotations

import numpy as np

from aegis.compliance import ExposureScenario, icnirp_limits


def time_average(series) -> float:
    """Mean exposure over the walk."""
    series = np.asarray(series, dtype=float)
    if series.size == 0:
        return 0.0
    return float(series.mean())


def as_icnirp_fraction(
    sab_density_wm2,
    freq_hz=28e9,
    scenario=ExposureScenario.GENERAL_PUBLIC,
) -> float:
    """Express a 4 cm^2-averaged S_ab density as a fraction of the ICNIRP limit."""
    limits = icnirp_limits(scenario=scenario, freq_hz=freq_hz)
    if limits.sab_4cm2 is None:
        raise ValueError(f"No Sab limit below 6 GHz (freq_hz={freq_hz}); use a SAR limit instead")
    return float(sab_density_wm2) / limits.sab_4cm2


def population_cdf(samples):
    """Empirical CDF: return (sorted_samples, cumulative_fraction)."""
    samples = np.sort(np.asarray(samples, dtype=float))
    n = samples.size
    if n == 0:
        return samples, np.zeros(0)
    f = np.arange(1, n + 1) / n
    return samples, f
