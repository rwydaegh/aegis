"""Tests for Sionna RT integration.

The unit conversion test does NOT require sionna-rt to be installed.
It tests the pure-math conversion from Sionna's channel coefficients to
AEGIS psi vectors.
"""

import numpy as np
import pytest

from aegis._array_backend import JAX_AVAILABLE
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


@pytest.mark.skipif(not JAX_AVAILABLE, reason="JAX not installed")
class TestJAXConversion:
    """Test that Sionna conversion functions work with JAX arrays."""

    def test_spherical_basis_jax(self):
        """_spherical_basis returns JAX arrays when given JAX input."""
        import jax
        import jax.numpy as jnp

        from aegis.integration.sionna import _spherical_basis

        theta = jnp.array([0.5, 1.0, 2.5])
        phi = jnp.array([0.3, 1.5, 4.0])
        e_theta, e_phi = _spherical_basis(theta, phi)

        assert isinstance(e_theta, jax.Array)
        assert isinstance(e_phi, jax.Array)

        for i in range(3):
            assert float(jnp.abs(jnp.dot(e_theta[i], e_phi[i]))) < 1e-12

    def test_spherical_basis_jax_matches_numpy(self):
        """JAX and NumPy spherical basis give identical results."""
        import jax.numpy as jnp

        from aegis.integration.sionna import _spherical_basis

        theta_np = np.array([0.5, 1.0, 2.5])
        phi_np = np.array([0.3, 1.5, 4.0])
        e_theta_np, e_phi_np = _spherical_basis(theta_np, phi_np)

        e_theta_jax, e_phi_jax = _spherical_basis(jnp.array(theta_np), jnp.array(phi_np))
        np.testing.assert_allclose(np.asarray(e_theta_jax), e_theta_np, atol=1e-14)
        np.testing.assert_allclose(np.asarray(e_phi_jax), e_phi_np, atol=1e-14)

    def test_convert_a_to_psi_jax_grad(self):
        """Gradient of |psi|^2 w.r.t. a_theta flows through conversion."""
        import jax
        import jax.numpy as jnp

        from aegis.integration.sionna import _convert_a_to_psi

        freq_hz = 28e9
        theta_r = jnp.array([jnp.pi / 2])
        phi_r = jnp.array([0.0])

        def loss(a_theta_real):
            a_theta = a_theta_real.astype(complex)
            a_phi = jnp.zeros(1, dtype=complex)
            psi = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, 1.0)
            return jnp.sum(jnp.abs(psi) ** 2) / (2 * Z_0)

        a_val = jnp.array([0.001])
        grad = jax.grad(loss)(a_val)
        assert jnp.all(jnp.isfinite(grad))
        assert float(jnp.abs(grad[0])) > 0.0

    def test_convert_a_to_psi_jax_matches_numpy(self):
        """JAX and NumPy conversion give identical results."""
        import jax.numpy as jnp

        from aegis.integration.sionna import _convert_a_to_psi

        freq_hz = 28e9
        a_theta_np = np.array([0.001 + 0.002j])
        a_phi_np = np.array([0.003 - 0.001j])
        theta_r_np = np.array([1.2])
        phi_r_np = np.array([0.7])

        psi_np = _convert_a_to_psi(a_theta_np, a_phi_np, theta_r_np, phi_r_np, freq_hz, 1.0)
        psi_jax = _convert_a_to_psi(
            jnp.array(a_theta_np),
            jnp.array(a_phi_np),
            jnp.array(theta_r_np),
            jnp.array(phi_r_np),
            freq_hz,
            1.0,
        )
        np.testing.assert_allclose(np.asarray(psi_jax), psi_np, rtol=1e-12)

    def test_paths_from_sionna_jax_shapes_and_masking(self):
        """_paths_from_sionna_jax produces correct shapes and masks invalid paths."""
        import jax.numpy as jnp

        from aegis.integration.sionna import _paths_from_sionna_jax

        n_elements = 2
        n_paths = 4
        freq_hz = 28e9
        tx_power_w = 1.0

        # Mock Sionna Paths object
        class MockPaths:
            def __init__(self):
                # (num_rx=1, num_rx_ant=2, num_tx=1, num_tx_ant=M, num_paths=N, num_time=1)
                a = np.zeros((1, 2, 1, n_elements, n_paths, 1), dtype=complex)
                # Put signal in theta component for paths 0,1,2 (path 3 invalid)
                a[0, 0, 0, :, :3, 0] = 0.001 + 0j
                self._a = jnp.array(a)
                self._tau = jnp.array(np.array([[[0.01, 0.02, 0.03, 0.0]]]))
                self.theta_r = jnp.array([[[1.0, 0.5, 1.5, 0.0]]])
                self.phi_r = jnp.array([[[0.3, 0.7, 1.2, 0.0]]])

            def cir(self, out_type="numpy"):
                return self._a, self._tau

        valid_np = np.array([[[True, True, True, False]]])

        result = _paths_from_sionna_jax(MockPaths(), valid_np, n_elements, freq_hz, tx_power_w)

        # Total paths = n_elements * n_paths_per_elem
        assert result.n_paths == n_elements * n_paths
        assert result.k_hat.shape == (n_elements * n_paths, 3)
        assert result.psi.shape == (n_elements * n_paths, 3)

        # Invalid paths (index 3 and 7) should have zero psi
        for invalid_idx in [3, 7]:
            assert float(jnp.sum(jnp.abs(result.psi[invalid_idx]))) == 0.0

        # Valid paths should have nonzero psi
        for valid_idx in [0, 1, 2, 4, 5, 6]:
            assert float(jnp.sum(jnp.abs(result.psi[valid_idx]))) > 0.0

        # Invalid paths k_hat should be safe default [0,0,-1], not zero
        for invalid_idx in [3, 7]:
            np.testing.assert_allclose(np.asarray(result.k_hat[invalid_idx]), [0.0, 0.0, -1.0])

        # Element indices: first n_paths belong to elem 0, next to elem 1
        assert int(result.element_index[0]) == 0
        assert int(result.element_index[n_paths]) == 1

        # LOS: one per element (shortest delay = path 0 in each block)
        assert bool(result.is_los[0])  # elem 0, path 0 (tau=0.01, lowest)
        assert bool(result.is_los[n_paths])  # elem 1, path 0 (tau=0.01, lowest)

    def test_differentiable_flag_exists(self):
        """paths_from_sionna_scene accepts differentiable parameter."""
        import inspect

        from aegis.integration.sionna import paths_from_sionna_scene

        sig = inspect.signature(paths_from_sionna_scene)
        assert "differentiable" in sig.parameters

    def test_end_to_end_sionna_to_dosimetry_grad(self):
        """Gradient flows from dosimetry loss through Sionna psi conversion."""
        import jax
        import jax.numpy as jnp

        from aegis.integration.sionna import _convert_a_to_psi
        from aegis.kernels.level2_geometric import level2_geometric

        freq_hz = 28e9
        normals = jnp.array([[0.0, 0.0, 1.0]])
        T0 = 0.5
        theta_r = jnp.array([0.01])  # near-zenith
        phi_r = jnp.array([0.0])

        def loss(a_theta_real):
            a_theta = a_theta_real.astype(complex)
            a_phi = jnp.zeros(1, dtype=complex)
            psi = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, 1.0)
            power = jnp.sum(jnp.abs(psi) ** 2, axis=1) / (2 * Z_0)
            k_hat = -jnp.array(
                [
                    [
                        jnp.sin(theta_r[0]) * jnp.cos(phi_r[0]),
                        jnp.sin(theta_r[0]) * jnp.sin(phi_r[0]),
                        jnp.cos(theta_r[0]),
                    ]
                ]
            )
            sab = level2_geometric(normals, k_hat, power, T0)
            return jnp.sum(sab)

        a_val = jnp.array([0.001])
        grad = jax.grad(loss)(a_val)
        assert jnp.all(jnp.isfinite(grad))
        assert float(grad[0]) > 0.0  # more signal -> more absorption

    def test_sionna_to_dosimetry_grad_matches_finite_diff(self):
        """JAX grad matches finite difference through Sionna conversion."""
        import jax
        import jax.numpy as jnp

        from aegis.integration.sionna import _convert_a_to_psi
        from aegis.kernels.level2_geometric import level2_geometric

        freq_hz = 28e9
        normals = jnp.array([[0.0, 0.0, 1.0]])
        T0 = 0.5
        theta_r = jnp.array([0.5])
        phi_r = jnp.array([0.3])

        def loss(a_theta_real):
            a_theta = a_theta_real.astype(complex)
            a_phi = jnp.zeros(1, dtype=complex)
            psi = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, 1.0)
            power = jnp.sum(jnp.abs(psi) ** 2, axis=1) / (2 * Z_0)
            k_hat = -jnp.array(
                [
                    [
                        jnp.sin(theta_r[0]) * jnp.cos(phi_r[0]),
                        jnp.sin(theta_r[0]) * jnp.sin(phi_r[0]),
                        jnp.cos(theta_r[0]),
                    ]
                ]
            )
            return jnp.sum(level2_geometric(normals, k_hat, power, T0))

        a_val = jnp.array([0.001])
        jax_grad = jax.grad(loss)(a_val)

        eps = 1e-7
        fd_grad = (float(loss(a_val + eps)) - float(loss(a_val - eps))) / (2 * eps)
        np.testing.assert_allclose(float(jax_grad[0]), fd_grad, rtol=1e-3)
