"""Tests for directivity computation and spherical harmonic fitting.

Covers: compute_directivity, spherical_angles_from_k_hat, fit_sh, eval_sh,
sh_reconstruction_error, and special-direction edge cases.
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.geometry.directivity import (
    compute_directivity,
    eval_sh,
    fit_sh,
    sh_reconstruction_error,
    spherical_angles_from_k_hat,
)


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
