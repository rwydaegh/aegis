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
    app.secret_key = "test"
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
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["session_id"] = "test-session"
    return c


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

    def test_duplicate_user_ids_returns_400(self):
        cache = _make_cache_with_body()
        users = [_make_user_cfg("same"), _make_user_cfg("same")]
        scene, err = _build_scene({"array": VALID_ARRAY, "users": users}, cache)
        assert scene is None
        resp, status = err
        assert status == 400
        assert "duplicate" in resp.get_json()["error"].lower()

    def test_users_not_a_list_returns_400(self):
        """Regression: users_cfg as string passed truthiness check but crashed on iteration."""
        cache = _make_cache_with_body()
        scene, err = _build_scene({"array": VALID_ARRAY, "users": "invalid"}, cache)
        assert scene is None
        resp, status = err
        assert status == 400
        assert "array" in resp.get_json()["error"].lower()

    def test_device_offset_null_uses_default(self):
        """Regression: device_offset: null crashed np.array(None) before try/except."""
        cache = _make_cache_with_body()
        user = _make_user_cfg()
        user["device_offset"] = None
        scene, err = _build_scene({"array": VALID_ARRAY, "users": [user]}, cache)
        assert err is None
        # Should fall back to device_position or default offset, not crash
        assert scene is not None

    def test_device_position_null_uses_default(self):
        """Both device_offset and device_position null should fall back to default."""
        cache = _make_cache_with_body()
        user = _make_user_cfg()
        user["device_offset"] = None
        user["device_position"] = None
        scene, err = _build_scene({"array": VALID_ARRAY, "users": [user]}, cache)
        assert err is None
        assert scene is not None

    def test_invalid_freq_hz_string_returns_400(self):
        """Non-numeric freq_hz should return 400."""
        cache = _make_cache_with_body()
        params = {"array": VALID_ARRAY, "users": [_make_user_cfg()], "freq_hz": "not_a_number"}
        scene, err = _build_scene(params, cache)
        assert scene is None
        resp, status = err
        assert status == 400
        assert "freq_hz" in resp.get_json()["error"]

    def test_negative_freq_hz_returns_400(self):
        """Negative freq_hz should return 400."""
        cache = _make_cache_with_body()
        params = {"array": VALID_ARRAY, "users": [_make_user_cfg()], "freq_hz": -100.0}
        scene, err = _build_scene(params, cache)
        assert scene is None
        resp, status = err
        assert status == 400
        assert "positive" in resp.get_json()["error"]

    def test_zero_freq_hz_returns_400(self):
        """Zero freq_hz should return 400."""
        cache = _make_cache_with_body()
        params = {"array": VALID_ARRAY, "users": [_make_user_cfg()], "freq_hz": 0}
        scene, err = _build_scene(params, cache)
        assert scene is None
        resp, status = err
        assert status == 400

    def test_invalid_power_dbm_string_returns_400(self):
        """Non-numeric power_dbm should return 400."""
        cache = _make_cache_with_body()
        params = {"array": VALID_ARRAY, "users": [_make_user_cfg()], "power_dbm": "loud"}
        scene, err = _build_scene(params, cache)
        assert scene is None
        resp, status = err
        assert status == 400
        assert "power_dbm" in resp.get_json()["error"]

    def test_orientation_rotation_applied_to_device_offset(self):
        """Device offset should be rotated by user orientation."""
        cache = _make_cache_with_body()
        user = _make_user_cfg()
        user["position"] = [5.0, 0.0, 0.0]
        user["device_offset"] = [1.0, 0.0, 1.4]
        user["orientation"] = np.pi / 2  # 90 degrees
        scene, err = _build_scene({"array": VALID_ARRAY, "users": [user]}, cache)
        assert err is None
        # After 90-degree rotation: [1,0] -> [0,1]
        dev_pos = scene.users[0].config.device_position
        np.testing.assert_allclose(dev_pos[0], 5.0, atol=1e-10)  # x: 5 + 0
        np.testing.assert_allclose(dev_pos[1], 1.0, atol=1e-10)  # y: 0 + 1
        np.testing.assert_allclose(dev_pos[2], 1.4, atol=1e-10)  # z unchanged

    @pytest.mark.parametrize("bad_value", ["abc", None, [1, 2, 3], {"x": 1}])
    def test_invalid_orientation_returns_400(self, bad_value):
        """Non-numeric orientation must return 400, not propagate TypeError/ValueError as 500."""
        cache = _make_cache_with_body()
        user = _make_user_cfg()
        user["orientation"] = bad_value
        scene, err = _build_scene({"array": VALID_ARRAY, "users": [user]}, cache)
        assert scene is None
        resp, status = err
        assert status == 400
        assert "orientation" in resp.get_json()["error"]

    def test_non_finite_orientation_returns_400(self):
        """Inf/NaN orientation returns 400 before cos/sin produce NaN downstream."""
        cache = _make_cache_with_body()
        user = _make_user_cfg()
        user["orientation"] = float("inf")
        scene, err = _build_scene({"array": VALID_ARRAY, "users": [user]}, cache)
        assert scene is None
        resp, status = err
        assert status == 400
        assert "finite" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# _user_stats unit tests
# ---------------------------------------------------------------------------


def _add_compliance_kwargs(mock_result):
    """Add a working compliance_kwargs method to a MagicMock result."""

    def _ckw(*, body=None):
        r = mock_result
        peak_4 = None
        if r.sab_averaged is not None and hasattr(r.sab_averaged, "size") and r.sab_averaged.size > 0:
            peak_4 = float(np.max(r.sab_averaged))
        elif r.sab is not None and hasattr(r.sab, "size") and r.sab.size > 0:
            peak_4 = float(np.max(r.sab))
        peak_1 = None
        if r.sab_1cm2_averaged is not None and hasattr(r.sab_1cm2_averaged, "size") and r.sab_1cm2_averaged.size > 0:
            peak_1 = float(np.max(r.sab_1cm2_averaged))
        sinc_peak = None
        if r.sinc_averaged is not None and hasattr(r.sinc_averaged, "size") and r.sinc_averaged.size > 0:
            sinc_peak = float(np.max(r.sinc_averaged))
        elif r.sinc is not None and hasattr(r.sinc, "size") and r.sinc.size > 0:
            sinc_peak = float(np.max(r.sinc))
        sinc_wb = None
        if body is not None and r.sinc is not None and hasattr(r.sinc, "size") and r.sinc.size > 0:
            sinc_wb = float(np.sum(r.sinc * body.areas) / np.sum(body.areas))
        return {
            "sab_4cm2": peak_4,
            "sab_1cm2": peak_1,
            "sar_wb": r.sar_wb,
            "sinc_local": sinc_peak,
            "sinc_whole_body": sinc_wb,
        }

    mock_result.compliance_kwargs = _ckw
    return mock_result


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
        result = _add_compliance_kwargs(MagicMock())
        result.p_abs = 0.005
        result.peak_sab = 12.3
        result.sab = np.array([0.0, 5.0, 12.3])
        result.sab_averaged = np.array([1.0, 2.0, 3.0])
        result.sinc = None
        result.sinc_averaged = None
        result.sab_1cm2_averaged = None
        result.sar_wb = None
        user.result = result
        scene = MagicMock()
        scene.freq_hz = 28e9
        stats = _user_stats(user, scene)
        assert stats["p_abs"] == pytest.approx(0.005)
        assert stats["p_abs_mw"] == pytest.approx(5.0)
        assert stats["peak_sab"] == pytest.approx(12.3)
        assert stats["peak_sab_averaged"] == pytest.approx(3.0)
        assert stats["n_illuminated"] == 2
        assert stats["n_triangles"] == 3
        # Distribution stats should be present
        assert "distribution" in stats
        assert stats["distribution"]["illuminated_fraction"] == pytest.approx(2 / 3)

    def test_with_result_and_body(self):
        """When body is present, illuminated_area_cm2 should be computed."""
        user = self._make_user_state()
        result = _add_compliance_kwargs(MagicMock())
        result.p_abs = 0.01
        result.peak_sab = 5.0
        result.sab = np.array([0.0, 5.0, 3.0, 0.0])
        result.sab_averaged = np.array([0.0, 4.0, 2.5, 0.0])
        result.sinc = None
        result.sinc_averaged = None
        result.sab_1cm2_averaged = None
        result.sar_wb = None
        user.result = result
        body = MagicMock()
        body.n_triangles = 4
        body.areas = np.array([1e-4, 2e-4, 3e-4, 4e-4])
        user.body = body
        scene = MagicMock()
        scene.freq_hz = 28e9
        stats = _user_stats(user, scene)
        assert stats["n_triangles"] == 4
        # illuminated_area_cm2: sum of areas where sab > 0 (indices 1,2) * 1e4
        expected_area_cm2 = (2e-4 + 3e-4) * 1e4
        assert stats["distribution"]["illuminated_area_cm2"] == pytest.approx(expected_area_cm2)

    def test_all_zero_sab(self):
        """When all sab values are zero, illuminated stats should handle it."""
        user = self._make_user_state()
        result = _add_compliance_kwargs(MagicMock())
        result.p_abs = 0.0
        result.peak_sab = 0.0
        result.sab = np.array([0.0, 0.0, 0.0])
        result.sab_averaged = None
        result.sinc = None
        result.sinc_averaged = None
        result.sab_1cm2_averaged = None
        result.sar_wb = None
        user.result = result
        scene = MagicMock()
        scene.freq_hz = 28e9
        stats = _user_stats(user, scene)
        assert stats["n_illuminated"] == 0
        dist = stats["distribution"]
        assert dist["illuminated_fraction"] == 0.0
        assert dist["illuminated_mean"] == 0.0
        assert dist["illuminated_p50"] == 0.0

    def test_sub_6ghz_compliance_vacuously_none(self):
        """At sub-6 GHz, sab_4cm2 has no ICNIRP limit, so compliance has no checks."""
        user = self._make_user_state()
        result = _add_compliance_kwargs(MagicMock())
        result.p_abs = 0.005
        result.peak_sab = 10.0
        result.sab = np.array([0.0, 5.0, 10.0])
        result.sab_averaged = np.array([1.0, 3.0, 8.0])
        result.sinc = None
        result.sinc_averaged = None
        result.sab_1cm2_averaged = None
        result.sar_wb = None
        user.result = result
        scene = MagicMock()
        scene.freq_hz = 3.5e9  # sub-6 GHz
        stats = _user_stats(user, scene)
        # No applicable ICNIRP checks for sab at sub-6 GHz
        assert stats["compliant"] is None
        assert stats["compliance"]["overall_pass"] is None
        assert stats["compliance"]["checks"] == []

    def test_sab_averaged_none_falls_back_to_raw_peak(self):
        """When sab_averaged is None, compliance uses raw sab peak."""
        user = self._make_user_state()
        result = _add_compliance_kwargs(MagicMock())
        result.p_abs = 0.01
        result.peak_sab = 15.0
        result.sab = np.array([0.0, 15.0, 5.0])
        result.sab_averaged = None
        result.sinc = None
        result.sinc_averaged = None
        result.sab_1cm2_averaged = None
        result.sar_wb = None
        user.result = result
        scene = MagicMock()
        scene.freq_hz = 28e9
        stats = _user_stats(user, scene)
        # Should use raw sab peak (15.0) for compliance against 20 W/m^2 limit
        assert stats["compliant"] is True
        assert stats["compliance"] is not None
        assert stats["compliance"]["overall_pass"] is True
        # Verify the sab check used the raw peak
        sab_check = [c for c in stats["compliance"]["checks"] if "S_ab" in c["label"]]
        assert len(sab_check) == 1
        assert sab_check[0]["value"] == pytest.approx(15.0)

    def test_sab_averaged_none_exceeding_limit_fails(self):
        """Raw sab peak exceeding ICNIRP limit should fail compliance."""
        user = self._make_user_state()
        result = _add_compliance_kwargs(MagicMock())
        result.p_abs = 0.05
        result.peak_sab = 25.0
        result.sab = np.array([0.0, 25.0, 10.0])
        result.sab_averaged = None
        result.sinc = None
        result.sinc_averaged = None
        result.sab_1cm2_averaged = None
        result.sar_wb = None
        user.result = result
        scene = MagicMock()
        scene.freq_hz = 28e9
        stats = _user_stats(user, scene)
        # 25 > 20 W/m^2 GP limit
        assert stats["compliant"] is False
        assert stats["compliance"]["overall_pass"] is False

    def test_sinc_local_included_in_compliance(self):
        """MIMO compliance should check sinc_local, not just sab_4cm2."""
        user = self._make_user_state()
        result = _add_compliance_kwargs(MagicMock())
        result.p_abs = 0.01
        result.peak_sab = 10.0
        result.sab = np.array([0.0, 5.0, 10.0])
        result.sab_averaged = np.array([1.0, 3.0, 8.0])
        # sinc_averaged exceeds ICNIRP sinc_local limit (~31.5 W/m^2 at 28 GHz GP)
        result.sinc_averaged = np.array([10.0, 20.0, 50.0])
        result.sinc = np.array([15.0, 25.0, 60.0])
        result.sab_1cm2_averaged = None
        result.sar_wb = None
        user.result = result
        scene = MagicMock()
        scene.freq_hz = 28e9
        stats = _user_stats(user, scene)
        # sinc_local check should be present and should fail (50 > ~31.5)
        sinc_checks = [c for c in stats["compliance"]["checks"] if "S_inc" in c["label"]]
        assert len(sinc_checks) >= 1, "sinc_local check missing from MIMO compliance"
        sinc_local_check = [c for c in sinc_checks if "local" in c["label"]]
        assert len(sinc_local_check) == 1
        assert sinc_local_check[0]["pass"] is False
        assert stats["compliance"]["overall_pass"] is False

    def test_sinc_whole_body_included_in_compliance(self):
        """MIMO compliance should check sinc_whole_body, matching single-user route."""
        user = self._make_user_state()
        result = _add_compliance_kwargs(MagicMock())
        result.p_abs = 0.01
        result.peak_sab = 10.0
        result.sab = np.array([0.0, 5.0, 10.0])
        result.sab_averaged = np.array([1.0, 3.0, 8.0])
        # sinc values that produce a whole-body average exceeding the ICNIRP
        # whole-body limit (10 W/m^2 for general public above 6 GHz)
        result.sinc = np.array([12.0, 12.0, 12.0])
        result.sinc_averaged = None
        result.sab_1cm2_averaged = None
        result.sar_wb = None
        user.result = result
        body = MagicMock()
        body.n_triangles = 3
        body.areas = np.array([1e-4, 1e-4, 1e-4])
        user.body = body
        scene = MagicMock()
        scene.freq_hz = 28e9
        stats = _user_stats(user, scene)
        # sinc_whole_body check should be present
        wb_checks = [c for c in stats["compliance"]["checks"] if "whole-body" in c["label"]]
        assert len(wb_checks) == 1, "sinc_whole_body check missing from MIMO compliance"
        # whole-body avg = 12.0 W/m^2 > 10.0 W/m^2 limit -> FAIL
        assert wb_checks[0]["pass"] is False
        assert stats["compliance"]["overall_pass"] is False

    def test_distribution_stats_without_body(self):
        """Distribution stats should work when body is None (no illuminated_area_cm2)."""
        user = self._make_user_state()
        result = _add_compliance_kwargs(MagicMock())
        result.p_abs = 0.01
        result.peak_sab = 8.0
        result.sab = np.array([0.0, 8.0, 3.0, 0.0, 1.0])
        result.sab_averaged = None
        result.sinc = None
        result.sinc_averaged = None
        result.sab_1cm2_averaged = None
        result.sar_wb = None
        user.result = result
        # body remains None (default)
        scene = MagicMock()
        scene.freq_hz = 28e9
        stats = _user_stats(user, scene)
        dist = stats["distribution"]
        assert dist["illuminated_area_cm2"] is None
        assert dist["illuminated_fraction"] == pytest.approx(3 / 5)
        assert dist["p95"] > 0
        assert dist["p99"] > 0


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

    def test_duplicate_user_ids_returns_400(self, client):
        users = [_make_user_cfg("same"), _make_user_cfg("same")]
        resp = client.post(
            "/api/mimo/compute",
            json={"array": VALID_ARRAY, "users": users},
        )
        assert resp.status_code == 400
        assert "duplicate" in resp.get_json()["error"].lower()

    def test_invalid_level_string_returns_400(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={"array": VALID_ARRAY, "users": [_make_user_cfg()], "level": "abc"},
        )
        assert resp.status_code == 400
        assert "integer" in resp.get_json()["error"].lower()

    def test_incoherent_level_returns_400(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={"array": VALID_ARRAY, "users": [_make_user_cfg()], "level": 2},
        )
        assert resp.status_code == 400
        assert "7 or 8" in resp.get_json()["error"]

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
        assert "test-session:mimo_scene" in cache
        assert "test-session:mimo_summary" in cache

    @pytest.mark.parametrize("bad_type", ["foo", "ZF", "", "maximum_ratio", None])
    def test_unknown_precoder_type_returns_400(self, bad_type, client):
        """Unknown precoder_type should reject as 400 before hitting compute."""
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": VALID_ARRAY,
                "users": [_make_user_cfg()],
                "precoder_type": bad_type,
            },
        )
        assert resp.status_code == 400
        assert "precoder_type" in resp.get_json()["error"]

    @pytest.mark.parametrize("precoder_type", ["zf", "zf_exposure"])
    @patch("aegis.viewer.routes.mimo.compute_mimo_scene_with_bodies")
    def test_zf_precoder_m_lt_k_returns_400(self, mock_compute, precoder_type, client):
        """ZF/zf_exposure with M_ant < K should reject as 400, not 500 from precoder."""
        small_array = {**VALID_ARRAY, "n_h": 1, "n_v": 1}  # M_ant = 1
        users = [_make_user_cfg("u1"), _make_user_cfg("u2")]  # K = 2
        users[1]["position"] = [6.0, 0.0, 0.0]
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": small_array,
                "users": users,
                "precoder_type": precoder_type,
            },
        )
        assert resp.status_code == 400
        body = resp.get_json()["error"]
        assert "M_ant" in body
        assert "K" in body
        assert mock_compute.call_count == 0  # never reached compute

    @patch("aegis.viewer.routes.mimo.compute_mimo_scene_with_bodies")
    def test_mmse_allowed_at_m_lt_k(self, mock_compute, client):
        """MMSE is regularized and works for any M, K — must not be blocked."""
        mock_compute.return_value = {"precoder_type": "mmse", "timings": {}}
        small_array = {**VALID_ARRAY, "n_h": 1, "n_v": 1}
        users = [_make_user_cfg("u1"), _make_user_cfg("u2")]
        users[1]["position"] = [6.0, 0.0, 0.0]
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": small_array,
                "users": users,
                "precoder_type": "mmse",
            },
        )
        assert resp.status_code == 200
        assert mock_compute.call_count == 1


# ---------------------------------------------------------------------------
# /api/mimo/result/<user_id>
# ---------------------------------------------------------------------------


class TestMIMOResult:
    def test_no_results_returns_404(self, client):
        resp = client.get("/api/mimo/result/u1")
        assert resp.status_code == 404

    def test_unknown_user_returns_404(self, app, client):
        app._test_cache["test-session:mimo_results_binary"] = {"u2": b"\x00" * 4}
        resp = client.get("/api/mimo/result/u1")
        assert resp.status_code == 404

    def test_returns_binary_with_stats(self, app, client):
        sab = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        stats = {"user_id": "u1", "p_abs": 0.01, "peak_sab": 3.0}
        app._test_cache["test-session:mimo_results_binary"] = {"u1": sab.tobytes()}
        app._test_cache["test-session:mimo_results_stats"] = {"u1": stats}
        resp = client.get("/api/mimo/result/u1")
        assert resp.status_code == 200
        assert resp.content_type == "application/octet-stream"
        arr = np.frombuffer(resp.data, dtype=np.float32)
        np.testing.assert_array_equal(arr, sab)
        header_stats = json.loads(resp.headers["X-Stats"])
        assert header_stats["user_id"] == "u1"
        assert header_stats["peak_sab"] == 3.0

    def test_missing_stats_returns_empty_dict(self, app, client):
        app._test_cache["test-session:mimo_results_binary"] = {"u1": b"\x00" * 4}
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
        cache["test-session:mimo_scene"] = scene
        cache["test-session:mimo_summary"] = summary
        cache["test-session:mimo_results_stats"] = results_stats

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

    def test_compliance_at_exact_budget_boundary(self, app, client):
        """User at exact budget boundary is non-compliant (strict less-than check)."""
        self._populate_cache(app, n_users=1)
        # Set budget exactly equal to user's p_abs_mw (1.0)
        app._test_cache["config"] = {"mimo": {"exposure_budget_mw": 1.0}}
        resp = client.get("/api/mimo/summary")
        data = resp.get_json()
        # p_abs_mw=1.0, budget=1.0: 1.0 < 1.0 is False -> non-compliant
        assert data["users"][0]["compliant"] is False

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
