from __future__ import annotations

import numpy as np

from semantic_twin.materials.roughness import roughness_to_scattering_coefficient, wavelength_m
from semantic_twin.materials.mmwave import (
    coherent_amplitude_retention,
    feature_electrical_size,
    phase_standard_deviation_rad,
)


def test_28_ghz_wavelength_is_about_one_centimetre() -> None:
    assert np.isclose(wavelength_m(28e9), 0.0107068735)


def test_phase_uncertainty_scales_with_frequency() -> None:
    low = phase_standard_deviation_rad(0.002, 28e9)
    high = phase_standard_deviation_rad(0.002, 60e9)
    assert high > low
    assert coherent_amplitude_retention(0.002, 60e9) < coherent_amplitude_retention(0.002, 28e9)


def test_bollard_is_electrically_large_at_mmwave() -> None:
    assert feature_electrical_size(0.1, 28e9) > 9.0


def test_roughness_closure_partitions_power_for_sionna() -> None:
    smooth = roughness_to_scattering_coefficient(0.0, np.cos(np.radians(30.0)), 60e9)
    rough = roughness_to_scattering_coefficient(0.002, np.cos(np.radians(30.0)), 60e9)
    assert smooth == 0.0
    assert 0.0 < rough < 1.0
