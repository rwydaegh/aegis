"""Tests for dipole model and communication channel vector."""

import numpy as np

from aegis.constants import C_0


class TestDipoleEffectiveLength:
    """Half-wave dipole radiation pattern."""

    def test_broadside_maximum(self):
        """Broadside effective length matches Balanis: lambda/pi at theta=90."""
        from aegis.mimo.channel import dipole_effective_length

        freq_hz = 28e9
        lam = C_0 / freq_hz
        d_hat = np.array([0.0, 0.0, 1.0])
        k_hat = np.array([[1.0, 0.0, 0.0]])
        C_R = dipole_effective_length(k_hat, d_hat, freq_hz)
        mag = np.linalg.norm(C_R[0])
        np.testing.assert_allclose(mag, lam / np.pi, rtol=1e-10)

    def test_endfire_null(self):
        """Zero response along dipole axis (endfire)."""
        from aegis.mimo.channel import dipole_effective_length

        freq_hz = 28e9
        d_hat = np.array([0.0, 0.0, 1.0])
        k_hat = np.array([[0.0, 0.0, 1.0]])
        C_R = dipole_effective_length(k_hat, d_hat, freq_hz)
        np.testing.assert_allclose(np.linalg.norm(C_R[0]), 0.0, atol=1e-10)

    def test_endfire_null_negative(self):
        """Zero response along negative dipole axis."""
        from aegis.mimo.channel import dipole_effective_length

        freq_hz = 28e9
        d_hat = np.array([0.0, 0.0, 1.0])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        C_R = dipole_effective_length(k_hat, d_hat, freq_hz)
        np.testing.assert_allclose(np.linalg.norm(C_R[0]), 0.0, atol=1e-10)

    def test_polarization_perpendicular_to_k(self):
        """Effective length is perpendicular to k_hat (transverse field)."""
        from aegis.mimo.channel import dipole_effective_length

        freq_hz = 28e9
        d_hat = np.array([0.0, 0.0, 1.0])
        rng = np.random.default_rng(99)
        k_hat = rng.standard_normal((10, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        C_R = dipole_effective_length(k_hat, d_hat, freq_hz)
        dots = np.sum(C_R.real * k_hat, axis=1)
        np.testing.assert_allclose(dots, 0.0, atol=1e-10)

    def test_azimuthal_symmetry(self):
        """Dipole has azimuthal symmetry around its axis."""
        from aegis.mimo.channel import dipole_effective_length

        freq_hz = 28e9
        d_hat = np.array([0.0, 0.0, 1.0])
        k1 = np.array([[1.0, 0.0, 0.0]])
        k2 = np.array([[0.0, 1.0, 0.0]])
        C_R1 = dipole_effective_length(k1, d_hat, freq_hz)
        C_R2 = dipole_effective_length(k2, d_hat, freq_hz)
        np.testing.assert_allclose(
            np.linalg.norm(C_R1),
            np.linalg.norm(C_R2),
            atol=1e-14,
        )

    def test_batch_shape(self):
        """Output shape is (N, 3) for N input directions."""
        from aegis.mimo.channel import dipole_effective_length

        k_hat = np.eye(3)
        d_hat = np.array([0.0, 0.0, 1.0])
        C_R = dipole_effective_length(k_hat, d_hat, freq_hz=28e9)
        assert C_R.shape == (3, 3)


class TestChannelVector:
    """Communication channel h_k from array to UE."""

    def _make_scenario(self):
        """2-element array, LOS path, vertical dipole UE."""
        from aegis.mimo.array import AntennaArray
        from aegis.paths import PropagationPaths

        freq_hz = 28e9
        lam = C_0 / freq_hz
        arr = AntennaArray.upa(
            n_h=2,
            n_v=1,
            d_h=0.5 * lam,
            d_v=0.5 * lam,
            center=np.array([5.0, 0.0, 3.0]),
            broadside=np.array([-1.0, 0.0, 0.0]),
        )
        k_hat = np.array([[-1.0, 0.0, 0.0]])
        power = np.array([1.0])
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        device_pos = np.array([0.0, 0.0, 1.5])
        device_ori = np.array([0.0, 0.0, 1.0])
        return arr, paths, device_pos, device_ori, freq_hz

    def test_shape(self):
        """Channel vector is (M_ant,) complex."""
        from aegis.mimo.channel import compute_channel_vector

        arr, paths, dev_pos, dev_ori, freq = self._make_scenario()
        h = compute_channel_vector(paths, arr, dev_pos, dev_ori, freq)
        assert h.shape == (arr.n_elements,)
        assert h.dtype == complex

    def test_single_element_scalar(self):
        """Single-element array gives a scalar channel."""
        from aegis.mimo.array import AntennaArray
        from aegis.mimo.channel import compute_channel_vector
        from aegis.paths import PropagationPaths

        freq_hz = 28e9
        arr = AntennaArray.upa(
            n_h=1,
            n_v=1,
            d_h=0.005,
            d_v=0.005,
            center=np.array([5.0, 0.0, 3.0]),
            broadside=np.array([-1.0, 0.0, 0.0]),
        )
        k_hat = np.array([[-1.0, 0.0, 0.0]])
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=np.array([1.0]))
        h = compute_channel_vector(
            paths,
            arr,
            device_position=np.array([0.0, 0.0, 1.5]),
            device_orientation=np.array([0.0, 0.0, 1.0]),
            freq_hz=freq_hz,
        )
        assert h.shape == (1,)

    def test_nonzero_for_broadside_dipole(self):
        """Channel is nonzero when UE dipole is perpendicular to arrival."""
        from aegis.mimo.channel import compute_channel_vector

        arr, paths, dev_pos, dev_ori, freq = self._make_scenario()
        h = compute_channel_vector(paths, arr, dev_pos, dev_ori, freq)
        assert np.linalg.norm(h) > 0

    def test_zero_for_endfire_dipole(self):
        """Channel is zero when UE dipole is aligned with arrival direction."""
        from aegis.mimo.channel import compute_channel_vector

        arr, paths, dev_pos, _, freq = self._make_scenario()
        dev_ori_endfire = np.array([-1.0, 0.0, 0.0])
        h = compute_channel_vector(paths, arr, dev_pos, dev_ori_endfire, freq)
        np.testing.assert_allclose(np.abs(h), 0.0, atol=1e-10)

    def test_steering_phase_in_channel(self):
        """Elements at different offsets have different phases in h."""
        from aegis.mimo.channel import compute_channel_vector

        arr, paths, dev_pos, dev_ori, freq = self._make_scenario()
        h = compute_channel_vector(paths, arr, dev_pos, dev_ori, freq)
        np.testing.assert_allclose(np.abs(h[0]), np.abs(h[1]), rtol=1e-10)
        offsets = arr.element_positions - arr.reference_position
        k0 = 2 * np.pi * freq / C_0
        expected_phase_diff = k0 * ((offsets[1] - offsets[0]) @ paths.k_hat[0])
        actual_phase_diff = np.angle(h[1]) - np.angle(h[0])
        actual_phase_diff = (actual_phase_diff + np.pi) % (2 * np.pi) - np.pi
        expected_phase_diff = (expected_phase_diff + np.pi) % (2 * np.pi) - np.pi
        np.testing.assert_allclose(actual_phase_diff, expected_phase_diff, atol=1e-10)

    def test_empty_paths(self):
        """Empty paths give zero channel."""
        from aegis.mimo.array import AntennaArray
        from aegis.mimo.channel import compute_channel_vector
        from aegis.paths import PropagationPaths

        arr = AntennaArray.upa(
            n_h=2,
            n_v=2,
            d_h=0.005,
            d_v=0.005,
            center=np.zeros(3),
            broadside=np.array([1.0, 0, 0]),
        )
        empty = PropagationPaths.from_powers(
            k_hat=np.empty((0, 3)),
            power=np.empty(0),
        )
        h = compute_channel_vector(
            empty,
            arr,
            device_position=np.zeros(3),
            device_orientation=np.array([0, 0, 1.0]),
            freq_hz=28e9,
        )
        np.testing.assert_allclose(h, 0.0)
