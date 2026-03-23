"""Property-based tests for tissue physics using Hypothesis.

These tests verify physics invariants hold across random parameter ranges,
catching edge cases that fixed golden tests might miss.
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from aegis.tissue.fresnel import T0, fresnel_transmission, n_complex

# Strategy: realistic tissue parameters
eps_r_st = st.floats(min_value=1.0, max_value=80.0)
sigma_st = st.floats(min_value=0.0, max_value=100.0)
freq_st = st.floats(min_value=1e9, max_value=300e9)
mu_st = st.floats(min_value=0.0, max_value=1.0)


class TestRefractiveIndexProperties:
    """Physics invariants for complex refractive index."""

    @given(eps_r=eps_r_st, sigma=sigma_st, freq=freq_st)
    @settings(max_examples=50)
    def test_positive_real_part(self, eps_r, sigma, freq):
        n = n_complex(eps_r, sigma, freq)
        assert n.real > 0

    @given(eps_r=eps_r_st, sigma=sigma_st, freq=freq_st)
    @settings(max_examples=50)
    def test_magnitude_at_least_one(self, eps_r, sigma, freq):
        """|n| >= 1 for any medium denser than vacuum."""
        n = n_complex(eps_r, sigma, freq)
        assert abs(n) >= 1.0 - 1e-10


class TestT0Properties:
    """Physics invariants for normal-incidence transmission."""

    @given(eps_r=eps_r_st, sigma=sigma_st, freq=freq_st)
    @settings(max_examples=50)
    def test_T0_in_unit_interval(self, eps_r, sigma, freq):
        n = n_complex(eps_r, sigma, freq)
        t0 = T0(n)
        assert 0 < t0 <= 1.0 + 1e-14

    def test_T0_unity_for_vacuum(self):
        """T_0 = 1 when n = 1 (no interface)."""
        assert T0(complex(1.0, 0.0)) == pytest.approx(1.0, abs=1e-10)

    def test_T0_decreases_with_n(self):
        """Higher |n| means more reflection, lower T_0."""
        t0_low = T0(complex(2.0, 0.0))
        t0_high = T0(complex(5.0, 0.0))
        assert t0_low > t0_high


class TestFresnelTransmissionProperties:
    """Physics invariants for angle-dependent Fresnel transmission."""

    @given(mu=mu_st)
    @settings(max_examples=50)
    def test_bounded_skin(self, mu):
        """T_s, T_p in [0, 1] for skin at 28 GHz."""
        n = n_complex(17.0, 25.0, 28e9)
        T_s, T_p = fresnel_transmission(mu, n)
        assert -1e-10 <= T_s <= 1.0 + 1e-10
        assert -1e-10 <= T_p <= 1.0 + 1e-10

    @given(
        eps_r=eps_r_st,
        sigma=sigma_st,
        freq=freq_st,
        mu=st.floats(min_value=0.01, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_bounded_general(self, eps_r, sigma, freq, mu):
        """T_s, T_p in [0, 1] for any tissue and angle."""
        n = n_complex(eps_r, sigma, freq)
        T_s, T_p = fresnel_transmission(mu, n)
        assert -1e-10 <= T_s <= 1.0 + 1e-10
        assert -1e-10 <= T_p <= 1.0 + 1e-10

    def test_Tp_exceeds_Ts_at_oblique(self):
        """TM transmission exceeds TE at oblique angles (pseudo-Brewster)."""
        n = n_complex(17.0, 25.0, 28e9)
        mu_60 = np.cos(np.radians(60))
        T_s, T_p = fresnel_transmission(mu_60, n)
        assert T_p > T_s
