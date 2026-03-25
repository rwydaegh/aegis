"""Tests for the MIMO scene orchestrator (compute.py)."""

from __future__ import annotations

import numpy as np

from aegis.engine import DosimetryEngine
from aegis.mimo import AntennaArray, MIMOScene, UserConfig, UserState
from aegis.mimo.compute import (
    build_user_channels,
    compute_mimo_scene,
    compute_multistream_sab,
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
