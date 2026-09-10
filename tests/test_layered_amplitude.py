"""Analytic incident-amplitude and power checks for layered depth profiles."""

import numpy as np
import pytest

from aegis.constants import C_0, EPS_0, MU_0
from aegis.hotspot.layered_skin import Layer, solve_layered


@pytest.mark.parametrize("pol", ["TE", "TM"])
@pytest.mark.parametrize("theta", [0.0, 0.7, 1.1])
def test_air_profile_preserves_total_incident_amplitude(pol, theta):
    amplitude = 2.3
    air = Layer("air", 1.0, 0.0, np.inf)
    profile = solve_layered([air, air], 2.45e9, theta, pol, incident_amplitude=amplitude)
    np.testing.assert_allclose(profile.E_abs, amplitude, rtol=1e-9)
    np.testing.assert_array_equal(profile.sar, 0.0)
    assert profile.power_transmission == pytest.approx(1.0)


@pytest.mark.parametrize("pol", ["TE", "TM"])
@pytest.mark.parametrize("theta", [0.0, 0.7, 1.1])
def test_lossless_halfspace_matches_total_field_and_power_fresnel(pol, theta):
    amplitude = 2.3
    n = 2.0
    mu = np.cos(theta)
    cos_t = np.sqrt(1 - (np.sin(theta) / n) ** 2)
    transmission = 2 * mu / (mu + n * cos_t) if pol == "TE" else 2 * mu / (n * mu + cos_t)
    stack = [Layer("air", 1.0, 0.0, np.inf), Layer("dielectric", n**2, 0.0, np.inf)]
    profile = solve_layered(stack, 2.45e9, theta, pol, incident_amplitude=amplitude)
    np.testing.assert_allclose(profile.E_abs, amplitude * transmission, rtol=1e-9)
    expected_power = n * cos_t / mu * transmission**2
    assert profile.power_transmission == pytest.approx(expected_power, rel=1e-9)


@pytest.mark.parametrize("pol", ["TE", "TM"])
@pytest.mark.parametrize("theta", [0.0, 0.7, 1.1])
def test_halfspace_integrated_sar_matches_incident_normal_power(pol, theta):
    frequency = 2.45e9
    amplitude = 2.3
    tissue = Layer("tissue", 35.0, 2.0, np.inf, density=1050.0)
    stack = [Layer("air", 1.0, 0.0, np.inf), tissue]
    omega = 2 * np.pi * frequency
    epsilon = tissue.eps_r - 1j * tissue.sigma / (omega * EPS_0)
    alpha = -(omega / C_0 * np.sqrt(epsilon - np.sin(theta) ** 2)).imag
    profile = solve_layered(stack, frequency, theta, pol, incident_amplitude=amplitude, depth_max=8 / alpha, n_z=20001)
    absorbed_per_area = np.trapezoid(profile.sar * tissue.density, profile.z)
    incident_normal_power = amplitude**2 / (2 * np.sqrt(MU_0 / EPS_0)) * np.cos(theta)
    expected = incident_normal_power * profile.power_transmission * (1 - np.exp(-16))
    assert absorbed_per_area == pytest.approx(expected, rel=1e-6)
