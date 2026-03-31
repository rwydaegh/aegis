"""Integration tests for the MIMO pipeline.

These tests verify that the MIMO building blocks compose correctly
and that the K=1 case matches the existing single-user coherent pipeline.
"""

import numpy as np

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.exposure_operator import compute_exposure_operator
from aegis.constants import C_0
from aegis.mimo.array import AntennaArray
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.mimo.channel import compute_channel_vector
from aegis.mimo.scene import MIMOScene
from aegis.mimo.user import UserConfig, UserState
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import NUMERICAL_FLOOR, make_flat_mesh, make_icosahedron


class TestSingleElementEquivalence:
    """Single-element array must reproduce the existing single-user pipeline."""

    def test_G_tilde_matches_single_user(self):
        """G_tilde from expanded paths matches direct single-user computation."""
        freq_hz = 28e9
        tissue = SKIN_28GHZ

        arr = AntennaArray.upa(
            n_h=1,
            n_v=1,
            d_h=0.005,
            d_v=0.005,
            center=np.zeros(3),
            broadside=np.array([1.0, 0, 0]),
        )

        rng = np.random.default_rng(42)
        N = 20
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 2.0, N)
        center_paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

        expanded = expand_paths_to_array(center_paths, arr, freq_hz)

        body = make_flat_mesh(50)

        G_mimo = compute_body_channel(
            body.normals,
            body.centroids,
            expanded.k_hat,
            expanded.psi,
            expanded.element_index,
            tissue.n_complex,
            tissue.sigma,
            freq_hz,
            n_elements=expanded.n_elements,
        )

        G_single = compute_body_channel(
            body.normals,
            body.centroids,
            center_paths.k_hat,
            center_paths.psi,
            np.zeros(N, dtype=np.intp),
            tissue.n_complex,
            tissue.sigma,
            freq_hz,
            n_elements=1,
        )

        np.testing.assert_allclose(G_mimo, G_single, atol=1e-12)

    def test_Q_matches_single_user(self):
        """Exposure operator from MIMO path matches single-user Q."""
        freq_hz = 28e9
        tissue = SKIN_28GHZ

        arr = AntennaArray.upa(
            n_h=1,
            n_v=1,
            d_h=0.005,
            d_v=0.005,
            center=np.zeros(3),
            broadside=np.array([1.0, 0, 0]),
        )
        rng = np.random.default_rng(42)
        N = 20
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 2.0, N)
        center_paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        expanded = expand_paths_to_array(center_paths, arr, freq_hz)

        body = make_flat_mesh(50)

        G = compute_body_channel(
            body.normals,
            body.centroids,
            expanded.k_hat,
            expanded.psi,
            expanded.element_index,
            tissue.n_complex,
            tissue.sigma,
            freq_hz,
            n_elements=1,
        )
        Q_mimo = compute_exposure_operator(G, body.areas)

        G_ref = compute_body_channel(
            body.normals,
            body.centroids,
            center_paths.k_hat,
            center_paths.psi,
            np.zeros(N, dtype=np.intp),
            tissue.n_complex,
            tissue.sigma,
            freq_hz,
            n_elements=1,
        )
        Q_ref = compute_exposure_operator(G_ref, body.areas)

        np.testing.assert_allclose(Q_mimo, Q_ref, atol=1e-12)


class TestMultiElementPipeline:
    """Multi-element array end-to-end test with synthetic data."""

    def test_expanded_paths_produce_valid_G_tilde(self):
        """4x4 array: expanded paths produce G_tilde with correct shape."""
        freq_hz = 28e9
        lam = C_0 / freq_hz
        tissue = SKIN_28GHZ

        arr = AntennaArray.upa(
            n_h=4,
            n_v=4,
            d_h=0.5 * lam,
            d_v=0.5 * lam,
            center=np.array([5.0, 0.0, 3.0]),
            broadside=np.array([-1.0, 0.0, 0.0]),
        )
        rng = np.random.default_rng(7)
        N = 10
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 1.0, N)
        center_paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        expanded = expand_paths_to_array(center_paths, arr, freq_hz)

        body = make_icosahedron()

        G_tilde = compute_body_channel(
            body.normals,
            body.centroids,
            expanded.k_hat,
            expanded.psi,
            expanded.element_index,
            tissue.n_complex,
            tissue.sigma,
            freq_hz,
            n_elements=arr.n_elements,
        )
        assert G_tilde.shape == (body.n_triangles, 3, 16)

        Q = compute_exposure_operator(G_tilde, body.areas)
        assert Q.shape == (16, 16)
        np.testing.assert_allclose(Q, Q.conj().T, atol=1e-12)
        eigenvalues = np.linalg.eigvalsh(Q)
        assert np.all(eigenvalues >= NUMERICAL_FLOOR)

    def test_channel_vector_with_expanded_paths(self):
        """Channel vector has correct shape and is nonzero."""
        freq_hz = 28e9
        lam = C_0 / freq_hz

        arr = AntennaArray.upa(
            n_h=4,
            n_v=4,
            d_h=0.5 * lam,
            d_v=0.5 * lam,
            center=np.array([5.0, 0.0, 3.0]),
            broadside=np.array([-1.0, 0.0, 0.0]),
        )
        rng = np.random.default_rng(7)
        N = 10
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 1.0, N)
        center_paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

        device_pos = np.array([0.0, 0.0, 1.5])
        device_ori = np.array([0.0, 0.0, 1.0])

        h = compute_channel_vector(center_paths, arr, device_pos, device_ori, freq_hz)
        assert h.shape == (16,)
        assert np.linalg.norm(h) > 0

    def test_full_scene_assembly(self):
        """MIMOScene can be assembled with populated UserStates."""
        freq_hz = 28e9
        lam = C_0 / freq_hz
        tissue = SKIN_28GHZ

        arr = AntennaArray.upa(
            n_h=4,
            n_v=4,
            d_h=0.5 * lam,
            d_v=0.5 * lam,
            center=np.array([5.0, 0.0, 3.0]),
            broadside=np.array([-1.0, 0.0, 0.0]),
        )

        users = []
        for i in range(2):
            cfg = UserConfig(
                user_id=f"user_{i}",
                phantom_name="thelonious",
                position=np.array([0.0, float(i) * 2, 0.0]),
                device_position=np.array([0.25, float(i) * 2, 1.4]),
                device_orientation=np.array([0.0, 0.0, 1.0]),
                orientation=0.0,
            )
            state = UserState(config=cfg)

            body = make_icosahedron()
            state.body = body

            rng = np.random.default_rng(42 + i)
            N = 10
            k_hat = rng.standard_normal((N, 3))
            k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
            power = rng.uniform(0.1, 1.0, N)
            center_paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
            state.center_paths = center_paths

            expanded = expand_paths_to_array(center_paths, arr, freq_hz)
            state.paths = expanded

            G_tilde = compute_body_channel(
                body.normals,
                body.centroids,
                expanded.k_hat,
                expanded.psi,
                expanded.element_index,
                tissue.n_complex,
                tissue.sigma,
                freq_hz,
                n_elements=arr.n_elements,
            )
            state.G_tilde = G_tilde
            state.Q = compute_exposure_operator(G_tilde, body.areas)
            state.h = compute_channel_vector(
                center_paths,
                arr,
                cfg.device_position,
                cfg.device_orientation,
                freq_hz,
            )
            users.append(state)

        scene = MIMOScene(
            array=arr,
            users=users,
            freq_hz=freq_hz,
            total_power=1.0,
            tissue=tissue,
        )

        assert scene.n_users == 2
        H = scene.all_h()
        assert H.shape == (2, 16)
        Qs = scene.all_Q()
        assert len(Qs) == 2
        for Q in Qs:
            assert Q.shape == (16, 16)
