"""Golden tests for Fresnel transmission against monograph Table 1.

Table 1: T_s, T_p, T_avg vs incidence angle for skin at 28 GHz.
Tissue: eps_r=17.0, sigma=25.0 S/m, freq=28 GHz.
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from aegis.tissue.fresnel import (
    T0,
    fresnel_amplitude,
    fresnel_reflection,
    fresnel_transmission,
    n_complex,
    xi_from_mu,
)
from tests.conftest import NUMERICAL_FLOOR

# Skin at 28 GHz
N_SKIN_28 = n_complex(17.0, 25.0, 28e9)


class TestFresnelGolden:
    """Monograph Table 1: Fresnel coefficients for skin at 28 GHz."""

    # (theta_deg, T_s, T_p, T_avg) from monograph Table 1
    TABLE_1 = [
        (0, 0.539, 0.539, 0.539),
        (30, 0.489, 0.591, 0.540),
        (45, 0.422, 0.666, 0.544),
        (60, 0.321, 0.791, 0.556),
        (75, 0.182, 0.952, 0.567),
    ]

    @pytest.mark.parametrize("theta_deg, exp_Ts, exp_Tp, exp_Tavg", TABLE_1)
    def test_table1_values(self, theta_deg, exp_Ts, exp_Tp, exp_Tavg):
        mu = np.cos(np.radians(theta_deg))
        T_s, T_p = fresnel_transmission(mu, N_SKIN_28)
        T_avg = 0.5 * (T_s + T_p)

        assert T_s == pytest.approx(exp_Ts, abs=0.002)
        assert T_p == pytest.approx(exp_Tp, abs=0.002)
        assert T_avg == pytest.approx(exp_Tavg, abs=0.002)


class TestFresnelProperties:
    """Physics invariants for Fresnel transmission."""

    def test_normal_incidence_symmetry(self):
        """T_s == T_p at normal incidence (theta=0)."""
        T_s, T_p = fresnel_transmission(1.0, N_SKIN_28)
        assert T_s == pytest.approx(T_p, abs=1e-10)

    def test_normal_incidence_matches_T0(self):
        """fresnel_transmission(mu=1) should match the T0 formula."""
        T_s, T_p = fresnel_transmission(1.0, N_SKIN_28)
        assert T_s == pytest.approx(T0(N_SKIN_28), abs=1e-10)

    def test_grazing_incidence_zero(self):
        """T -> 0 at grazing incidence (theta -> 90)."""
        T_s, T_p = fresnel_transmission(0.0, N_SKIN_28)
        assert T_s == 0.0
        assert T_p == 0.0

    def test_transmission_bounded(self):
        """0 <= T_s, T_p <= 1 for all angles."""
        mu = np.cos(np.linspace(0, np.pi / 2, 91))
        T_s, T_p = fresnel_transmission(mu, N_SKIN_28)
        assert np.all(T_s >= 0)
        assert np.all(T_s <= 1)
        assert np.all(T_p >= 0)
        assert np.all(T_p <= 1)

    def test_vectorized_matches_scalar(self):
        """Array input should match element-wise scalar calls."""
        angles = [0, 30, 45, 60, 75]
        mu_arr = np.cos(np.radians(angles))
        T_s_vec, T_p_vec = fresnel_transmission(mu_arr, N_SKIN_28)

        for i, theta in enumerate(angles):
            mu = np.cos(np.radians(theta))
            T_s_scalar, T_p_scalar = fresnel_transmission(mu, N_SKIN_28)
            assert T_s_vec[i] == pytest.approx(T_s_scalar, abs=1e-12)
            assert T_p_vec[i] == pytest.approx(T_p_scalar, abs=1e-12)


class TestRefractiveIndex:
    """Tests for n_complex."""

    def test_positive_real_part(self):
        n = n_complex(17.0, 25.0, 28e9)
        assert n.real > 0

    def test_lossy_has_imaginary(self):
        n = n_complex(17.0, 25.0, 28e9)
        assert n.imag != 0

    def test_lossless_real(self):
        """sigma=0 gives purely real n = sqrt(eps_r)."""
        n = n_complex(4.0, 0.0, 28e9)
        assert n.imag == pytest.approx(0.0, abs=1e-15)
        assert n.real == pytest.approx(2.0, abs=1e-10)

    def test_skin_28ghz_magnitude(self):
        """|n| for skin at 28 GHz should be ~4.84."""
        n = n_complex(17.0, 25.0, 28e9)
        assert abs(n) == pytest.approx(4.84, abs=0.02)


class TestFresnelReflection:
    """Tests for fresnel_reflection amplitude coefficients."""

    def test_normal_incidence_formula(self):
        """At normal incidence |r_s| = |r_p| = |1 - n| / |1 + n|."""
        n = n_complex(4.0, 0.0, 28e9)  # lossless dielectric, n=2
        r_s, r_p = fresnel_reflection(1.0, n)
        # r_s = (mu - xi)/(mu + xi) = (1 - n)/(1 + n) at normal incidence
        assert r_s == pytest.approx((1 - n) / (1 + n), abs=1e-10)
        # r_p = (n^2*mu - xi)/(n^2*mu + xi) = (n^2 - n)/(n^2 + n) = (n-1)/(n+1)
        assert r_p == pytest.approx((n - 1) / (n + 1), abs=1e-10)
        # |r_s| == |r_p| at normal incidence
        assert abs(r_s) == pytest.approx(abs(r_p), abs=1e-10)

    def test_normal_incidence_symmetry(self):
        """|r_s| == |r_p| at normal incidence (signs differ by convention)."""
        r_s, r_p = fresnel_reflection(1.0, N_SKIN_28)
        assert abs(r_s) == pytest.approx(abs(r_p), abs=1e-10)

    def test_reflection_transmission_conservation(self):
        """Energy conservation: |r|^2 + T = 1 for lossless media."""
        n = n_complex(4.0, 0.0, 28e9)
        mu = np.cos(np.linspace(0.01, np.pi / 2, 50))
        r_s, r_p = fresnel_reflection(mu, n)
        T_s, T_p = fresnel_transmission(mu, n)
        np.testing.assert_allclose(np.abs(r_s) ** 2 + T_s, 1.0, atol=1e-10)
        np.testing.assert_allclose(np.abs(r_p) ** 2 + T_p, 1.0, atol=1e-10)

    def test_reflection_bounded(self):
        """|r_s|, |r_p| <= 1 for all angles."""
        mu = np.cos(np.linspace(0, np.pi / 2, 91))
        r_s, r_p = fresnel_reflection(mu, N_SKIN_28)
        assert np.all(np.abs(r_s) <= 1.0 + 1e-10)
        assert np.all(np.abs(r_p) <= 1.0 + 1e-10)

    def test_vectorized_matches_scalar(self):
        """Array input matches element-wise scalar calls."""
        mu_arr = np.cos(np.radians([0, 30, 45, 60, 75]))
        r_s_vec, r_p_vec = fresnel_reflection(mu_arr, N_SKIN_28)
        for i, mu in enumerate(mu_arr):
            r_s_s, r_p_s = fresnel_reflection(float(mu), N_SKIN_28)
            assert r_s_vec[i] == pytest.approx(r_s_s, abs=1e-12)
            assert r_p_vec[i] == pytest.approx(r_p_s, abs=1e-12)


class TestFresnelEdgeCases:
    """Edge case tests for Fresnel transmission and reflection."""

    def test_energy_conservation(self):
        """T + R <= 1 for all angles (energy conservation)."""
        n_tilde = n_complex(17.0, 25.0, 28e9)
        mu_values = np.linspace(0.01, 1.0, 100)
        for mu in mu_values:
            T_s, T_p = fresnel_transmission(mu, n_tilde)
            r_s, r_p = fresnel_reflection(mu, n_tilde)
            R_s = abs(r_s) ** 2
            R_p = abs(r_p) ** 2
            assert T_s + R_s <= 1.0 + 1e-10, f"T_s + R_s > 1 at mu={mu}"
            assert T_p + R_p <= 1.0 + 1e-10, f"T_p + R_p > 1 at mu={mu}"

    def test_T0_bounds(self):
        """T0 should be in (0, 1] for physical materials."""
        for eps_r, sigma, freq in [(17.0, 25.0, 28e9), (7.9, 36.4, 60e9), (4.0, 2.0, 28e9)]:
            n = n_complex(eps_r, sigma, freq)
            t0 = T0(n)
            assert 0 < t0 <= 1.0, f"T0={t0} out of bounds for eps_r={eps_r}"

    def test_xi_branch_selection(self):
        """xi = sqrt(n^2 - 1 + mu^2) should always have Re(xi) >= 0."""
        from aegis._array_backend import xp

        n_tilde = n_complex(17.0, 25.0, 28e9)
        mu_values = xp.linspace(0.0, 1.0, 200)
        xi = xi_from_mu(mu_values, n_tilde)
        xi_np = np.asarray(xi)
        assert np.all(np.real(xi_np) >= NUMERICAL_FLOOR), "Re(xi) must be >= 0"

    def test_vectorized_fresnel_transmission(self):
        """Fresnel should work with array mu inputs."""
        n_tilde = n_complex(17.0, 25.0, 28e9)
        mu = np.linspace(0.01, 1.0, 50)
        T_s, T_p = fresnel_transmission(mu, n_tilde)
        assert T_s.shape == (50,)
        assert T_p.shape == (50,)
        assert np.all(T_s >= 0)
        assert np.all(T_p >= 0)

    def test_amplitude_transmission_nonzero_at_normal(self):
        """Amplitude transmission should be nonzero at normal incidence."""
        n_tilde = n_complex(17.0, 25.0, 28e9)
        t_s, t_p = fresnel_amplitude(1.0, n_tilde)
        assert abs(t_s) > 0
        assert abs(t_p) > 0

    def test_n_complex_positive_real_multiple_materials(self):
        """Complex refractive index should have Re(n) > 0."""
        for eps_r, sigma, freq in [(17.0, 25.0, 28e9), (7.9, 36.4, 60e9), (80.0, 0.5, 1e9)]:
            n = n_complex(eps_r, sigma, freq)
            assert n.real > 0, f"Re(n) should be > 0, got {n}"

    @given(
        eps_r=st.floats(min_value=1.0, max_value=100.0),
        sigma=st.floats(min_value=0.01, max_value=100.0),
    )
    @settings(max_examples=50)
    def test_T0_positive_hypothesis(self, eps_r, sigma):
        """T0 is positive for any reasonable tissue."""
        n = n_complex(eps_r, sigma, 28e9)
        t0 = T0(n)
        assert t0 > 0
        assert t0 <= 1.0
