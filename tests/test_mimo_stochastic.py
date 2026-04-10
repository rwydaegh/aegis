"""Tests for stochastic channel + MIMO pipeline integration."""

from pathlib import Path

import numpy as np

from aegis.channel.presets import load_preset
from aegis.constants import C_0
from aegis.mimo.array import AntennaArray
from aegis.mimo.compute import make_stochastic_paths_fn
from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import NUMERICAL_FLOOR, make_icosahedron

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "channel_presets"
PRESET_NAME = "3GPP_38.901_UMi_LOS"


def _make_array(freq_hz: float = 28e9) -> AntennaArray:
    """4x4 UPA at (5, 0, 3) pointing toward origin."""
    lam = C_0 / freq_hz
    return AntennaArray.upa(
        n_h=4,
        n_v=4,
        d_h=0.5 * lam,
        d_v=0.5 * lam,
        center=np.array([5.0, 0.0, 3.0]),
        broadside=np.array([-1.0, 0.0, 0.0]),
    )


class TestStochasticPathsFactory:
    """Tests for make_stochastic_paths_fn."""

    def test_returns_valid_paths(self):
        """Factory returns PropagationPaths with correct fields."""
        preset = load_preset(PRESET_NAME, DATA_DIR)
        fn = make_stochastic_paths_fn(
            params=preset["params"],
            freq_ghz=28.0,
            power_dbm=30.0,
            base_seed=42,
        )
        body = make_icosahedron()
        paths = fn(body, np.array([5.0, 0.0, 3.0]), 28e9, np.array([0.0, 0.0, 1.5]))

        assert paths.n_paths > 0
        assert paths.k_hat.shape == (paths.n_paths, 3)
        assert paths.psi.shape == (paths.n_paths, 3)
        assert np.all(np.isfinite(paths.k_hat))
        assert np.all(np.isfinite(paths.psi))
        assert np.all(paths.power >= 0)

    def test_per_user_seed_independence(self):
        """Successive calls use different seeds, producing different paths."""
        preset = load_preset(PRESET_NAME, DATA_DIR)
        fn = make_stochastic_paths_fn(
            params=preset["params"],
            freq_ghz=28.0,
            power_dbm=30.0,
            base_seed=42,
        )
        body = make_icosahedron()
        arr_center = np.array([5.0, 0.0, 3.0])

        paths_0 = fn(body, arr_center, 28e9, np.array([0.0, 0.0, 1.5]))
        paths_1 = fn(body, arr_center, 28e9, np.array([0.0, 2.0, 1.5]))

        # k_hat should differ because seeds differ
        assert not np.allclose(paths_0.k_hat, paths_1.k_hat)

    def test_viz_collector_populated(self):
        """viz_collector receives cluster data for each call."""
        preset = load_preset(PRESET_NAME, DATA_DIR)
        viz_collector: list[dict] = []
        fn = make_stochastic_paths_fn(
            params=preset["params"],
            freq_ghz=28.0,
            power_dbm=30.0,
            base_seed=42,
            viz_collector=viz_collector,
        )
        body = make_icosahedron()
        fn(body, np.array([5.0, 0.0, 3.0]), 28e9, None)
        fn(body, np.array([5.0, 0.0, 3.0]), 28e9, None)

        assert len(viz_collector) == 2
        assert "n_clusters" in viz_collector[0]
        assert "cluster_power" in viz_collector[0]

    def test_seed_determinism(self):
        """Same base_seed produces identical paths."""
        preset = load_preset(PRESET_NAME, DATA_DIR)
        body = make_icosahedron()
        arr_center = np.array([5.0, 0.0, 3.0])

        fn1 = make_stochastic_paths_fn(preset["params"], 28.0, 30.0, base_seed=99)
        fn2 = make_stochastic_paths_fn(preset["params"], 28.0, 30.0, base_seed=99)

        p1 = fn1(body, arr_center, 28e9, None)
        p2 = fn2(body, arr_center, 28e9, None)

        np.testing.assert_array_equal(p1.k_hat, p2.k_hat)
        np.testing.assert_array_equal(p1.psi, p2.psi)


class TestMISOEndToEnd:
    """Single-user MIMO with stochastic channel (MISO = 1 user, M antennas)."""

    def test_level7_sab_nonneg_and_finite(self):
        """Stochastic paths -> 4x4 array -> Level 7 -> valid SAB."""
        from aegis.coherent.body_channel import compute_body_channel_factored
        from aegis.coherent.exposure_operator import compute_exposure_operator
        from aegis.mimo.array_paths import expand_paths_to_array
        from aegis.mimo.channel import compute_channel_vector

        freq_hz = 28e9
        tissue = SKIN_28GHZ
        arr = _make_array(freq_hz)
        body = make_icosahedron()

        preset = load_preset(PRESET_NAME, DATA_DIR)
        fn = make_stochastic_paths_fn(preset["params"], 28.0, 30.0, base_seed=42)
        center_paths = fn(body, arr.reference_position, freq_hz, np.array([0.0, 0.0, 1.5]))

        # Expand to per-element paths
        expanded = expand_paths_to_array(center_paths, arr, freq_hz)
        assert expanded.n_paths == center_paths.n_paths * arr.n_elements

        # Body channel
        G_tilde = compute_body_channel_factored(
            normals=body.normals,
            centroids=body.centroids,
            center_k_hat=center_paths.k_hat,
            center_psi=center_paths.psi,
            element_psi=expanded.psi,
            element_index=expanded.element_index,
            n_tilde=tissue.n_complex,
            sigma=tissue.sigma,
            freq_hz=freq_hz,
            n_elements=arr.n_elements,
        )
        assert G_tilde.shape == (body.n_triangles, 3, arr.n_elements)

        # Exposure operator Q
        Q = compute_exposure_operator(G_tilde, body.areas)
        assert Q.shape == (arr.n_elements, arr.n_elements)
        # Hermitian
        np.testing.assert_allclose(Q, Q.conj().T, atol=1e-12)
        # PSD (eigenvalues >= 0)
        eigs = np.linalg.eigvalsh(Q)
        assert np.all(eigs >= NUMERICAL_FLOOR)

        # Communication channel h
        h = compute_channel_vector(
            center_paths,
            arr,
            device_position=np.array([0.0, 0.0, 1.5]),
            device_orientation=np.array([0.0, 0.0, 1.0]),
            freq_hz=freq_hz,
        )
        assert h.shape == (arr.n_elements,)
        assert np.linalg.norm(h) > 0

        # MRT precoder
        x = np.conj(h) / np.linalg.norm(h)

        # SAB = ||G_tilde @ x||^2 per triangle
        field = np.einsum("mia,a->mi", G_tilde, x)
        sab = np.real(np.sum(np.conj(field) * field, axis=1))

        assert sab.shape == (body.n_triangles,)
        assert np.all(np.isfinite(sab))
        assert np.all(sab >= NUMERICAL_FLOOR)


class TestMIMOEndToEnd:
    """Multi-user MIMO with stochastic channel."""

    def test_two_user_mrt(self):
        """2-user MIMO with stochastic channel and MRT precoder."""
        from aegis.mimo.compute import compute_mimo_scene_with_bodies, make_stochastic_paths_fn
        from aegis.mimo.scene import MIMOScene
        from aegis.mimo.user import UserConfig, UserState

        freq_hz = 28e9
        arr = _make_array(freq_hz)

        users = []
        for i in range(2):
            cfg = UserConfig(
                user_id=f"user_{i}",
                phantom_name="icosahedron",
                position=np.array([0.0, float(i) * 2, 0.0]),
                device_position=np.array([0.25, float(i) * 2, 1.4]),
                device_orientation=np.array([0.0, 0.0, 1.0]),
            )
            users.append(UserState(config=cfg))

        scene = MIMOScene(
            array=arr,
            users=users,
            freq_hz=freq_hz,
            total_power=1.0,
            tissue=SKIN_28GHZ,
        )

        preset = load_preset(PRESET_NAME, DATA_DIR)
        gen_fn = make_stochastic_paths_fn(preset["params"], 28.0, 30.0, base_seed=42)

        # Use icosahedron as the body for both users
        bodies = {"icosahedron": make_icosahedron()}

        summary = compute_mimo_scene_with_bodies(
            scene,
            bodies,
            level=7,
            generate_paths_fn=gen_fn,
            precoder_type="mrt",
        )

        assert "user_ids" in summary
        assert len(summary["user_ids"]) == 2

        # Verify per-user results
        for user in scene.users:
            assert user.result is not None
            sab = user.result.sab
            assert np.all(np.isfinite(sab))
            assert np.all(sab >= NUMERICAL_FLOOR)
            assert user.Q is not None
            assert user.h is not None

    def test_two_user_zf(self):
        """2-user MIMO with stochastic channel and ZF precoder."""
        from aegis.mimo.compute import compute_mimo_scene_with_bodies, make_stochastic_paths_fn
        from aegis.mimo.scene import MIMOScene
        from aegis.mimo.user import UserConfig, UserState

        freq_hz = 28e9
        arr = _make_array(freq_hz)

        users = []
        for i in range(2):
            cfg = UserConfig(
                user_id=f"user_{i}",
                phantom_name="icosahedron",
                position=np.array([0.0, float(i) * 2, 0.0]),
                device_position=np.array([0.25, float(i) * 2, 1.4]),
                device_orientation=np.array([0.0, 0.0, 1.0]),
            )
            users.append(UserState(config=cfg))

        scene = MIMOScene(
            array=arr,
            users=users,
            freq_hz=freq_hz,
            total_power=1.0,
            tissue=SKIN_28GHZ,
        )

        preset = load_preset(PRESET_NAME, DATA_DIR)
        gen_fn = make_stochastic_paths_fn(preset["params"], 28.0, 30.0, base_seed=42)
        bodies = {"icosahedron": make_icosahedron()}

        summary = compute_mimo_scene_with_bodies(
            scene,
            bodies,
            level=7,
            generate_paths_fn=gen_fn,
            precoder_type="zf",
        )

        assert len(summary["user_ids"]) == 2
        for user in scene.users:
            assert user.result is not None
            assert np.all(np.isfinite(user.result.sab))
