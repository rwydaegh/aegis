"""Tests for vectorized Cole-Cole."""

from __future__ import annotations

import numpy as np
import pytest

from aegis.tissue.cole_cole import cole_cole_permittivity


class TestColeColeVectorized:
    """Verify vectorized Cole-Cole matches scalar-by-scalar calls."""

    @pytest.fixture
    def params(self):
        return {
            "ef": 4.0,
            "del1": 32.0,
            "tau1": 7.23,
            "alf1": 0.0,
            "del2": 1100.0,
            "tau2": 32.48,
            "alf2": 0.2,
            "del3": 33000.0,
            "tau3": 159.15,
            "alf3": 0.2,
            "del4": 0.0,
            "tau4": 15.915,
            "alf4": 0.2,
            "sig": 0.0002,
        }

    def test_vectorized_matches_scalar(self, params):
        freqs = np.linspace(1e9, 100e9, 50)
        eps_vec = cole_cole_permittivity(freqs, params)
        for i, f in enumerate(freqs):
            eps_scalar = cole_cole_permittivity(f, params)
            assert abs(eps_vec[i] - eps_scalar) < 1e-10

    def test_vectorized_causality(self, params):
        """Real part should be positive, imaginary part negative for lossy tissue."""
        freqs = np.geomspace(1e6, 300e9, 200)
        eps = cole_cole_permittivity(freqs, params)
        assert np.all(np.real(eps) > 0), "Real permittivity should be positive"
        assert np.all(np.imag(eps) <= 0), "Imaginary part should be non-positive (lossy)"
