"""Golden tests for multi-user MIMO dosimetry.

Deterministic inputs, verify numerical properties. If a test fails, physics changed.
"""

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.mimo import AntennaArray, MIMOScene, UserConfig, UserState
from aegis.mimo.compute import build_user_channels, compute_mimo_scene
from aegis.mimo.precoders import zf
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import make_icosahedron


def _deterministic_paths(seed, n_paths=3):
    rng = np.random.default_rng(seed)
    k_hat = rng.standard_normal((n_paths, 3))
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


@pytest.fixture
def golden_scene():
    """Deterministic 2-user scene with 2x2 UPA at 28 GHz."""
    freq_hz = 28e9
    lam = 3e8 / freq_hz
    array = AntennaArray.upa(
        n_h=2,
        n_v=2,
        d_h=0.5 * lam,
        d_v=0.5 * lam,
        center=np.array([5.0, 0.0, 1.5]),
        broadside=np.array([-1.0, 0.0, 0.0]),
    )
    users = []
    for i, seed in enumerate([1000, 2000]):
        config = UserConfig(
            user_id=f"golden_user_{i}",
            phantom_name="thelonious",
            position=np.array([0.0, i * 1.0, 0.0]),
            device_position=np.array([0.25, i * 1.0, 1.4]),
            device_orientation=np.array([0.0, 0.0, 1.0]),
        )
        state = UserState(config=config, body=make_icosahedron())
        state.center_paths = _deterministic_paths(seed)
        users.append(state)
    return MIMOScene(array=array, users=users, freq_hz=freq_hz, total_power=1.0, tissue=SKIN_28GHZ)


class TestGoldenTwoUserZF:
    def test_zf_zero_interference(self, golden_scene):
        """H @ W should be diagonal."""
        build_user_channels(golden_scene)
        H = golden_scene.all_h()
        W = zf(H, P=golden_scene.total_power)
        HW = H @ W
        off_diag = HW - np.diag(np.diag(HW))
        np.testing.assert_allclose(np.abs(off_diag), 0, atol=1e-10)

    def test_p_abs_trace_consistency(self, golden_scene):
        """P_abs from sab must match trace(W^H Q W) for both users."""
        engine = DosimetryEngine(SKIN_28GHZ)
        result = compute_mimo_scene(golden_scene, engine, precoder_type="zf")
        W = result["W"]
        for user in golden_scene.users:
            p_abs_sab = user.result.p_abs
            p_abs_trace = float(np.real(np.trace(W.conj().T @ user.Q @ W)))
            np.testing.assert_allclose(p_abs_sab, p_abs_trace, rtol=1e-5)

    def test_sab_nonnegative(self, golden_scene):
        engine = DosimetryEngine(SKIN_28GHZ)
        compute_mimo_scene(golden_scene, engine, precoder_type="zf")
        for user in golden_scene.users:
            assert np.all(user.result.sab >= -1e-15)

    def test_total_power_conservation(self, golden_scene):
        """Sum of absorbed power across all bodies <= total transmit power."""
        engine = DosimetryEngine(SKIN_28GHZ)
        result = compute_mimo_scene(golden_scene, engine, precoder_type="zf")
        total_p_abs = sum(result["per_user_p_abs"])
        assert total_p_abs <= golden_scene.total_power + 1e-10

    def test_deterministic_results(self, golden_scene):
        """Running twice with same inputs gives identical results."""
        engine = DosimetryEngine(SKIN_28GHZ)
        compute_mimo_scene(golden_scene, engine, precoder_type="zf")
        sab1 = [u.result.sab.copy() for u in golden_scene.users]
        for u in golden_scene.users:
            u.result = None
        compute_mimo_scene(golden_scene, engine, precoder_type="zf")
        for i, user in enumerate(golden_scene.users):
            np.testing.assert_array_equal(sab1[i], user.result.sab)
