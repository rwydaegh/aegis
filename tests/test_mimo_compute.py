"""Tests for the MIMO orchestrator and multi-user compute pipeline.

Covers: compute_per_user_channels, compute_multiuser_sab, compute_mimo_scene,
and the full end-to-end MIMO pipeline.
"""

import numpy as np
import pytest

from aegis.mimo.array import AntennaArray
from aegis.mimo.compute import (
    MIMOResult,
    compute_mimo_scene,
    compute_multiuser_sab,
    compute_per_user_channels,
)
from aegis.mimo.precoders import PrecoderMatrix, mrt, zf
from aegis.mimo.scene import MIMOScene
from aegis.mimo.user import UserConfig, UserState
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import make_flat_mesh

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_two_user_scene(M_ant=4):
    """Create a deterministic 2-user MIMO scene with flat meshes."""
    freq_hz = 28e9
    array = AntennaArray.upa(
        2, M_ant // 2, 0.005, 0.005, center=np.array([5.0, 0.0, 3.0]), broadside=np.array([-1.0, 0.0, 0.0])
    )

    # User 1: body at origin, device in front
    cfg1 = UserConfig(
        user_id="user1",
        phantom_name="flat",
        position=np.array([0.0, 0.0, 0.0]),
        device_position=np.array([0.3, 0.0, 1.0]),
        device_orientation=np.array([0.0, 0.0, 1.0]),
    )
    # User 2: body offset to the side
    cfg2 = UserConfig(
        user_id="user2",
        phantom_name="flat",
        position=np.array([0.0, 3.0, 0.0]),
        device_position=np.array([0.3, 3.0, 1.0]),
        device_orientation=np.array([0.0, 0.0, 1.0]),
    )

    body1 = make_flat_mesh(n=20)
    body2 = make_flat_mesh(n=20)

    # Simple paths: single LOS from array center to each user
    k_hat1 = np.array([[-1.0, 0.0, 0.0]])
    k_hat2 = np.array([[0.0, -1.0, 0.0]])

    psi1 = np.array([[0.0, 0.0, 1.0 + 0j]])  # vertically polarized
    psi2 = np.array([[0.0, 0.0, 1.0 + 0j]])

    center_paths1 = PropagationPaths(
        k_hat=k_hat1,
        psi=psi1,
        element_index=np.array([0]),
        delay=np.array([0.0]),
        is_los=np.array([True]),
    )
    center_paths2 = PropagationPaths(
        k_hat=k_hat2,
        psi=psi2,
        element_index=np.array([0]),
        delay=np.array([0.0]),
        is_los=np.array([True]),
    )

    # Expand paths to per-element
    from aegis.mimo.array_paths import expand_paths_to_array

    paths1 = expand_paths_to_array(center_paths1, array, freq_hz)
    paths2 = expand_paths_to_array(center_paths2, array, freq_hz)

    user1 = UserState(config=cfg1, body=body1, paths=paths1, center_paths=center_paths1)
    user2 = UserState(config=cfg2, body=body2, paths=paths2, center_paths=center_paths2)

    scene = MIMOScene(
        array=array,
        users=[user1, user2],
        freq_hz=freq_hz,
        total_power=1.0,
        tissue=SKIN_28GHZ,
    )
    return scene


# ---------------------------------------------------------------------------
# compute_per_user_channels
# ---------------------------------------------------------------------------


class TestComputePerUserChannels:
    def test_populates_G_tilde(self):
        scene = make_two_user_scene()
        compute_per_user_channels(scene)

        for user in scene.users:
            assert user.G_tilde is not None
            assert user.G_tilde.shape == (20, 3, scene.array.n_elements)

    def test_populates_Q(self):
        scene = make_two_user_scene()
        compute_per_user_channels(scene)

        M = scene.array.n_elements
        for user in scene.users:
            assert user.Q is not None
            assert user.Q.shape == (M, M)
            # Q should be Hermitian
            np.testing.assert_allclose(user.Q, user.Q.conj().T, atol=1e-12)
            # Q should be PSD (eigenvalues >= 0)
            eigs = np.linalg.eigvalsh(user.Q)
            assert np.all(eigs >= -1e-12)

    def test_populates_h(self):
        scene = make_two_user_scene()
        compute_per_user_channels(scene)

        M = scene.array.n_elements
        for user in scene.users:
            assert user.h is not None
            assert user.h.shape == (M,)

    def test_raises_without_tissue(self):
        scene = make_two_user_scene()
        scene.tissue = None
        with pytest.raises(ValueError, match="TissueModel"):
            compute_per_user_channels(scene)

    def test_raises_without_body(self):
        scene = make_two_user_scene()
        scene.users[0].body = None
        with pytest.raises(ValueError, match="no body"):
            compute_per_user_channels(scene)


# ---------------------------------------------------------------------------
# compute_multiuser_sab
# ---------------------------------------------------------------------------


class TestComputeMultiuserSab:
    def test_nonneg(self):
        """Sab should always be non-negative."""
        rng = np.random.default_rng(42)
        M_tri, M_ant, K = 20, 4, 2
        G_tilde = (rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))) / np.sqrt(2)
        W = (rng.standard_normal((M_ant, K)) + 1j * rng.standard_normal((M_ant, K))) / np.sqrt(2)

        sab = compute_multiuser_sab(G_tilde, W)
        assert sab.shape == (M_tri,)
        assert np.all(sab >= 0)

    def test_single_stream_matches_level7(self):
        """Single-stream Sab should match ||G_tilde @ w||^2."""
        rng = np.random.default_rng(42)
        M_tri, M_ant = 10, 4
        G_tilde = (rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))) / np.sqrt(2)
        x = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)

        # Single-stream: W = x[:, None]
        sab_multi = compute_multiuser_sab(G_tilde, x[:, np.newaxis])

        # Direct computation
        field = np.einsum("mia,a->mi", G_tilde, x)
        sab_direct = np.real(np.sum(np.conj(field) * field, axis=1))

        np.testing.assert_allclose(sab_multi, sab_direct, rtol=1e-10)

    def test_linearity_in_power(self):
        """Doubling W should quadruple Sab (power is quadratic in field)."""
        rng = np.random.default_rng(42)
        M_tri, M_ant, K = 10, 4, 2
        G_tilde = (rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))) / np.sqrt(2)
        W = (rng.standard_normal((M_ant, K)) + 1j * rng.standard_normal((M_ant, K))) / np.sqrt(2)

        sab1 = compute_multiuser_sab(G_tilde, W)
        sab2 = compute_multiuser_sab(G_tilde, 2 * W)

        np.testing.assert_allclose(sab2, 4 * sab1, rtol=1e-10)


# ---------------------------------------------------------------------------
# compute_mimo_scene (full pipeline)
# ---------------------------------------------------------------------------


class TestComputeMIMOScene:
    def test_full_pipeline(self):
        """End-to-end: scene -> channels -> precoder -> results."""
        scene = make_two_user_scene()
        compute_per_user_channels(scene)

        H = scene.all_h()
        precoder = mrt(H, P=scene.total_power)

        result = compute_mimo_scene(scene, precoder)

        assert isinstance(result, MIMOResult)
        assert len(result.user_results) == 2
        assert "user1" in result.user_results
        assert "user2" in result.user_results

        for _uid, dr in result.user_results.items():
            assert dr.sab.shape == (20,)
            assert np.all(dr.sab >= 0)
            assert dr.p_abs >= 0
            assert dr.fidelity_level == 7

    def test_p_abs_consistency(self):
        """P_abs from trace(W^H Q W) should match sum(sab * areas)."""
        scene = make_two_user_scene()
        compute_per_user_channels(scene)

        H = scene.all_h()
        precoder = mrt(H, P=scene.total_power)
        result = compute_mimo_scene(scene, precoder)

        for user in scene.users:
            uid = user.config.user_id
            dr = result.user_results[uid]

            # P_abs from trace formula
            p_abs_trace = result.user_p_abs[uid]

            # P_abs from integrating sab over body surface
            p_abs_integral = float(np.sum(dr.sab * user.body.areas))

            # These use different computation paths, should agree
            np.testing.assert_allclose(p_abs_trace, p_abs_integral, rtol=0.05)

    def test_zf_pipeline(self):
        """Full pipeline with ZF precoder."""
        scene = make_two_user_scene()
        compute_per_user_channels(scene)

        H = scene.all_h()
        precoder = zf(H, P=scene.total_power)

        result = compute_mimo_scene(scene, precoder)
        assert result.total_p_abs >= 0

    def test_dimension_mismatch_raises(self):
        """Precoder with wrong number of elements should raise."""
        scene = make_two_user_scene()
        compute_per_user_channels(scene)

        # Wrong M_ant
        wrong_W = np.eye(8, 2, dtype=complex)
        precoder = PrecoderMatrix(W=wrong_W, method="test")

        with pytest.raises(ValueError, match="elements"):
            compute_mimo_scene(scene, precoder)

    def test_user_count_mismatch_raises(self):
        """Precoder serving wrong number of users should raise."""
        scene = make_two_user_scene()
        compute_per_user_channels(scene)

        M = scene.array.n_elements
        wrong_W = np.eye(M, 3, dtype=complex)  # 3 users, scene has 2
        precoder = PrecoderMatrix(W=wrong_W, method="test")

        with pytest.raises(ValueError, match="users"):
            compute_mimo_scene(scene, precoder)

    def test_stores_result_on_user_state(self):
        """compute_mimo_scene should populate user.result."""
        scene = make_two_user_scene()
        compute_per_user_channels(scene)

        H = scene.all_h()
        precoder = mrt(H, P=scene.total_power)
        compute_mimo_scene(scene, precoder)

        for user in scene.users:
            assert user.result is not None
            assert user.result.sab is not None


# ---------------------------------------------------------------------------
# Single-element equivalence
# ---------------------------------------------------------------------------


class TestSingleElementEquivalence:
    def test_single_element_mrt_matches_level7(self):
        """K=1, M=1 MRT through the orchestrator should match engine level 7."""
        from aegis.engine import DosimetryEngine
        from aegis.precoder import Precoder

        freq_hz = 28e9
        array = AntennaArray.upa(
            1, 1, 0.005, 0.005, center=np.array([5.0, 0.0, 3.0]), broadside=np.array([-1.0, 0.0, 0.0])
        )

        body = make_flat_mesh(n=20)
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[0.0, 1.0 + 0j, 0.0]])

        center_paths = PropagationPaths(
            k_hat=k_hat,
            psi=psi,
            element_index=np.array([0]),
            delay=np.array([0.0]),
            is_los=np.array([True]),
        )

        from aegis.mimo.array_paths import expand_paths_to_array

        paths = expand_paths_to_array(center_paths, array, freq_hz)

        cfg = UserConfig(
            user_id="solo",
            phantom_name="flat",
            position=np.zeros(3),
            device_position=np.array([0.3, 0.0, 1.0]),
            device_orientation=np.array([0.0, 0.0, 1.0]),
        )
        user = UserState(config=cfg, body=body, paths=paths, center_paths=center_paths)

        scene = MIMOScene(
            array=array,
            users=[user],
            freq_hz=freq_hz,
            total_power=1.0,
            tissue=SKIN_28GHZ,
        )

        # MIMO pipeline
        compute_per_user_channels(scene)
        H = scene.all_h()
        precoder_matrix = mrt(H, P=1.0)
        mimo_result = compute_mimo_scene(scene, precoder_matrix)

        # Engine level 7 pipeline
        engine = DosimetryEngine(SKIN_28GHZ)
        precoder_single = Precoder.mrt(user.h, P=1.0)
        engine_result = engine.compute(body, paths, level=7, precoder=precoder_single, h=user.h)

        # Sab should be proportional (may differ by global phase alignment)
        # Total absorbed power should match
        np.testing.assert_allclose(
            mimo_result.user_results["solo"].p_abs,
            engine_result.p_abs,
            rtol=0.1,  # relaxed due to multi-stream vs single-stream formulation
        )
