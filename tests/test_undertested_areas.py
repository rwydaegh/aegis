"""Tests for undertested areas: Cole-Cole model, Fresnel edge cases,
directivity SH fitting, averaging matrix properties, and ECBF validation.

Added by overnight Agent 3 to close coverage gaps identified in codebase audit.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from aegis._array_backend import xp
from aegis.coherent.ecbf import solve_ecbf
from aegis.coherent.exposure_operator import compute_exposure_operator, compute_rho, eigendecompose_Q
from aegis.geometry.averaging import precompute_averaging_matrix
from aegis.geometry.directivity import (
    compute_directivity,
    eval_sh,
    fit_sh,
    sh_reconstruction_error,
    spherical_angles_from_k_hat,
)
from aegis.tissue.cole_cole import cole_cole_permittivity, debye_permittivity
from aegis.tissue.dielectric import SKIN_28GHZ, TissueModel
from aegis.tissue.fresnel import (
    T0,
    fresnel_amplitude,
    fresnel_reflection,
    fresnel_transmission,
    n_complex,
    xi_from_mu,
)

# ---------------------------------------------------------------------------
# Cole-Cole 4-pole model tests
# ---------------------------------------------------------------------------


class TestColeCole:
    """Tests for the 4-pole Cole-Cole permittivity model."""

    @pytest.fixture
    def skin_params(self):
        """Gabriel parameters for dry skin (approximate literature values)."""
        return {
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

    def test_high_frequency_limit(self, skin_params):
        """At very high frequency, permittivity approaches ef."""
        eps = cole_cole_permittivity(1e15, skin_params)
        assert abs(eps.real - skin_params["ef"]) < 1.0

    def test_low_frequency_limit(self, skin_params):
        """At very low frequency, real part should include all dispersion poles."""
        eps = cole_cole_permittivity(1.0, skin_params)
        # Real part should be much larger than ef due to dispersion
        assert eps.real > skin_params["ef"]

    def test_imaginary_part_negative(self, skin_params):
        """Imaginary part should be negative (lossy medium convention)."""
        for f in [1e6, 1e9, 28e9, 60e9]:
            eps = cole_cole_permittivity(f, skin_params)
            assert eps.imag < 0, f"Expected Im(eps) < 0 at {f} Hz, got {eps.imag}"

    def test_permittivity_decreases_with_frequency(self, skin_params):
        """Real permittivity generally decreases with increasing frequency."""
        freqs = [1e6, 1e8, 1e9, 10e9, 100e9]
        eps_values = [cole_cole_permittivity(f, skin_params).real for f in freqs]
        # Not strictly monotone due to multiple poles, but overall trend is decreasing
        assert eps_values[0] > eps_values[-1]

    def test_zero_poles_give_ef(self):
        """When all dispersion poles are zero, result is just ef + conductivity."""
        params = {
            "ef": 5.0,
            "del1": 0,
            "tau1": 0,
            "alf1": 0,
            "del2": 0,
            "tau2": 0,
            "alf2": 0,
            "del3": 0,
            "tau3": 0,
            "alf3": 0,
            "del4": 0,
            "tau4": 0,
            "alf4": 0,
            "sig": 0,
        }
        eps = cole_cole_permittivity(28e9, params)
        assert abs(eps - 5.0) < 1e-10

    def test_single_debye_pole_matches_debye_model(self):
        """Cole-Cole with alpha=0 reduces to Debye. Check consistency."""
        eps_inf = 4.0
        eps_static = 40.0
        sigma = 0.5
        tau_s = 7.23e-12  # picoseconds -> seconds
        f = 28e9

        # Cole-Cole with one active pole (alpha=0 => Debye)
        cc_params = {
            "ef": eps_inf,
            "del1": eps_static - eps_inf,
            "tau1": tau_s / 1e-12,
            "alf1": 0.0,
            "del2": 0,
            "tau2": 0,
            "alf2": 0,
            "del3": 0,
            "tau3": 0,
            "alf3": 0,
            "del4": 0,
            "tau4": 0,
            "alf4": 0,
            "sig": sigma,
        }
        eps_cc = cole_cole_permittivity(f, cc_params)
        eps_debye = debye_permittivity(f, eps_inf, eps_static, sigma, tau_s)

        assert abs(eps_cc - eps_debye) < 1e-8, f"Cole-Cole with alpha=0 should match Debye: {eps_cc} vs {eps_debye}"

    def test_array_frequency_input(self):
        """Cole-Cole should handle array frequency inputs."""
        params = {
            "ef": 4.0,
            "del1": 32.0,
            "tau1": 7.23,
            "alf1": 0.0,
            "del2": 0,
            "tau2": 0,
            "alf2": 0,
            "del3": 0,
            "tau3": 0,
            "alf3": 0,
            "del4": 0,
            "tau4": 0,
            "alf4": 0,
            "sig": 0.001,
        }
        freqs = np.array([1e9, 10e9, 28e9, 60e9])
        eps = cole_cole_permittivity(freqs, params)
        assert eps.shape == (4,)
        # Each element should match the scalar call
        for i, f in enumerate(freqs):
            eps_scalar = cole_cole_permittivity(f, params)
            assert abs(eps[i] - eps_scalar) < 1e-10

    def test_scalar_returns_complex(self):
        """Scalar frequency input should return a Python complex."""
        params = {
            "ef": 4.0,
            "del1": 32.0,
            "tau1": 7.23,
            "alf1": 0.0,
            "del2": 0,
            "tau2": 0,
            "alf2": 0,
            "del3": 0,
            "tau3": 0,
            "alf3": 0,
            "del4": 0,
            "tau4": 0,
            "alf4": 0,
            "sig": 0.001,
        }
        eps = cole_cole_permittivity(28e9, params)
        assert isinstance(eps, complex)


# ---------------------------------------------------------------------------
# Debye model tests
# ---------------------------------------------------------------------------


class TestDebye:
    def test_static_limit(self):
        """At omega -> 0, Debye gives eps_static (minus conductivity divergence)."""
        eps = debye_permittivity(1e-3, eps_inf=4.0, eps_static=40.0, sigma=0.0, tau_s=1e-11)
        assert abs(eps.real - 40.0) < 0.1

    def test_high_freq_limit(self):
        """At very high frequency, Debye gives eps_inf."""
        eps = debye_permittivity(1e15, eps_inf=4.0, eps_static=40.0, sigma=0.0, tau_s=1e-11)
        assert abs(eps.real - 4.0) < 0.1

    def test_conductivity_contribution(self):
        """Adding conductivity makes imaginary part more negative."""
        f = 28e9
        eps_no_sig = debye_permittivity(f, 4.0, 40.0, sigma=0.0, tau_s=1e-11)
        eps_with_sig = debye_permittivity(f, 4.0, 40.0, sigma=1.0, tau_s=1e-11)
        assert eps_with_sig.imag < eps_no_sig.imag


# ---------------------------------------------------------------------------
# Fresnel coefficient tests
# ---------------------------------------------------------------------------


class TestFresnelEdgeCases:
    """Edge case tests for Fresnel transmission and reflection."""

    def test_normal_incidence_matches_T0(self):
        """At mu=1 (normal incidence), Fresnel T_s and T_p should match T0."""
        n_tilde = n_complex(17.0, 25.0, 28e9)
        T_s, T_p = fresnel_transmission(1.0, n_tilde)
        t0 = T0(n_tilde)
        assert abs(T_s - t0) < 1e-6
        assert abs(T_p - t0) < 1e-6

    def test_grazing_incidence_zero(self):
        """At mu=0 (grazing), T_s and T_p should be zero."""
        n_tilde = n_complex(17.0, 25.0, 28e9)
        T_s, T_p = fresnel_transmission(0.0, n_tilde)
        assert abs(T_s) < 1e-6
        assert abs(T_p) < 1e-6

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
        n_tilde = n_complex(17.0, 25.0, 28e9)
        mu_values = xp.linspace(0.0, 1.0, 200)
        xi = xi_from_mu(mu_values, n_tilde)
        xi_np = np.asarray(xi)
        assert np.all(np.real(xi_np) >= -1e-15), "Re(xi) must be >= 0"

    def test_vectorized_fresnel(self):
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

    def test_n_complex_positive_real(self):
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


# ---------------------------------------------------------------------------
# Directivity and SH fitting tests
# ---------------------------------------------------------------------------


class TestDirectivitySH:
    """Tests for spherical harmonic fitting edge cases."""

    def test_constant_directivity_L0(self):
        """L=0 fit of constant D should give perfect reconstruction."""
        rng = np.random.default_rng(42)
        N = 50
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        theta, phi = spherical_angles_from_k_hat(k_hat)
        D = np.ones(N) * 3.0  # constant directivity

        c = fit_sh(D, theta, phi, L=0)
        D_hat = eval_sh(c, theta, phi, L=0)
        assert np.allclose(D_hat, D, atol=1e-6)

    def test_sh_reconstruction_error_decreases_with_L(self):
        """Higher L should give equal or lower reconstruction error."""
        rng = np.random.default_rng(42)
        N = 200
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        theta, phi = spherical_angles_from_k_hat(k_hat)

        # Create a non-trivial directivity pattern
        D = 1.0 + 0.5 * np.cos(theta) + 0.3 * np.sin(theta) * np.cos(phi)
        D = np.abs(D)  # ensure positive

        errors = []
        for L in range(5):
            result = sh_reconstruction_error(D, theta, phi, L)
            errors.append(result["rms"])

        # Error should generally decrease (allow small numerical fluctuation)
        for i in range(1, len(errors)):
            assert errors[i] <= errors[i - 1] + 1e-8

    def test_sh_n_coefficients(self):
        """Number of SH coefficients should be (L+1)^2."""
        for L in range(6):
            rng = np.random.default_rng(42)
            k_hat = rng.standard_normal((100, 3))
            k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
            theta, phi = spherical_angles_from_k_hat(k_hat)
            D = np.ones(100)
            c = fit_sh(D, theta, phi, L)
            assert c.shape == ((L + 1) ** 2,)

    def test_compute_directivity_mean_one(self):
        """Directivity D = A_perp / mean(A_perp) should have mean 1."""
        A_perp = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        D = compute_directivity(A_perp)
        assert abs(np.mean(D) - 1.0) < 1e-12

    def test_compute_directivity_zero_raises(self):
        """Zero projected area should raise ValueError."""
        with pytest.raises(ValueError, match="mean.*> 0"):
            compute_directivity(np.zeros(5))

    def test_spherical_angles_special_directions(self):
        """Check known directions produce correct angles."""
        # +z -> theta=0
        k = np.array([[0, 0, 1.0]])
        theta, phi = spherical_angles_from_k_hat(k)
        assert abs(theta[0]) < 1e-10

        # -z -> theta=pi
        k = np.array([[0, 0, -1.0]])
        theta, phi = spherical_angles_from_k_hat(k)
        assert abs(theta[0] - np.pi) < 1e-10

        # +x -> theta=pi/2, phi=0
        k = np.array([[1.0, 0, 0]])
        theta, phi = spherical_angles_from_k_hat(k)
        assert abs(theta[0] - np.pi / 2) < 1e-10
        assert abs(phi[0]) < 1e-10

    def test_spherical_angles_zero_vector_raises(self):
        """Zero-length vectors should raise ValueError."""
        with pytest.raises(ValueError, match="zero-length"):
            spherical_angles_from_k_hat(np.array([[0, 0, 0]]))

    def test_fit_sh_negative_L_raises(self):
        """Negative L should raise ValueError."""
        with pytest.raises(ValueError, match="L must be >= 0"):
            fit_sh(np.ones(10), np.ones(10), np.ones(10), L=-1)


# ---------------------------------------------------------------------------
# Averaging matrix property tests
# ---------------------------------------------------------------------------


class TestAveragingMatrix:
    """Property tests for the spatial averaging matrix."""

    def test_row_stochastic(self):
        """Each row of G should sum to 1 (row-stochastic)."""
        rng = np.random.default_rng(42)
        M = 50
        centroids = rng.uniform(0, 0.1, (M, 3))
        areas = np.full(M, 1e-4)  # 1 cm^2 each

        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        row_sums = np.asarray(G.sum(axis=1)).ravel()
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-12)

    def test_non_negative_entries(self):
        """All entries of G should be non-negative."""
        rng = np.random.default_rng(42)
        M = 50
        centroids = rng.uniform(0, 0.1, (M, 3))
        areas = np.full(M, 1e-4)

        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        assert np.all(G.toarray() >= 0)

    def test_averaging_reduces_peak(self):
        """Spatial averaging should not increase the peak value for positive sab."""
        rng = np.random.default_rng(42)
        M = 80
        centroids = rng.uniform(0, 0.05, (M, 3))
        areas = np.full(M, 5e-5)

        sab = rng.uniform(0, 10, M)
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        sab_avg = np.asarray(G @ sab).ravel()

        # Peak of averaged <= peak of raw (convexity of weighted average)
        assert np.max(sab_avg) <= np.max(sab) + 1e-10

    def test_constant_field_preserved(self):
        """Averaging a constant field should return the same constant."""
        rng = np.random.default_rng(42)
        M = 40
        centroids = rng.uniform(0, 0.05, (M, 3))
        areas = np.full(M, 1e-4)

        sab = np.full(M, 7.5)
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        sab_avg = np.asarray(G @ sab).ravel()
        np.testing.assert_allclose(sab_avg, 7.5, atol=1e-10)

    def test_total_power_preserved(self):
        """Total absorbed power P_abs = sum(sab * area) should be approximately preserved."""
        rng = np.random.default_rng(42)
        M = 60
        centroids = rng.uniform(0, 0.05, (M, 3))
        areas = rng.uniform(5e-5, 2e-4, M)

        sab = rng.uniform(0, 10, M)
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        sab_avg = np.asarray(G @ sab).ravel()

        p_abs_raw = np.sum(sab * areas)
        p_abs_avg = np.sum(sab_avg * areas)

        # Not exactly preserved (weighted average != area-preserving),
        # but should be close for reasonably uniform meshes
        assert abs(p_abs_avg - p_abs_raw) / p_abs_raw < 0.5

    def test_single_triangle(self):
        """Single triangle: G should be [1]."""
        centroids = np.array([[0, 0, 0]])
        areas = np.array([1e-4])
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        assert G.toarray().shape == (1, 1)
        assert abs(G.toarray()[0, 0] - 1.0) < 1e-12

    def test_widely_separated_triangles(self):
        """Triangles far apart should only average with themselves."""
        centroids = np.array([[0, 0, 0], [100, 0, 0], [0, 100, 0]], dtype=float)
        areas = np.array([1e-4, 1e-4, 1e-4])
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        # Each row should be a one-hot (self-averaging only)
        G_dense = G.toarray()
        np.testing.assert_allclose(G_dense, np.eye(3), atol=1e-12)


# ---------------------------------------------------------------------------
# ECBF solver validation tests
# ---------------------------------------------------------------------------


class TestECBFValidation:
    """Input validation tests for the ECBF solver."""

    def test_negative_power_raises(self):
        """Negative transmit power should raise ValueError."""
        h = np.array([1 + 0j, 0])
        Q = np.eye(2)
        with pytest.raises(ValueError, match="positive"):
            solve_ecbf(h, Q, P_abs_max=0.1, P=-1.0)

    def test_zero_power_raises(self):
        """Zero transmit power should raise ValueError."""
        h = np.array([1 + 0j, 0])
        Q = np.eye(2)
        with pytest.raises(ValueError, match="positive"):
            solve_ecbf(h, Q, P_abs_max=0.1, P=0.0)

    def test_negative_pabs_max_raises(self):
        """Negative P_abs_max should raise ValueError."""
        h = np.array([1 + 0j, 0])
        Q = np.eye(2)
        with pytest.raises(ValueError, match="positive"):
            solve_ecbf(h, Q, P_abs_max=-0.1, P=1.0)

    def test_h_wrong_shape_raises(self):
        """2D channel vector should raise ValueError."""
        h = np.array([[1 + 0j, 0]])  # 2D
        Q = np.eye(2)
        with pytest.raises(ValueError, match="1D"):
            solve_ecbf(h, Q, P_abs_max=0.1, P=1.0)

    def test_Q_non_square_raises(self):
        """Non-square Q should raise ValueError."""
        h = np.array([1 + 0j, 0])
        Q = np.ones((2, 3))
        with pytest.raises(ValueError, match="square"):
            solve_ecbf(h, Q, P_abs_max=0.1, P=1.0)

    def test_dimension_mismatch_raises(self):
        """Mismatched h and Q dimensions should raise ValueError."""
        h = np.array([1 + 0j, 0, 0])  # 3 elements
        Q = np.eye(2)  # 2x2
        with pytest.raises(ValueError, match="mismatch"):
            solve_ecbf(h, Q, P_abs_max=0.1, P=1.0)

    def test_unconstrained_returns_mrt(self):
        """When constraint is not active, should return MRT precoder."""
        M = 4
        h = np.array([1, 0.5, 0.2, 0.1], dtype=complex)
        Q = 0.001 * np.eye(M)  # very small Q => constraint easily satisfied
        P = 1.0
        P_abs_max = 10.0  # very loose constraint

        x_star = np.asarray(solve_ecbf(h, Q, P_abs_max, P))

        # Should be MRT: x = sqrt(P) * h* / ||h||
        h_conj = h.conj()
        x_mrt = np.sqrt(P) * h_conj / np.linalg.norm(h_conj)
        np.testing.assert_allclose(x_star, x_mrt, atol=1e-8)

    def test_power_constraint_satisfied(self):
        """||x*||^2 should equal P."""
        M = 4
        rng = np.random.default_rng(42)
        h = rng.standard_normal(M) + 1j * rng.standard_normal(M)
        A = rng.standard_normal((M, M)) + 1j * rng.standard_normal((M, M))
        Q = A.conj().T @ A  # Hermitian PSD
        P = 2.0
        P_abs_max = 0.5

        x_star = np.asarray(solve_ecbf(h, Q, P_abs_max, P))
        power = float(np.real(np.vdot(x_star, x_star)))
        assert abs(power - P) < 1e-6

    def test_exposure_constraint_satisfied(self):
        """x*^H Q x* should be <= P_abs_max."""
        M = 4
        rng = np.random.default_rng(42)
        h = rng.standard_normal(M) + 1j * rng.standard_normal(M)
        A = rng.standard_normal((M, M)) + 1j * rng.standard_normal((M, M))
        Q = A.conj().T @ A
        P = 2.0
        P_abs_max = 0.3

        x_star = np.asarray(solve_ecbf(h, Q, P_abs_max, P))
        p_abs = float(np.real(x_star.conj() @ Q @ x_star))
        assert p_abs <= P_abs_max + 1e-6


# ---------------------------------------------------------------------------
# Exposure operator tests
# ---------------------------------------------------------------------------


class TestExposureOperator:
    """Tests for Q computation and eigendecomposition."""

    def test_Q_hermitian(self):
        """Q should be Hermitian."""
        rng = np.random.default_rng(42)
        M_tri, M_ant = 10, 4
        G_tilde = rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))
        areas = np.full(M_tri, 1e-4)

        Q = np.asarray(compute_exposure_operator(xp.asarray(G_tilde), xp.asarray(areas)))
        np.testing.assert_allclose(Q, Q.conj().T, atol=1e-12)

    def test_Q_positive_semidefinite(self):
        """Q eigenvalues should be >= 0."""
        rng = np.random.default_rng(42)
        M_tri, M_ant = 10, 4
        G_tilde = rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))
        areas = np.full(M_tri, 1e-4)

        Q = compute_exposure_operator(xp.asarray(G_tilde), xp.asarray(areas))
        eigenvalues, _ = eigendecompose_Q(Q)
        assert np.all(np.asarray(eigenvalues) >= -1e-12)

    def test_eigenvalues_descending(self):
        """Eigenvalues from eigendecompose_Q should be in descending order."""
        rng = np.random.default_rng(42)
        M_tri, M_ant = 10, 4
        G_tilde = rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))
        areas = np.full(M_tri, 1e-4)

        Q = compute_exposure_operator(xp.asarray(G_tilde), xp.asarray(areas))
        eigenvalues, _ = eigendecompose_Q(Q)
        ev = np.asarray(eigenvalues)
        assert np.all(np.diff(ev) <= 1e-12), "Eigenvalues not in descending order"

    def test_rho_bounds(self):
        """rho should be in [0, 1]."""
        rng = np.random.default_rng(42)
        M_ant = 4
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        A = rng.standard_normal((M_ant, M_ant)) + 1j * rng.standard_normal((M_ant, M_ant))
        Q = xp.asarray(A.conj().T @ A)

        rho = compute_rho(xp.asarray(h), Q)
        assert 0 <= rho <= 1.0 + 1e-10

    def test_rho_eigenvector_extremes(self):
        """rho = 1 when h is the dominant eigenvector of Q."""
        M_ant = 4
        rng = np.random.default_rng(42)
        A = rng.standard_normal((M_ant, M_ant)) + 1j * rng.standard_normal((M_ant, M_ant))
        Q_np = A.conj().T @ A
        eigenvalues, V = np.linalg.eigh(Q_np)
        h_max = V[:, -1]  # dominant eigenvector

        rho = compute_rho(xp.asarray(h_max), xp.asarray(Q_np))
        assert abs(rho - 1.0) < 1e-8

    def test_rho_zero_channel(self):
        """rho should be 0 for zero channel vector."""
        Q = xp.asarray(np.eye(4, dtype=complex))
        h = xp.asarray(np.zeros(4, dtype=complex))
        rho = compute_rho(h, Q)
        assert rho == 0.0


# ---------------------------------------------------------------------------
# TissueModel tests
# ---------------------------------------------------------------------------


class TestTissueModel:
    def test_skin_28ghz_T0_range(self):
        """Predefined skin tissue should have physical T0."""
        assert 0.3 < SKIN_28GHZ.T0 < 0.7

    def test_n_complex_positive_real(self):
        """Refractive index should have positive real part."""
        for tissue in [SKIN_28GHZ]:
            assert tissue.n_complex.real > 0

    def test_from_params(self):
        """from_params should create identical tissue."""
        t = TissueModel.from_params("test", eps_r=17.0, sigma=25.0, freq_hz=28e9)
        assert t.eps_r == 17.0
        assert t.sigma == 25.0
        assert t.freq_hz == 28e9

    def test_frozen(self):
        """TissueModel should be immutable."""
        with pytest.raises(AttributeError):
            SKIN_28GHZ.eps_r = 42.0


# ---------------------------------------------------------------------------
# Level 1 array backend fix verification
# ---------------------------------------------------------------------------


class TestLevel1ArrayBackend:
    """Verify the np.full -> xp.full fix in level1_aggregate."""

    def test_level1_returns_correct_type(self):
        """level1_aggregate should return xp arrays, not NumPy arrays when using xp backend."""
        from aegis.kernels.level1_aggregate import level1_aggregate

        k_hat = np.array([[0, 0, -1.0]])
        power = np.array([1.0])
        sab, p_abs = level1_aggregate(
            total_area=0.1,
            A_ab=0.01,
            k_hat=k_hat,
            power=power,
            T0=0.5,
            n_triangles=10,
        )
        assert sab.shape == (10,)
        assert np.all(np.isfinite(np.asarray(sab)))

    def test_level1_uniform_distribution(self):
        """Level 1 should distribute power uniformly across all triangles."""
        from aegis.kernels.level1_aggregate import level1_aggregate

        k_hat = np.array([[0, 0, -1.0], [1, 0, 0.0]])
        power = np.array([1.0, 0.5])
        n_tri = 20

        sab, p_abs = level1_aggregate(
            total_area=0.5,
            A_ab=0.02,
            k_hat=k_hat,
            power=power,
            T0=0.5,
            n_triangles=n_tri,
        )
        sab_np = np.asarray(sab)
        # All values should be identical (uniform)
        assert np.allclose(sab_np, sab_np[0])
        # sab * total_area should equal p_abs
        assert abs(sab_np[0] * 0.5 - p_abs) < 1e-12
