"""Tests for the MIMO compute orchestrator."""

from __future__ import annotations

import numpy as np
import pytest

from aegis.mimo import AntennaArray


@pytest.fixture
def two_element_array():
    """2-element array for basic MIMO tests."""
    return AntennaArray.upa(
        n_h=2,
        n_v=1,
        d_h=0.5 * 0.0107,  # lambda/2 at 28 GHz
        d_v=0.0107,
        center=np.array([5.0, 0.0, 3.0]),
        broadside=np.array([-1.0, 0.0, 0.0]),
    )


class TestMRTPrecoder:
    def test_mrt_shape(self, two_element_array):
        from aegis.mimo.compute import compute_mrt_precoder

        H = np.array([[1 + 0j, 0.5 + 0.5j], [0.5 - 0.5j, 1 + 0j]])
        W = compute_mrt_precoder(H, total_power=1.0)
        assert W.shape == (2, 2)

    def test_mrt_conjugate_direction(self):
        from aegis.mimo.compute import compute_mrt_precoder

        h = np.array([[1 + 1j, 0 + 0j]])
        W = compute_mrt_precoder(h, total_power=1.0)
        expected_dir = np.conj(h[0]) / np.linalg.norm(h[0])
        actual_dir = W[:, 0] / np.linalg.norm(W[:, 0])
        np.testing.assert_allclose(actual_dir, expected_dir, atol=1e-10)

    def test_mrt_equal_power_per_user(self):
        from aegis.mimo.compute import compute_mrt_precoder

        H = np.array([[1 + 0j, 0 + 0j], [0 + 0j, 1 + 0j]])
        P = 2.0
        W = compute_mrt_precoder(H, total_power=P)
        for k in range(2):
            np.testing.assert_allclose(np.linalg.norm(W[:, k]) ** 2, P / 2, atol=1e-10)

    def test_mrt_total_power(self):
        from aegis.mimo.compute import compute_mrt_precoder

        rng = np.random.default_rng(42)
        H = rng.standard_normal((3, 8)) + 1j * rng.standard_normal((3, 8))
        P = 5.0
        W = compute_mrt_precoder(H, total_power=P)
        np.testing.assert_allclose(np.linalg.norm(W, "fro") ** 2, P, atol=1e-10)


class TestComputeUserSab:
    def test_sab_shape(self):
        from aegis.mimo.compute import compute_user_sab

        M_tri, M_ant, K = 100, 4, 2
        rng = np.random.default_rng(0)
        G_tilde = rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))
        W = rng.standard_normal((M_ant, K)) + 1j * rng.standard_normal((M_ant, K))
        sab = compute_user_sab(G_tilde, W)
        assert sab.shape == (M_tri,)

    def test_sab_nonnegative(self):
        from aegis.mimo.compute import compute_user_sab

        rng = np.random.default_rng(1)
        G_tilde = rng.standard_normal((50, 3, 4)) + 1j * rng.standard_normal((50, 3, 4))
        W = rng.standard_normal((4, 2)) + 1j * rng.standard_normal((4, 2))
        sab = compute_user_sab(G_tilde, W)
        assert np.all(sab >= 0)

    def test_sab_single_user_matches_single_column(self):
        from aegis.mimo.compute import compute_user_sab

        rng = np.random.default_rng(2)
        M_tri, M_ant = 30, 4
        G_tilde = rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))
        w = rng.standard_normal((M_ant, 1)) + 1j * rng.standard_normal((M_ant, 1))
        sab = compute_user_sab(G_tilde, w)
        expected = np.array([np.linalg.norm(G_tilde[m] @ w[:, 0]) ** 2 for m in range(M_tri)])
        np.testing.assert_allclose(sab, expected, atol=1e-10)


class TestComputeExposureQuadratic:
    def test_exposure_from_Q(self):
        from aegis.mimo.compute import compute_total_exposure

        M_ant, K = 4, 2
        rng = np.random.default_rng(3)
        A = rng.standard_normal((M_ant, M_ant)) + 1j * rng.standard_normal((M_ant, M_ant))
        Q = A.conj().T @ A
        W = rng.standard_normal((M_ant, K)) + 1j * rng.standard_normal((M_ant, K))
        p_abs = compute_total_exposure(Q, W)
        expected = np.real(np.trace(W.conj().T @ Q @ W))
        np.testing.assert_allclose(p_abs, expected, atol=1e-10)
        assert p_abs >= 0
