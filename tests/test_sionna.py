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


@pytest.mark.slow
def test_trace_sets_scene_frequency_to_carrier():
    """paths_from_sionna_scene must set the carrier on the scene.

    Sionna defaults a loaded scene to 3.5 GHz, and the frequency drives the
    radio material coefficients, synthetic-array spacing, and path-loss
    wavelength. A caller that does not set it would silently trace the wrong
    band, so the bridge sets it from freq_hz.
    """
    srt = pytest.importorskip("sionna.rt")

    from aegis.integration.sionna import paths_from_sionna_scene

    scene = srt.load_scene(srt.scene.simple_street_canyon)
    scene.frequency = 3.5e9  # wrong band on purpose

    tx = np.array([[0.0, 0.0, 20.0]])
    rx = np.array([30.0, 0.0, 1.5])
    paths_from_sionna_scene(scene, tx, rx, freq_hz=28e9, max_bounces=2, tx_power_dbm=30.0)

    assert float(scene.frequency[0]) == pytest.approx(28e9)


def _wrap(x):
    return (x + np.pi) % (2 * np.pi) - np.pi


def test_coherent_psi_carries_propagation_phase_away_from_origin():
    """The kernel plane-wave expansion E(r) = sum_n psi_n exp(-i k0 k_n . r)
    (absolute coordinates) must reproduce the analytic spherical-wave phase at
    a receiver far from the world origin.

    Regression for two 2026-07 bugs: Sionna keeps the carrier propagation
    phase in tau (not in a) and the bridge normalized delays to zero, so psi
    carried no propagation phase at all; and psi was referenced to the rx
    point while every coherent kernel phases at absolute coordinates.
    """
    srt = pytest.importorskip("sionna.rt")

    from aegis.integration.sionna import paths_from_sionna_scene

    scene = srt.load_scene()  # empty: single LOS path
    freq = 28e9
    k0 = 2 * np.pi * freq / C_0
    tx = np.array([40.0, -25.0, 12.0])
    rx = np.array([120.0, 80.0, 1.5])
    d = np.linalg.norm(rx - tx)

    paths = paths_from_sionna_scene(
        scene,
        tx_positions=tx[None, :],
        rx_position=rx,
        freq_hz=freq,
        max_bounces=1,
        tx_power_dbm=30.0,
        samples_per_src=100_000,
    )
    assert paths.n_paths == 1
    assert paths.k_hat_tx is not None
    np.testing.assert_allclose(paths.k_hat[0], (rx - tx) / d, atol=1e-3)
    np.testing.assert_allclose(paths.k_hat_tx[0], (rx - tx) / d, atol=1e-3)
    # true delay survives (no first-arrival normalization)
    np.testing.assert_allclose(paths.delay[0], d / C_0, rtol=1e-6)

    psi = np.asarray(paths.psi[0])
    comp = int(np.argmax(np.abs(psi)))
    # kernel-reconstructed field phase at the rx (absolute-coordinate rule)
    ph_kernel = _wrap(np.angle(psi[comp]) - k0 * float(paths.k_hat[0] @ rx))
    # analytic spherical wave, up to the pi from Sionna's V-pol e_theta basis
    ph_analytic = _wrap(-k0 * d + np.pi)
    assert abs(_wrap(ph_kernel - ph_analytic)) < 1e-2

    # and the phase advances like a plane wave across a body-sized offset
    delta = 0.5
    rx2 = rx + paths.k_hat[0] * delta
    ph_kernel2 = _wrap(np.angle(psi[comp]) - k0 * float(paths.k_hat[0] @ rx2))
    assert abs(_wrap(ph_kernel2 - (ph_kernel - k0 * delta))) < 1e-4


def test_coherent_interpath_phase_advances_with_rx_translation():
    """Move the receiver a couple of wavelengths: the RELATIVE phase between
    the LOS and a bounce path must advance by k0 delta . (k_b - k_los), the
    geometry that creates interference fringes on a walking body.

    This is the decisive regression for the missing-carrier-phase bug: with
    psi built from Sionna's a alone (no delay phase), the relative phase stays
    constant under rx translation and no fringe can ever form.
    """
    srt = pytest.importorskip("sionna.rt")

    from aegis.integration.sionna import paths_from_sionna_scene

    scene = srt.load_scene(srt.scene.simple_street_canyon)
    freq = 28e9
    k0 = 2 * np.pi * freq / C_0
    tx = np.array([12.0, 4.0, 18.0])
    rx = np.array([-9.0, -3.0, 1.5])
    # ~2-3 wavelengths with a z component so both wall and ground bounces
    # produce a nonzero predicted advance; reflection geometry ~unchanged
    delta = np.array([0.02, 0.01, 0.015])

    def trace(rx_pos):
        paths = paths_from_sionna_scene(
            scene,
            tx_positions=tx[None, :],
            rx_position=rx_pos,
            freq_hz=freq,
            max_bounces=1,
            tx_power_dbm=30.0,
            samples_per_src=2_000_000,
            seed=7,
        )
        assert paths.n_paths >= 2
        return np.asarray(paths.psi), np.asarray(paths.k_hat), np.asarray(paths.delay)

    psi0, k0hat, delay0 = trace(rx)
    psi1, k1hat, _ = trace(rx + delta)
    los = int(np.argmin(delay0))
    bounce = int(np.argsort(delay0)[1])

    def phase_at(psi_row, k_row, rx_pos, comp):
        return np.angle(psi_row[comp]) - k0 * float(k_row @ rx_pos)

    def match(k_ref):
        # same physical path in the second trace: nearest arrival direction
        return int(np.argmax(k1hat @ k_ref))

    comp_l = int(np.argmax(np.abs(psi0[los])))
    comp_b = int(np.argmax(np.abs(psi0[bounce])))
    ml, mb = match(k0hat[los]), match(k0hat[bounce])
    assert float(k1hat[ml] @ k0hat[los]) > 0.9999
    assert float(k1hat[mb] @ k0hat[bounce]) > 0.9999

    rel0 = _wrap(phase_at(psi0[bounce], k0hat[bounce], rx, comp_b) - phase_at(psi0[los], k0hat[los], rx, comp_l))
    rel1 = _wrap(phase_at(psi1[mb], k1hat[mb], rx + delta, comp_b) - phase_at(psi1[ml], k1hat[ml], rx + delta, comp_l))
    measured_advance = _wrap(rel1 - rel0)
    predicted_advance = _wrap(-k0 * float((k0hat[bounce] - k0hat[los]) @ delta))
    assert abs(predicted_advance) > 0.3  # geometry actually discriminates
    assert abs(_wrap(measured_advance - predicted_advance)) < 0.15
