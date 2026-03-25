"""Tests for the MIMO scene orchestrator and compute helpers (compute.py)."""

from __future__ import annotations

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.mimo import AntennaArray, MIMOScene, UserConfig, UserState
from aegis.mimo.compute import (
    build_user_channels,
    compute_mimo_scene,
    compute_mrt_precoder,
    compute_multistream_sab,
    compute_total_exposure,
    compute_user_sab,
)
from aegis.mimo.precoders import compute_precoder
from aegis.paths import PropagationPaths
from aegis.precoder import Precoder
from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import make_icosahedron

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_center_paths(rng, n_paths=5):
    """Create synthetic center-of-array paths pointing roughly toward -x."""
    k_hat = rng.standard_normal((n_paths, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    k_hat[:, 0] = -np.abs(k_hat[:, 0])
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    psi = rng.standard_normal((n_paths, 3)) + 1j * rng.standard_normal((n_paths, 3))
    psi *= 0.01
    return PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=np.zeros(n_paths, dtype=int),
        delay=np.zeros(n_paths),
        is_los=np.zeros(n_paths, dtype=bool),
    )


def _make_test_scene(rng, n_users=2, n_h=2, n_v=2, n_paths=5):
    freq_hz = 28e9
    array = AntennaArray.upa(
        n_h=n_h,
        n_v=n_v,
        d_h=0.5 * 3e8 / freq_hz,
        d_v=0.5 * 3e8 / freq_hz,
        center=np.array([5.0, 0.0, 1.5]),
        broadside=np.array([-1.0, 0.0, 0.0]),
    )
    users = []
    for i in range(n_users):
        body = make_icosahedron()
        config = UserConfig(
            user_id=f"user_{i}",
            phantom_name="thelonious",
            position=np.array([0.0, i * 1.0, 0.0]),
            device_position=np.array([0.25, i * 1.0, 1.4]),
            device_orientation=np.array([0.0, 0.0, 1.0]),
        )
        state = UserState(config=config, body=body)
        state.center_paths = _make_center_paths(rng, n_paths)
        users.append(state)
    return MIMOScene(
        array=array,
        users=users,
        freq_hz=freq_hz,
        total_power=1.0,
        tissue=SKIN_28GHZ,
    )


# ---------------------------------------------------------------------------
# TestBuildUserChannels
# ---------------------------------------------------------------------------


class TestBuildUserChannels:
    def test_fills_all_fields(self):
        rng = np.random.default_rng(42)
        scene = _make_test_scene(rng, n_users=2, n_h=2, n_v=2, n_paths=5)
        M_ant = scene.array.n_elements  # 4
        M_tri = 20  # icosahedron

        build_user_channels(scene)

        for user in scene.users:
            assert user.paths is not None
            assert user.G_tilde is not None
            assert user.Q is not None
            assert user.h is not None

            # Shape checks
            assert user.G_tilde.shape == (M_tri, 3, M_ant)
            assert user.Q.shape == (M_ant, M_ant)
            assert user.h.shape == (M_ant,)

    def test_Q_is_hermitian_psd(self):
        rng = np.random.default_rng(99)
        scene = _make_test_scene(rng, n_users=2, n_h=2, n_v=2, n_paths=5)

        build_user_channels(scene)

        for user in scene.users:
            Q = user.Q
            # Hermitian
            np.testing.assert_allclose(Q, Q.conj().T, atol=1e-12)
            # Positive semidefinite
            eigvals = np.linalg.eigvalsh(Q)
            assert np.all(eigvals >= -1e-12)


# ---------------------------------------------------------------------------
# TestComputeMultistreamSab
# ---------------------------------------------------------------------------


class TestComputeMultistreamSab:
    def test_single_column_matches_single_user(self):
        """W=(M,1), sab matches ||G_tilde @ x||^2."""
        rng = np.random.default_rng(7)
        scene = _make_test_scene(rng, n_users=1, n_h=2, n_v=2, n_paths=5)
        build_user_channels(scene)

        user = scene.users[0]
        x = rng.standard_normal(scene.array.n_elements) + 1j * rng.standard_normal(scene.array.n_elements)
        W = x.reshape(-1, 1)

        sab = compute_multistream_sab(user.G_tilde, W)

        # Reference: per-triangle ||G_tilde[m] @ x||^2
        Gx = np.einsum("mia,a->mi", user.G_tilde, x)
        sab_ref = np.sum(np.abs(Gx) ** 2, axis=1)

        np.testing.assert_allclose(sab, sab_ref, rtol=1e-12)

    def test_nonnegative(self):
        rng = np.random.default_rng(8)
        scene = _make_test_scene(rng, n_users=2, n_h=2, n_v=2, n_paths=5)
        build_user_channels(scene)

        H = scene.all_h()
        W = compute_precoder(H, "zf", P=scene.total_power)

        for user in scene.users:
            sab = compute_multistream_sab(user.G_tilde, W)
            assert np.all(sab >= 0)

    def test_additivity(self):
        """sab(W) = sum_k sab(w_k)."""
        rng = np.random.default_rng(9)
        scene = _make_test_scene(rng, n_users=2, n_h=2, n_v=2, n_paths=5)
        build_user_channels(scene)

        H = scene.all_h()
        W = compute_precoder(H, "zf", P=scene.total_power)
        K = W.shape[1]

        user = scene.users[0]
        sab_full = compute_multistream_sab(user.G_tilde, W)

        sab_sum = np.zeros_like(sab_full)
        for k in range(K):
            w_k = W[:, k : k + 1]
            sab_sum += compute_multistream_sab(user.G_tilde, w_k)

        np.testing.assert_allclose(sab_full, sab_sum, rtol=1e-12)


# ---------------------------------------------------------------------------
# TestComputeMIMOScene
# ---------------------------------------------------------------------------


class TestComputeMIMOScene:
    def test_two_user_zf(self):
        rng = np.random.default_rng(10)
        scene = _make_test_scene(rng, n_users=2, n_h=2, n_v=2, n_paths=5)
        engine = DosimetryEngine(SKIN_28GHZ)

        out = compute_mimo_scene(scene, engine, precoder_type="zf")

        # W shape
        M_ant = scene.array.n_elements
        K = scene.n_users
        assert out["W"].shape == (M_ant, K)

        # Per-user results
        for user in scene.users:
            assert user.result is not None
            assert user.result.sab.shape == (20,)
            assert user.result.p_abs >= 0
            assert user.result.fidelity_level == 7
            assert user.result.sab_averaged is not None

        # per_user_p_abs
        assert len(out["per_user_p_abs"]) == K
        for p in out["per_user_p_abs"]:
            assert p >= 0

    def test_single_user_equivalence(self):
        """K=1 MRT matches engine.compute(level=7, precoder=Precoder.mrt(h, P))."""
        rng = np.random.default_rng(11)
        scene = _make_test_scene(rng, n_users=1, n_h=2, n_v=2, n_paths=5)
        engine = DosimetryEngine(SKIN_28GHZ)

        compute_mimo_scene(scene, engine, precoder_type="mrt")
        mimo_result = scene.users[0].result

        # Single-user reference via existing engine
        user = scene.users[0]
        precoder = Precoder.mrt(user.h, P=scene.total_power)
        ref_result = engine.compute(
            user.body,
            user.paths,
            level=7,
            precoder=precoder,
            freq_hz=scene.freq_hz,
        )

        np.testing.assert_allclose(mimo_result.sab, ref_result.sab, rtol=1e-10)
        np.testing.assert_allclose(mimo_result.p_abs, ref_result.p_abs, rtol=1e-10)

    def test_p_abs_matches_trace(self):
        """p_abs from sab integration matches trace(W^H Q W)."""
        rng = np.random.default_rng(12)
        scene = _make_test_scene(rng, n_users=2, n_h=2, n_v=2, n_paths=5)
        engine = DosimetryEngine(SKIN_28GHZ)

        out = compute_mimo_scene(scene, engine, precoder_type="zf")
        W = out["W"]

        for user in scene.users:
            p_abs_sab = user.result.p_abs
            p_abs_trace = float(np.real(np.trace(W.conj().T @ user.Q @ W)))
            np.testing.assert_allclose(p_abs_sab, p_abs_trace, rtol=1e-6)

    def test_all_precoder_types(self):
        rng = np.random.default_rng(13)
        scene = _make_test_scene(rng, n_users=2, n_h=2, n_v=2, n_paths=5)
        engine = DosimetryEngine(SKIN_28GHZ)

        for ptype in ["mrt", "zf", "mmse", "zf_exposure"]:
            # Reset results so build_user_channels does not skip
            for user in scene.users:
                user.result = None

            compute_mimo_scene(scene, engine, precoder_type=ptype)
            for user in scene.users:
                assert user.result is not None
                assert np.all(user.result.sab >= 0)


# ---------------------------------------------------------------------------
# TestMRTPrecoder
# ---------------------------------------------------------------------------


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
        H = np.array([[1 + 0j, 0.5 + 0.5j], [0.5 - 0.5j, 1 + 0j]])
        W = compute_mrt_precoder(H, total_power=1.0)
        assert W.shape == (2, 2)

    def test_mrt_conjugate_direction(self):
        h = np.array([[1 + 1j, 0 + 0j]])
        W = compute_mrt_precoder(h, total_power=1.0)
        expected_dir = np.conj(h[0]) / np.linalg.norm(h[0])
        actual_dir = W[:, 0] / np.linalg.norm(W[:, 0])
        np.testing.assert_allclose(actual_dir, expected_dir, atol=1e-10)

    def test_mrt_equal_power_per_user(self):
        H = np.array([[1 + 0j, 0 + 0j], [0 + 0j, 1 + 0j]])
        P = 2.0
        W = compute_mrt_precoder(H, total_power=P)
        for k in range(2):
            np.testing.assert_allclose(np.linalg.norm(W[:, k]) ** 2, P / 2, atol=1e-10)

    def test_mrt_total_power(self):
        rng = np.random.default_rng(42)
        H = rng.standard_normal((3, 8)) + 1j * rng.standard_normal((3, 8))
        P = 5.0
        W = compute_mrt_precoder(H, total_power=P)
        np.testing.assert_allclose(np.linalg.norm(W, "fro") ** 2, P, atol=1e-10)


# ---------------------------------------------------------------------------
# TestComputeUserSab
# ---------------------------------------------------------------------------


class TestComputeUserSab:
    def test_sab_shape(self):
        M_tri, M_ant, K = 100, 4, 2
        rng = np.random.default_rng(0)
        G_tilde = rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))
        W = rng.standard_normal((M_ant, K)) + 1j * rng.standard_normal((M_ant, K))
        sab = compute_user_sab(G_tilde, W)
        assert sab.shape == (M_tri,)

    def test_sab_nonnegative(self):
        rng = np.random.default_rng(1)
        G_tilde = rng.standard_normal((50, 3, 4)) + 1j * rng.standard_normal((50, 3, 4))
        W = rng.standard_normal((4, 2)) + 1j * rng.standard_normal((4, 2))
        sab = compute_user_sab(G_tilde, W)
        assert np.all(sab >= 0)

    def test_sab_single_user_matches_single_column(self):
        rng = np.random.default_rng(2)
        M_tri, M_ant = 30, 4
        G_tilde = rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))
        w = rng.standard_normal((M_ant, 1)) + 1j * rng.standard_normal((M_ant, 1))
        sab = compute_user_sab(G_tilde, w)
        expected = np.array([np.linalg.norm(G_tilde[m] @ w[:, 0]) ** 2 for m in range(M_tri)])
        np.testing.assert_allclose(sab, expected, atol=1e-10)


# ---------------------------------------------------------------------------
# TestComputeExposureQuadratic
# ---------------------------------------------------------------------------


class TestComputeExposureQuadratic:
    def test_exposure_from_Q(self):
        M_ant, K = 4, 2
        rng = np.random.default_rng(3)
        A = rng.standard_normal((M_ant, M_ant)) + 1j * rng.standard_normal((M_ant, M_ant))
        Q = A.conj().T @ A
        W = rng.standard_normal((M_ant, K)) + 1j * rng.standard_normal((M_ant, K))
        p_abs = compute_total_exposure(Q, W)
        expected = np.real(np.trace(W.conj().T @ Q @ W))
        np.testing.assert_allclose(p_abs, expected, atol=1e-10)
        assert p_abs >= 0
