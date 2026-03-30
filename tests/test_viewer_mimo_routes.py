"""Tests for MIMO viewer API routes.

Covers: /api/mimo/compute, /api/mimo/result/<user_id>, /api/mimo/summary.
Tests input validation, error paths, and response formats using mocked compute.
"""

from __future__ import annotations

import json
import threading
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

pytest.importorskip("flask")

from flask import Flask  # noqa: E402

from aegis.mimo.user import UserConfig, UserState  # noqa: E402
from aegis.viewer.routes.mimo import _build_scene, _user_stats  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_ARRAY = {
    "n_h": 4,
    "n_v": 4,
    "d_h_wavelengths": 0.5,
    "d_v_wavelengths": 0.5,
    "position": [0.0, 0.0, 3.0],
    "broadside": [1.0, 0.0, 0.0],
    "element_pattern": "patch",
}


def _make_user_cfg(uid: str = "u1") -> dict:
    return {
        "id": uid,
        "phantom": "thelonious",
        "position": [5.0, 0.0, 0.0],
        "device_offset": [0.25, 0.0, 1.4],
    }


def _make_body_mock():
    """Minimal BodyMesh-like mock."""
    body = MagicMock()
    body.n_triangles = 10
    return body


def _make_cache_with_body():
    return {
        "bodies": {
            "thelonious": {"body": _make_body_mock()},
        },
        "default_body": "thelonious",
    }


@pytest.fixture
def app():
    """Flask app with MIMO routes registered."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    cache = _make_cache_with_body()
    cache_lock = threading.Lock()
    from aegis.viewer.routes.mimo import register

    register(app, cache, cache_lock)
    # Expose cache for manipulation in tests
    app._test_cache = cache
    app._test_cache_lock = cache_lock
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def _app_ctx(app):
    """Provide Flask app context for unit tests calling _build_scene."""
    with app.app_context():
        yield


# ---------------------------------------------------------------------------
# _build_scene unit tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_app_ctx")
class TestBuildScene:
    def test_missing_array_returns_error(self):
        cache = _make_cache_with_body()
        scene, err = _build_scene({"users": [_make_user_cfg()]}, cache)
        assert scene is None
        assert err is not None

    def test_missing_users_returns_error(self):
        cache = _make_cache_with_body()
        scene, err = _build_scene({"array": VALID_ARRAY}, cache)
        assert scene is None
        assert err is not None

    def test_empty_users_returns_error(self):
        cache = _make_cache_with_body()
        scene, err = _build_scene({"array": VALID_ARRAY, "users": []}, cache)
        assert scene is None
        assert err is not None

    def test_unknown_phantom_returns_404(self):
        cache = _make_cache_with_body()
        user = _make_user_cfg()
        user["phantom"] = "nonexistent"
        scene, err = _build_scene({"array": VALID_ARRAY, "users": [user]}, cache)
        assert scene is None
        resp, status = err
        assert status == 404

    def test_valid_input_returns_scene(self):
        cache = _make_cache_with_body()
        scene, err = _build_scene({"array": VALID_ARRAY, "users": [_make_user_cfg()]}, cache)
        assert err is None
        assert scene is not None
        assert scene.n_users == 1
        assert scene.users[0].config.user_id == "u1"

    def test_multiple_users(self):
        cache = _make_cache_with_body()
        users = [_make_user_cfg("u1"), _make_user_cfg("u2")]
        users[1]["position"] = [10.0, 0.0, 0.0]
        scene, err = _build_scene({"array": VALID_ARRAY, "users": users}, cache)
        assert err is None
        assert scene.n_users == 2

    def test_custom_freq_and_power(self):
        cache = _make_cache_with_body()
        params = {
            "array": VALID_ARRAY,
            "users": [_make_user_cfg()],
            "freq_hz": 3.5e9,
            "power_dbm": 40.0,
        }
        scene, err = _build_scene(params, cache)
        assert err is None
        assert scene.freq_hz == 3.5e9
        np.testing.assert_allclose(scene.total_power, 10.0 ** ((40 - 30) / 10))

    def test_invalid_array_missing_n_h(self):
        cache = _make_cache_with_body()
        bad_array = {**VALID_ARRAY}
        del bad_array["n_h"]
        scene, err = _build_scene({"array": bad_array, "users": [_make_user_cfg()]}, cache)
        assert scene is None
        resp, status = err
        assert status == 400

    def test_device_offset_adds_to_user_position(self):
        cache = _make_cache_with_body()
        user = _make_user_cfg()
        user["position"] = [5.0, 2.0, 0.0]
        user["device_offset"] = [0.25, 0.0, 1.4]
        scene, err = _build_scene({"array": VALID_ARRAY, "users": [user]}, cache)
        assert err is None
        np.testing.assert_allclose(
            scene.users[0].config.device_position,
            [5.25, 2.0, 1.4],
        )

    def test_defaults_for_optional_params(self):
        cache = _make_cache_with_body()
        user = {"id": "u1", "phantom": "thelonious"}
        scene, err = _build_scene({"array": VALID_ARRAY, "users": [user]}, cache)
        assert err is None
        np.testing.assert_allclose(scene.users[0].config.position, [0.0, 0.0, 0.0])


# ---------------------------------------------------------------------------
# _user_stats unit tests
# ---------------------------------------------------------------------------


class TestUserStats:
    def _make_user_state(self, uid="u1", phantom="thelonious"):
        cfg = UserConfig(
            user_id=uid,
            phantom_name=phantom,
            position=np.zeros(3),
            device_position=np.array([0.25, 0.0, 1.4]),
            device_orientation=np.array([0.0, 0.0, 1.0]),
        )
        return UserState(config=cfg)

    def test_no_result(self):
        user = self._make_user_state()
        scene = MagicMock()
        stats = _user_stats(user, scene)
        assert stats["user_id"] == "u1"
        assert stats["phantom"] == "thelonious"
        assert "p_abs" not in stats

    def test_with_result(self):
        user = self._make_user_state()
        result = MagicMock()
        result.p_abs = 0.005
        result.peak_sab = 12.3
        result.sab_averaged = np.array([1.0, 2.0, 3.0])
        user.result = result
        scene = MagicMock()
        stats = _user_stats(user, scene)
        assert stats["p_abs"] == pytest.approx(0.005)
        assert stats["p_abs_mw"] == pytest.approx(5.0)
        assert stats["peak_sab"] == pytest.approx(12.3)
        assert stats["peak_sab_averaged"] == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# /api/mimo/compute
# ---------------------------------------------------------------------------


class TestMIMOCompute:
    def test_missing_array_returns_400(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={"users": [_make_user_cfg()]},
        )
        assert resp.status_code == 400
        assert "array" in resp.get_json()["error"].lower()

    def test_missing_users_returns_400(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={"array": VALID_ARRAY},
        )
        assert resp.status_code == 400
        assert "users" in resp.get_json()["error"].lower()

    def test_empty_body_returns_400(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={},
        )
        assert resp.status_code == 400

    def test_unknown_phantom_returns_404(self, client):
        user = _make_user_cfg()
        user["phantom"] = "ghost"
        resp = client.post(
            "/api/mimo/compute",
            json={"array": VALID_ARRAY, "users": [user]},
        )
        assert resp.status_code == 404

    @patch("aegis.viewer.routes.mimo.compute_mimo_scene_with_bodies")
    def test_successful_compute(self, mock_compute, app, client):
        mock_compute.return_value = {
            "precoder_type": "mrt",
            "timings": {"total_s": 0.1},
        }
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": VALID_ARRAY,
                "users": [_make_user_cfg()],
                "level": 7,
                "precoder_type": "mrt",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["precoder_type"] == "mrt"
        mock_compute.assert_called_once()
        call_kwargs = mock_compute.call_args
        assert call_kwargs[1]["level"] == 7
        assert call_kwargs[1]["precoder_type"] == "mrt"

    @patch("aegis.viewer.routes.mimo.compute_mimo_scene_with_bodies")
    def test_compute_exception_returns_500(self, mock_compute, client):
        mock_compute.side_effect = RuntimeError("Channel matrix is singular")
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": VALID_ARRAY,
                "users": [_make_user_cfg()],
            },
        )
        assert resp.status_code == 500
        assert "singular" in resp.get_json()["error"].lower()

    @patch("aegis.viewer.routes.mimo.compute_mimo_scene_with_bodies")
    def test_compute_caches_results(self, mock_compute, app, client):
        mock_compute.return_value = {"precoder_type": "mrt", "timings": {}}
        client.post(
            "/api/mimo/compute",
            json={"array": VALID_ARRAY, "users": [_make_user_cfg()]},
        )
        cache = app._test_cache
        assert "mimo_scene" in cache
        assert "mimo_summary" in cache


# ---------------------------------------------------------------------------
# /api/mimo/result/<user_id>
# ---------------------------------------------------------------------------


class TestMIMOResult:
    def test_no_results_returns_404(self, client):
        resp = client.get("/api/mimo/result/u1")
        assert resp.status_code == 404

    def test_unknown_user_returns_404(self, app, client):
        app._test_cache["mimo_results_binary"] = {"u2": b"\x00" * 4}
        resp = client.get("/api/mimo/result/u1")
        assert resp.status_code == 404

    def test_returns_binary_with_stats(self, app, client):
        sab = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        stats = {"user_id": "u1", "p_abs": 0.01, "peak_sab": 3.0}
        app._test_cache["mimo_results_binary"] = {"u1": sab.tobytes()}
        app._test_cache["mimo_results_stats"] = {"u1": stats}
        resp = client.get("/api/mimo/result/u1")
        assert resp.status_code == 200
        assert resp.content_type == "application/octet-stream"
        arr = np.frombuffer(resp.data, dtype=np.float32)
        np.testing.assert_array_equal(arr, sab)
        header_stats = json.loads(resp.headers["X-Stats"])
        assert header_stats["user_id"] == "u1"
        assert header_stats["peak_sab"] == 3.0

    def test_missing_stats_returns_empty_dict(self, app, client):
        app._test_cache["mimo_results_binary"] = {"u1": b"\x00" * 4}
        resp = client.get("/api/mimo/result/u1")
        assert resp.status_code == 200
        header_stats = json.loads(resp.headers["X-Stats"])
        assert header_stats == {}


# ---------------------------------------------------------------------------
# /api/mimo/summary
# ---------------------------------------------------------------------------


class TestMIMOSummary:
    def _populate_cache(self, app, n_users=1, warning=None):
        """Set up cache with a computed MIMO scene."""
        users = []
        results_stats = {}
        for i in range(n_users):
            uid = f"u{i + 1}"
            cfg = UserConfig(
                user_id=uid,
                phantom_name="thelonious",
                position=np.array([float(i * 5), 0.0, 0.0]),
                device_position=np.array([float(i * 5) + 0.25, 0.0, 1.4]),
                device_orientation=np.array([0.0, 0.0, 1.0]),
            )
            user = UserState(config=cfg)
            users.append(user)
            results_stats[uid] = {
                "user_id": uid,
                "phantom": "thelonious",
                "p_abs": 0.001 * (i + 1),
                "p_abs_mw": 1.0 * (i + 1),
                "peak_sab": 5.0 * (i + 1),
            }

        from aegis.mimo.array import AntennaArray

        array = AntennaArray.upa(
            n_h=4,
            n_v=4,
            d_h=0.005,
            d_v=0.005,
            center=np.array([0.0, 0.0, 3.0]),
            broadside=np.array([1.0, 0.0, 0.0]),
        )
        from aegis.mimo.scene import MIMOScene

        scene = MIMOScene(array=array, users=users, freq_hz=28e9)
        summary = {
            "precoder_type": "mrt",
            "timings": {"total_s": 0.42},
        }
        if warning:
            summary["warning"] = warning

        cache = app._test_cache
        cache["mimo_scene"] = scene
        cache["mimo_summary"] = summary
        cache["mimo_results_stats"] = results_stats

    def test_no_results_returns_404(self, client):
        resp = client.get("/api/mimo/summary")
        assert resp.status_code == 404

    def test_single_user_summary(self, app, client):
        self._populate_cache(app, n_users=1)
        resp = client.get("/api/mimo/summary")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["precoder"] == "mrt"
        assert len(data["users"]) == 1
        user = data["users"][0]
        assert user["id"] == "u1"
        assert user["phantom"] == "thelonious"
        assert user["p_abs_mw"] == pytest.approx(1.0)
        assert user["peak_sab"] == pytest.approx(5.0)

    def test_multi_user_summary(self, app, client):
        self._populate_cache(app, n_users=3)
        resp = client.get("/api/mimo/summary")
        data = resp.get_json()
        assert len(data["users"]) == 3
        mws = [u["p_abs_mw"] for u in data["users"]]
        assert mws == [1.0, 2.0, 3.0]

    def test_compliance_flag_below_budget(self, app, client):
        self._populate_cache(app, n_users=1)
        resp = client.get("/api/mimo/summary")
        data = resp.get_json()
        assert data["users"][0]["compliant"] is True

    def test_compliance_flag_above_budget(self, app, client):
        self._populate_cache(app, n_users=1)
        app._test_cache["config"] = {"mimo": {"exposure_budget_mw": 0.5}}
        resp = client.get("/api/mimo/summary")
        data = resp.get_json()
        assert data["users"][0]["compliant"] is False

    def test_warning_included(self, app, client):
        self._populate_cache(app, n_users=1, warning="Degenerate channel")
        resp = client.get("/api/mimo/summary")
        data = resp.get_json()
        assert data["warning"] == "Degenerate channel"

    def test_no_warning_key_when_none(self, app, client):
        self._populate_cache(app, n_users=1)
        resp = client.get("/api/mimo/summary")
        data = resp.get_json()
        assert "warning" not in data

    def test_timings_included(self, app, client):
        self._populate_cache(app, n_users=1)
        resp = client.get("/api/mimo/summary")
        data = resp.get_json()
        assert data["timings"]["total_s"] == pytest.approx(0.42)

    def test_position_serialized(self, app, client):
        self._populate_cache(app, n_users=1)
        resp = client.get("/api/mimo/summary")
        data = resp.get_json()
        assert data["users"][0]["position"] == [0.0, 0.0, 0.0]
