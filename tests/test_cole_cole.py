"""Tests for the 4-pole Cole-Cole model."""

import numpy as np
import pytest

from aegis.tissue.cole_cole import cole_cole_permittivity

# Gabriel (1996) skin parameters (from IT'IS v5.0)
SKIN_PARAMS = {
    "ef": 4.0,
    "del1": 32.0,
    "tau1": 7.23,
    "alf1": 0.0,
    "del2": 1100.0,
    "tau2": 32.48,
    "alf2": 0.2,
    "del3": 0.0,
    "tau3": 159.15,
    "alf3": 0.2,
    "del4": 0.0,
    "tau4": 15.915,
    "alf4": 0.2,
    "sig": 0.0002,
}


class TestColeColeBasic:
    def test_returns_complex(self):
        eps = cole_cole_permittivity(28e9, SKIN_PARAMS)
        assert isinstance(eps, complex)

    def test_real_part_positive(self):
        """Real part of permittivity must be positive for biological tissue."""
        eps = cole_cole_permittivity(28e9, SKIN_PARAMS)
        assert eps.real > 0

    def test_imaginary_part_negative(self):
        """Imaginary part is negative (loss convention eps = eps' - j*eps'')."""
        eps = cole_cole_permittivity(28e9, SKIN_PARAMS)
        assert eps.imag < 0

    def test_high_frequency_limit(self):
        """At very high frequency, permittivity approaches ef (high-freq limit)."""
        eps = cole_cole_permittivity(1e15, SKIN_PARAMS)
        assert eps.real == pytest.approx(SKIN_PARAMS["ef"], rel=0.1)

    def test_permittivity_decreases_with_frequency(self):
        """Real part of permittivity decreases with frequency (normal dispersion)."""
        eps_low = cole_cole_permittivity(1e9, SKIN_PARAMS)
        eps_high = cole_cole_permittivity(100e9, SKIN_PARAMS)
        assert eps_low.real > eps_high.real


class TestColeColeEdgeCases:
    def test_zero_conductivity(self):
        """With sig=0, no DC conductivity term."""
        params = {**SKIN_PARAMS, "sig": 0.0}
        eps = cole_cole_permittivity(28e9, params)
        assert isinstance(eps, complex)
        assert eps.real > 0

    def test_single_pole_only(self):
        """With only one active pole, result is a simple Debye relaxation."""
        params = {
            "ef": 4.0,
            "del1": 30.0,
            "tau1": 7.0,
            "alf1": 0.0,
            "del2": 0.0,
            "tau2": 0.0,
            "alf2": 0.0,
            "del3": 0.0,
            "tau3": 0.0,
            "alf3": 0.0,
            "del4": 0.0,
            "tau4": 0.0,
            "alf4": 0.0,
            "sig": 0.0,
        }
        eps = cole_cole_permittivity(28e9, params)
        # Manual Debye: ef + del1 / (1 + j*omega*tau)
        omega = 2 * np.pi * 28e9
        tau = 7.0 * 1e-12  # pole 1 unit is ps
        expected = 4.0 + 30.0 / (1 + 1j * omega * tau)
        assert eps.real == pytest.approx(expected.real, rel=1e-10)
        assert eps.imag == pytest.approx(expected.imag, rel=1e-10)

    def test_multiple_frequencies_consistent(self):
        """Multiple scalar calls produce monotonically decreasing real part."""
        freqs = [1e9, 10e9, 28e9, 60e9, 100e9]
        eps_vals = [cole_cole_permittivity(f, SKIN_PARAMS) for f in freqs]
        reals = [e.real for e in eps_vals]
        for i in range(len(reals) - 1):
            assert reals[i] > reals[i + 1]
