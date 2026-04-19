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

    @pytest.mark.parametrize(("theta_deg", "exp_Ts", "exp_Tp", "exp_Tavg"), TABLE_1)
    def test_table1_values(self, theta_deg, exp_Ts, exp_Tp, exp_Tavg):
        mu = np.cos(np.radians(theta_deg))
        T_s, T_p = fresnel_transmission(mu, N_SKIN_28)
        T_avg = 0.5 * (T_s + T_p)

        # 1e-3 is tight enough to reject small numerical corruptions like
        # `mu**2 -> mu**3` (diffs ~1e-3 at oblique angles) while still matching
        # the 3-digit monograph values (rounding error < 5e-4).
        assert T_s == pytest.approx(exp_Ts, abs=1e-3)
        assert T_p == pytest.approx(exp_Tp, abs=1e-3)
        assert T_avg == pytest.approx(exp_Tavg, abs=1e-3)


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

    def test_T0_degenerate_n_tilde_minus_one_raises(self):
        """T0(-1) causes |1+n|^2=0, must raise instead of returning inf."""
        with pytest.raises(ValueError, match="Cannot compute T0"):
            T0(-1.0 + 0j)


class TestFresnelHighPrecision:
    """High-precision reference values for skin at 28 GHz.

    The monograph Table 1 is rounded to 3 decimals, which lets small numeric
    corruptions (e.g. ``mu**2 -> mu**3``) slip through with <5e-4 error.
    These tests lock the formula at 8-decimal precision against values
    computed from the canonical closed form, and anchor the amplitude
    transmission/reflection coefficients (phase + magnitude) so the coherent
    path cannot drift independently of the power path.
    """

    # Reference values computed from the canonical formulas at theta=45 deg,
    # skin at 28 GHz (eps_r=17.0, sigma=25.0 S/m). Captured to 10 decimals from
    # the unmutated implementation. A 1e-9 abs tolerance is well below any
    # physically meaningful mutation on this function.
    REF_T_S = 0.4218406076
    REF_T_P = 0.6657317169
    REF_T_S_NORMAL = 0.5386723767
    REF_T0 = 0.5386723767
    REF_T_S_AMP_45 = 0.24447251063166323 + 0.08565982285270618j
    REF_T_P_AMP_45 = 0.3103780207303508 + 0.09455736751523924j
    REF_R_S_45 = -0.7555274893683368 + 0.08565982285270621j
    REF_R_P_45 = 0.5634841819400653 - 0.12943670179928313j
    REF_XI_45 = 4.445107820955217 - 1.8052655039958063j

    def test_transmission_power_45deg_exact(self):
        mu = float(np.cos(np.radians(45)))
        T_s, T_p = fresnel_transmission(mu, N_SKIN_28)
        assert T_s == pytest.approx(self.REF_T_S, abs=1e-9)
        assert T_p == pytest.approx(self.REF_T_P, abs=1e-9)

    def test_transmission_power_normal_exact(self):
        T_s, T_p = fresnel_transmission(1.0, N_SKIN_28)
        assert T_s == pytest.approx(self.REF_T_S_NORMAL, abs=1e-9)
        assert T_p == pytest.approx(self.REF_T_S_NORMAL, abs=1e-9)
        assert T0(N_SKIN_28) == pytest.approx(self.REF_T0, abs=1e-9)

    def test_amplitude_transmission_normal_matches_2_over_1_plus_n(self):
        """At normal incidence, t_s = t_p = 2 / (1 + n_tilde) (closed form)."""
        t_s, t_p = fresnel_amplitude(1.0, N_SKIN_28)
        expected = 2 / (1 + N_SKIN_28)
        assert t_s == pytest.approx(expected, abs=1e-12)
        assert t_p == pytest.approx(expected, abs=1e-12)
        # Anchor magnitude so a mutation like ``2 * mu * (mu + xi)`` (instead
        # of divide) can't sneak through.
        assert abs(t_s) == pytest.approx(abs(expected), abs=1e-12)
        # The phase and sign must also match; ``2 / mu / (mu + xi)`` at mu=1
        # gives the same value but away from normal it doesn't.

    def test_amplitude_transmission_45deg_exact(self):
        mu = float(np.cos(np.radians(45)))
        t_s, t_p = fresnel_amplitude(mu, N_SKIN_28)
        assert t_s == pytest.approx(self.REF_T_S_AMP_45, abs=1e-12)
        assert t_p == pytest.approx(self.REF_T_P_AMP_45, abs=1e-12)

    def test_reflection_45deg_exact(self):
        mu = float(np.cos(np.radians(45)))
        r_s, r_p = fresnel_reflection(mu, N_SKIN_28)
        assert r_s == pytest.approx(self.REF_R_S_45, abs=1e-12)
        assert r_p == pytest.approx(self.REF_R_P_45, abs=1e-12)

    def test_xi_from_mu_45deg_exact(self):
        """xi = sqrt(n^2 - 1 + mu^2), 10-decimal reference at theta=45."""
        from aegis._array_backend import xp

        mu = xp.asarray([float(np.cos(np.radians(45)))], dtype=complex)
        xi = xi_from_mu(mu, N_SKIN_28)
        xi_val = complex(np.asarray(xi)[0])
        assert xi_val == pytest.approx(self.REF_XI_45, abs=1e-12)

    def test_xi_from_mu_normal_equals_n_tilde(self):
        """At normal incidence (mu=1), xi = sqrt(n^2 - 1 + 1) = n_tilde."""
        from aegis._array_backend import xp

        xi = xi_from_mu(xp.asarray([1.0 + 0j]), N_SKIN_28)
        xi_val = complex(np.asarray(xi)[0])
        assert xi_val == pytest.approx(N_SKIN_28, abs=1e-12)


class TestScalarReturnTypes:
    """Scalar inputs must return Python scalars, not 1-element arrays.

    The wrappers branch on ``scalar_input = mu.ndim == 0``. A mutation of the
    branch predicate silently returns a NumPy array at the scalar API, which
    downstream coherent code passes to JAX primitives that then raise or
    silently broadcast. Lock the contract here.
    """

    def test_fresnel_transmission_scalar_returns_python_floats(self):
        T_s, T_p = fresnel_transmission(0.5, N_SKIN_28)
        assert isinstance(T_s, float)
        assert isinstance(T_p, float)

    def test_fresnel_reflection_scalar_returns_python_complex(self):
        r_s, r_p = fresnel_reflection(0.5, N_SKIN_28)
        assert isinstance(r_s, complex)
        assert isinstance(r_p, complex)

    def test_fresnel_amplitude_scalar_returns_python_complex(self):
        t_s, t_p = fresnel_amplitude(0.5, N_SKIN_28)
        assert isinstance(t_s, complex)
        assert isinstance(t_p, complex)

    def test_array_input_returns_ndarray(self):
        mu = np.asarray([0.5, 0.8])
        T_s, T_p = fresnel_transmission(mu, N_SKIN_28)
        assert isinstance(T_s, np.ndarray)
        assert isinstance(T_p, np.ndarray)


class TestGrazingClamp:
    """The sub-threshold grazing clamp (mu_real < 1e-10 -> T = 0) must engage
    specifically when mu is tiny-but-nonzero, not only at mu = 0. Without the
    clamp, JIT'd complex paths can leak sub-picowatt T that then causes NaNs
    when projected through 1/mu in downstream Sab normalisation.
    """

    def test_tiny_mu_is_clamped_to_zero(self):
        T_s, T_p = fresnel_transmission(1e-11, N_SKIN_28)
        assert T_s == 0.0
        assert T_p == 0.0

    def test_mu_above_threshold_is_not_clamped(self):
        T_s, T_p = fresnel_transmission(1e-9, N_SKIN_28)
        assert T_s > 0.0
        assert T_p > 0.0


class TestSignConvention:
    """n_complex uses the physics time-convention exp(-j omega t).

    This fixes ``Im(n_tilde) < 0`` for lossy media. The coherent kernels and
    the Fresnel amplitude coefficients carry a phase that inverts under the
    opposite convention, so a sign flip must fail loudly.
    """

    def test_n_complex_imag_negative_for_lossy_medium(self):
        """Im(n) < 0 for a lossy dielectric under exp(-j omega t)."""
        n = n_complex(17.0, 25.0, 28e9)
        assert n.imag < 0, f"Expected Im(n) < 0, got {n}"

    def test_n_complex_imag_scales_with_sigma(self):
        """|Im(n)| grows monotonically with conductivity (more loss)."""
        n1 = n_complex(17.0, 1.0, 28e9)
        n2 = n_complex(17.0, 25.0, 28e9)
        n3 = n_complex(17.0, 100.0, 28e9)
        assert abs(n1.imag) < abs(n2.imag) < abs(n3.imag)
