"""Frequency-scaled quality metrics for propagation-scene reconstruction."""

from __future__ import annotations

import numpy as np

SPEED_OF_LIGHT_M_S = 299_792_458.0


def wavelength_m(frequency_hz: float | np.ndarray) -> np.ndarray:
    frequency = np.asarray(frequency_hz, dtype=np.float64)
    if np.any(frequency <= 0.0):
        raise ValueError("frequency must be positive")
    return SPEED_OF_LIGHT_M_S / frequency


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


def rayleigh_roughness_parameter(
    rms_height_m: float | np.ndarray,
    incidence_cosine: float | np.ndarray,
    frequency_hz: float | np.ndarray,
) -> np.ndarray:
    """Dimensionless surface roughness relative to wavelength and incidence."""
    cosine = np.clip(np.asarray(incidence_cosine, dtype=np.float64), 0.0, 1.0)
    return 4.0 * np.pi * np.asarray(rms_height_m) * cosine / wavelength_m(frequency_hz)


def roughness_to_scattering_coefficient(
    rms_height_m: float | np.ndarray,
    incidence_cosine: float | np.ndarray,
    frequency_hz: float | np.ndarray,
) -> np.ndarray:
    """Map Gaussian roughness to Sionna's diffuse amplitude coefficient.

    The coherent reflected power fraction is approximated as ``exp(-g**2)``,
    where ``g`` is the Rayleigh roughness parameter. The remaining reflected
    power is assigned to Sionna's diffuse component, whose power fraction is
    ``S**2``. This is an engineering closure, not an ITU-R P.2040 parameter.
    """
    g = rayleigh_roughness_parameter(rms_height_m, incidence_cosine, frequency_hz)
    return np.sqrt(np.maximum(0.0, -np.expm1(-(g**2))))


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
