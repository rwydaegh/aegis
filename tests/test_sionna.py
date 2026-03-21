"""Tests for Sionna RT integration.

The unit conversion test does NOT require sionna-rt to be installed.
It tests the pure-math conversion from Sionna's channel coefficients to
AEGIS psi vectors.
"""

import numpy as np

from aegis.constants import C_0, Z_0


class TestUnitConversion:
    """Test the Sionna a -> AEGIS psi conversion formula.

    Reference: spec section 1c, numerical verification table.
    LOS, isotropic TX, P_T=1W, d=10m, f=28GHz, lambda=0.01071m.
    """

    def test_los_power_density(self):
        """Verify converted psi gives correct free-space power density."""
        from aegis.integration.sionna import _convert_a_to_psi

        freq_hz = 28e9
        lambda_ = C_0 / freq_hz
        d = 10.0
        P_T = 1.0

        # Sionna LOS coefficient for isotropic TX: a = lambda/(4*pi*d)
        # Arriving from +x direction: theta_r = pi/2, phi_r = pi (pointing -x)
        a_magnitude = lambda_ / (4 * np.pi * d)

        # Vertically polarized: all energy in theta component
        a_theta = np.array([a_magnitude + 0j])
        a_phi = np.array([0.0 + 0j])
        theta_r = np.array([np.pi / 2])
        phi_r = np.array([np.pi])

        psi = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, P_T)

        # |psi|^2 / (2*Z_0) should equal S_inc = P_T / (4*pi*d^2)
        power = np.sum(np.abs(psi) ** 2, axis=1) / (2 * Z_0)
        expected = P_T / (4 * np.pi * d**2)
        np.testing.assert_allclose(power, expected, rtol=1e-10)

    def test_los_psi_magnitude_matches_differt(self):
        """Cross-check: psi magnitude should match DiffeRT's formula."""
        from aegis.integration.sionna import _convert_a_to_psi

        freq_hz = 28e9
        lambda_ = C_0 / freq_hz
        d = 10.0
        P_T = 1.0

        a_theta = np.array([lambda_ / (4 * np.pi * d) + 0j])
        a_phi = np.array([0.0 + 0j])
        theta_r = np.array([np.pi / 2])
        phi_r = np.array([0.0])

        psi = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, P_T)

        # DiffeRT formula: amplitude = sqrt(2*Z_0*P_T/(4*pi)) / d
        expected_magnitude = np.sqrt(2 * Z_0 * P_T / (4 * np.pi)) / d
        actual_magnitude = np.linalg.norm(psi[0])
        np.testing.assert_allclose(actual_magnitude, expected_magnitude, rtol=1e-10)

    def test_psi_perpendicular_to_k_hat(self):
        """psi must be perpendicular to the direction of arrival."""
        from aegis.integration.sionna import _convert_a_to_psi

        freq_hz = 28e9
        a_theta = np.array([0.001 + 0.002j])
        a_phi = np.array([0.003 - 0.001j])
        theta_r = np.array([1.2])
        phi_r = np.array([0.7])

        psi = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, 1.0)

        # k_hat from spherical angles
        k_hat = np.array(
            [
                np.sin(theta_r[0]) * np.cos(phi_r[0]),
                np.sin(theta_r[0]) * np.sin(phi_r[0]),
                np.cos(theta_r[0]),
            ]
        )
        dot = np.abs(np.dot(psi[0].real, k_hat)) + np.abs(np.dot(psi[0].imag, k_hat))
        assert dot < 1e-12

    def test_spherical_basis_orthonormality(self):
        """e_theta and e_phi should be orthonormal and perpendicular to r_hat."""
        from aegis.integration.sionna import _spherical_basis

        theta = np.array([0.5, 1.0, 2.5])
        phi = np.array([0.3, 1.5, 4.0])
        e_theta, e_phi = _spherical_basis(theta, phi)

        for i in range(3):
            # Unit length
            np.testing.assert_allclose(np.linalg.norm(e_theta[i]), 1.0, atol=1e-14)
            np.testing.assert_allclose(np.linalg.norm(e_phi[i]), 1.0, atol=1e-14)
            # Orthogonal to each other
            np.testing.assert_allclose(np.dot(e_theta[i], e_phi[i]), 0.0, atol=1e-14)
            # Orthogonal to r_hat
            r_hat = np.array(
                [
                    np.sin(theta[i]) * np.cos(phi[i]),
                    np.sin(theta[i]) * np.sin(phi[i]),
                    np.cos(theta[i]),
                ]
            )
            np.testing.assert_allclose(np.dot(e_theta[i], r_hat), 0.0, atol=1e-14)
            np.testing.assert_allclose(np.dot(e_phi[i], r_hat), 0.0, atol=1e-14)

    def test_higher_power_scales_psi(self):
        """Doubling TX power should multiply |psi| by sqrt(2)."""
        from aegis.integration.sionna import _convert_a_to_psi

        freq_hz = 28e9
        lambda_ = C_0 / freq_hz
        a_theta = np.array([lambda_ / (4 * np.pi * 10) + 0j])
        a_phi = np.array([0.0 + 0j])
        theta_r = np.array([np.pi / 2])
        phi_r = np.array([0.0])

        psi_1w = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, 1.0)
        psi_2w = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, 2.0)

        ratio = np.linalg.norm(psi_2w) / np.linalg.norm(psi_1w)
        np.testing.assert_allclose(ratio, np.sqrt(2), rtol=1e-10)
