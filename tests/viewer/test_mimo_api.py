"""Integration tests for MIMO API routes."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

pytest.importorskip("flask", reason="Flask not installed (viewer extra)")
from aegis.viewer.config import DEFAULTS


@pytest.fixture
def mimo_app():
    """Flask test app with MIMO routes registered."""
    from flask import Flask

    app = Flask(__name__)
    app.config["TESTING"] = True

    cache = {
        "config": DEFAULTS,
        "bodies": {
            "thelonious": {"body": MagicMock(name="thelonious"), "binary": b"", "meta": {}},
        },
        "default_body": "thelonious",
    }
    cache_lock = threading.Lock()

    from aegis.viewer.routes import mimo

    mimo.register(app, cache, cache_lock)
    return app, cache


@pytest.fixture
def client(mimo_app):
    app, _ = mimo_app
    return app.test_client()


def _mock_compute(scene, bodies, level=7, generate_paths_fn=None, precoder_type="mrt"):
    """Mock compute that populates user states."""
    for user in scene.users:
        user._sab_raw = np.ones(10, dtype=np.float32)
        result = MagicMock()
        result.p_abs = 0.05
        result.peak_sab = 10.0
        result.sab = np.ones(10, dtype=np.float32) * 10.0
        result.sab_averaged = np.ones(10, dtype=np.float32) * 8.0
        user.result = result
    return {
        "user_ids": [u.config.user_id for u in scene.users],
        "timings": {"total_ms": 1.0},
        "precoder_type": "mrt",
    }


COMPUTE_PATCH = "aegis.viewer.routes.mimo.compute_mimo_scene_with_bodies"


class TestMIMOCompute:
    def test_basic_compute(self, client):
        with patch(COMPUTE_PATCH, side_effect=_mock_compute):
            resp = client.post(
                "/api/mimo/compute",
                json={
                    "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                    "users": [
                        {
                            "id": "u1",
                            "phantom": "thelonious",
                            "position": [0, 0, 0],
                            "device_position": [0.25, 0, 1.4],
                            "device_orientation": [0, 0, 1],
                        }
                    ],
                    "freq_hz": 28e9,
                    "power_dbm": 60,
                },
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "u1" in data["user_ids"]
        assert "timings" in data
        assert data["precoder_type"] == "mrt"

    def test_missing_array(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={
                "users": [{"id": "u1", "phantom": "thelonious", "position": [0, 0, 0]}],
            },
        )
        assert resp.status_code == 400

    def test_empty_users(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                "users": [],
            },
        )
        assert resp.status_code == 400

    def test_unknown_phantom(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                "users": [{"id": "u1", "phantom": "nonexistent", "position": [0, 0, 0]}],
            },
        )
        assert resp.status_code == 404


class TestMIMOResult:
    def _compute_first(self, client):
        with patch(COMPUTE_PATCH, side_effect=_mock_compute):
            client.post(
                "/api/mimo/compute",
                json={
                    "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                    "users": [
                        {
                            "id": "u1",
                            "phantom": "thelonious",
                            "position": [0, 0, 0],
                            "device_position": [0.25, 0, 1.4],
                            "device_orientation": [0, 0, 1],
                        }
                    ],
                    "freq_hz": 28e9,
                    "power_dbm": 60,
                },
            )

    def test_result_before_compute(self, client):
        resp = client.get("/api/mimo/result/u1")
        assert resp.status_code == 404

    def test_result_after_compute(self, client):
        self._compute_first(client)
        resp = client.get("/api/mimo/result/u1")
        assert resp.status_code == 200
        assert resp.content_type == "application/octet-stream"
        assert "X-Stats" in resp.headers
        data = np.frombuffer(resp.data, dtype=np.float32)
        assert len(data) == 10
        assert np.all(np.isfinite(data))

    def test_result_unknown_user(self, client):
        self._compute_first(client)
        resp = client.get("/api/mimo/result/nonexistent")
        assert resp.status_code == 404


class TestMIMOSummary:
    def _compute_first(self, client):
        with patch(COMPUTE_PATCH, side_effect=_mock_compute):
            client.post(
                "/api/mimo/compute",
                json={
                    "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                    "users": [
                        {
                            "id": "u1",
                            "phantom": "thelonious",
                            "position": [0, 0, 0],
                            "device_position": [0.25, 0, 1.4],
                            "device_orientation": [0, 0, 1],
                        }
                    ],
                    "freq_hz": 28e9,
                    "power_dbm": 60,
                },
            )

    def test_summary_before_compute(self, client):
        resp = client.get("/api/mimo/summary")
        assert resp.status_code == 404

    def test_summary_after_compute(self, client):
        self._compute_first(client)
        resp = client.get("/api/mimo/summary")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["users"]) == 1
        u = data["users"][0]
        assert u["id"] == "u1"
        assert "p_abs_mw" in u
        assert "compliant" in u
        assert data["precoder"] == "mrt"


class TestMIMOInputValidation:
    """Regression tests for freq_hz/power_dbm validation in _build_scene."""

    def test_non_numeric_freq_hz_returns_400(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                "users": [{"id": "u1", "phantom": "thelonious", "position": [0, 0, 0]}],
                "freq_hz": "not_a_number",
            },
        )
        assert resp.status_code == 400
        assert "freq_hz" in resp.get_json()["error"]

    def test_zero_freq_hz_returns_400(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                "users": [{"id": "u1", "phantom": "thelonious", "position": [0, 0, 0]}],
                "freq_hz": 0,
            },
        )
        assert resp.status_code == 400
        assert "freq_hz" in resp.get_json()["error"]

    def test_non_numeric_power_dbm_returns_400(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                "users": [{"id": "u1", "phantom": "thelonious", "position": [0, 0, 0]}],
                "power_dbm": "abc",
            },
        )
        assert resp.status_code == 400
        assert "power_dbm" in resp.get_json()["error"]


_ARRAY_CFG = {"type": "upa", "n_h": 4, "n_v": 4, "position": [5, 0, 3], "broadside": [-1, 0, 0]}


def _mock_compute_varied_power(scene, bodies, level=7, generate_paths_fn=None, precoder_type="mrt"):
    """Mock compute that assigns different p_abs per user index."""
    powers = [0.05, 0.15]
    for i, user in enumerate(scene.users):
        user._sab_raw = np.ones(10, dtype=np.float32)
        result = MagicMock()
        result.p_abs = powers[i] if i < len(powers) else 0.05
        result.peak_sab = 10.0
        result.sab = np.ones(10, dtype=np.float32) * 10.0
        result.sab_averaged = None
        user.result = result
    return {
        "user_ids": [u.config.user_id for u in scene.users],
        "timings": {"total_ms": 1.0},
        "precoder_type": "mrt",
    }


class TestMIMOMultiUser:
    def _compute_two_users(self, client):
        with patch(COMPUTE_PATCH, side_effect=_mock_compute):
            return client.post(
                "/api/mimo/compute",
                json={
                    "array": _ARRAY_CFG,
                    "users": [
                        {"id": "u1", "phantom": "thelonious", "position": [0, 0, 0]},
                        {"id": "u2", "phantom": "thelonious", "position": [2, 0, 0]},
                    ],
                    "freq_hz": 28e9,
                    "power_dbm": 60,
                },
            )

    def test_two_user_compute(self, client):
        resp = self._compute_two_users(client)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "u1" in data["user_ids"]
        assert "u2" in data["user_ids"]

    def test_two_user_individual_results(self, client):
        self._compute_two_users(client)
        resp_u1 = client.get("/api/mimo/result/u1")
        resp_u2 = client.get("/api/mimo/result/u2")
        assert resp_u1.status_code == 200
        assert resp_u1.content_type == "application/octet-stream"
        assert resp_u2.status_code == 200
        assert resp_u2.content_type == "application/octet-stream"

    def test_two_user_summary(self, client):
        self._compute_two_users(client)
        resp = client.get("/api/mimo/summary")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["users"]) == 2
        ids = [u["id"] for u in data["users"]]
        assert "u1" in ids
        assert "u2" in ids

    def test_duplicate_phantoms(self, client):
        with patch(COMPUTE_PATCH, side_effect=_mock_compute):
            resp = client.post(
                "/api/mimo/compute",
                json={
                    "array": _ARRAY_CFG,
                    "users": [
                        {"id": "ua", "phantom": "thelonious", "position": [0, 0, 0]},
                        {"id": "ub", "phantom": "thelonious", "position": [2, 0, 0]},
                        {"id": "uc", "phantom": "thelonious", "position": [4, 0, 0]},
                    ],
                    "freq_hz": 28e9,
                    "power_dbm": 60,
                },
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["user_ids"]) == 3
        assert "ua" in data["user_ids"]
        assert "ub" in data["user_ids"]
        assert "uc" in data["user_ids"]


class TestMIMOCompliance:
    def test_compliance_boundary(self, client):
        with patch(COMPUTE_PATCH, side_effect=_mock_compute_varied_power):
            client.post(
                "/api/mimo/compute",
                json={
                    "array": _ARRAY_CFG,
                    "users": [
                        {"id": "low", "phantom": "thelonious", "position": [0, 0, 0]},
                        {"id": "high", "phantom": "thelonious", "position": [2, 0, 0]},
                    ],
                    "freq_hz": 28e9,
                    "power_dbm": 60,
                },
            )
        resp = client.get("/api/mimo/summary")
        assert resp.status_code == 200
        data = resp.get_json()
        users_by_id = {u["id"]: u for u in data["users"]}
        assert users_by_id["low"]["compliant"] is True
        assert users_by_id["high"]["compliant"] is False


class TestMIMOCacheReplacement:
    def test_second_compute_replaces_first(self, client):
        with patch(COMPUTE_PATCH, side_effect=_mock_compute):
            client.post(
                "/api/mimo/compute",
                json={
                    "array": _ARRAY_CFG,
                    "users": [{"id": "u1", "phantom": "thelonious", "position": [0, 0, 0]}],
                    "freq_hz": 28e9,
                    "power_dbm": 60,
                },
            )
        with patch(COMPUTE_PATCH, side_effect=_mock_compute):
            client.post(
                "/api/mimo/compute",
                json={
                    "array": _ARRAY_CFG,
                    "users": [{"id": "u2", "phantom": "thelonious", "position": [2, 0, 0]}],
                    "freq_hz": 28e9,
                    "power_dbm": 60,
                },
            )
        resp_u1 = client.get("/api/mimo/result/u1")
        resp_u2 = client.get("/api/mimo/result/u2")
        assert resp_u1.status_code == 404
        assert resp_u2.status_code == 200
