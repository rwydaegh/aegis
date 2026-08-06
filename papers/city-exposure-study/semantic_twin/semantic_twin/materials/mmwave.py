"""Frequency-scaled quality metrics for propagation-scene reconstruction.

How well a reconstruction has to be built is a question about wavelengths, and
these are the four scalings that answer it: how much phase a path length error
costs, how much of a phasor survives it, how large a feature is in wavelengths,
and how much to discount an image whose projected footprint is coarser than the
feature it claims to resolve.

The surface roughness closure used to live here as well. It is a material
property, so it now lives in :mod:`semantic_twin.materials.roughness` alongside
the prior that supplies its RMS height, and the names below are re-exported for
callers that have not moved yet.
"""

from __future__ import annotations

import numpy as np

from .roughness import (
    SPEED_OF_LIGHT_M_S,
    rayleigh_roughness_parameter,
    rayleigh_smooth_threshold_m,
    roughness_to_scattering_coefficient,
    specular_power_fraction,
    wavelength_m,
)

__all__ = [
    "SPEED_OF_LIGHT_M_S",
    "coherent_amplitude_retention",
    "feature_electrical_size",
    "phase_standard_deviation_rad",
    "rayleigh_roughness_parameter",
    "rayleigh_smooth_threshold_m",
    "resolution_quality",
    "roughness_to_scattering_coefficient",
    "specular_power_fraction",
    "wavelength_m",
]


def phase_standard_deviation_rad(
    path_length_standard_deviation_m: float | np.ndarray,
    frequency_hz: float | np.ndarray,
) -> np.ndarray:
    """One-sigma phase error caused by uncertain path length."""
    return 2.0 * np.pi * np.asarray(path_length_standard_deviation_m) / wavelength_m(frequency_hz)


def coherent_amplitude_retention(
    path_length_standard_deviation_m: float | np.ndarray,
    frequency_hz: float | np.ndarray,
) -> np.ndarray:
    """Expected phasor magnitude for zero-mean Gaussian path error."""
    phase_sigma = phase_standard_deviation_rad(path_length_standard_deviation_m, frequency_hz)
    return np.exp(-0.5 * phase_sigma**2)


def feature_electrical_size(feature_size_m: float | np.ndarray, frequency_hz: float | np.ndarray) -> np.ndarray:
    """Physical feature size measured in wavelengths."""
    return np.asarray(feature_size_m, dtype=np.float64) / wavelength_m(frequency_hz)


def resolution_quality(
    footprint_m: float | np.ndarray,
    target_feature_m: float | np.ndarray,
) -> np.ndarray:
    """Smoothly discount image evidence whose projected footprint is too large."""
    footprint = np.asarray(footprint_m, dtype=np.float64)
    target = np.asarray(target_feature_m, dtype=np.float64)
    if np.any(target <= 0.0):
        raise ValueError("target feature size must be positive")
    ratio = footprint / target
    return np.exp(-(ratio**2))
