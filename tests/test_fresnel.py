"""Golden tests for Fresnel transmission against monograph Table 1.

Table 1: T_s, T_p, T_avg vs incidence angle for skin at 28 GHz.
Tissue: eps_r=17.0, sigma=25.0 S/m, freq=28 GHz.
"""

import numpy as np
import pytest

from aegis.tissue.fresnel import T0, fresnel_transmission, n_complex

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
