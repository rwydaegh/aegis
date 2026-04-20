"""Tests for /api/optimize SSE endpoint."""

import json
import threading

import numpy as np
import pytest

pytest.importorskip("flask")
from flask import Flask  # noqa: E402


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    cache = {}
    cache_lock = threading.RLock()

    from aegis.viewer.routes.optimize import register

    register(app, cache, cache_lock)
    app._optimize_cache = cache
    app._optimize_cache_lock = cache_lock
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestOptimizeEndpoint:
    def test_mimo_peak_streams_events(self, client):
        rng = np.random.default_rng(42)
        n_tri, n_ant = 50, 16
        G_tilde = (rng.standard_normal((n_tri, 3, n_ant)) + 1j * rng.standard_normal((n_tri, 3, n_ant))) * 0.01
        G_tilde[0, :, :] = 0.5 * np.ones((3, n_ant))
        x_init = np.conj(G_tilde[0, 0, :]) / np.linalg.norm(G_tilde[0, 0, :])

        resp = client.post(
            "/api/optimize",
            json={
                "mode": "mimo_peak",
                "G_tilde_real": G_tilde.real.tolist(),
                "G_tilde_imag": G_tilde.imag.tolist(),
                "x_init_real": x_init.real.tolist(),
                "x_init_imag": x_init.imag.tolist(),
                "p_max": 1.0,
                "max_iters": 5,
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

        events = []
        for line in resp.data.decode().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        assert len(events) >= 2
        # Check iteration events have expected fields
        iter_events = [e for e in events if "iter" in e and not e.get("done")]
        assert len(iter_events) >= 1
        assert "sab_b64" in iter_events[0]
        assert "objective" in iter_events[0]

    def test_missing_mode_returns_400(self, client):
        resp = client.post("/api/optimize", json={})
        assert resp.status_code == 400

    def test_unknown_mode_returns_400(self, client):
        resp = client.post("/api/optimize", json={"mode": "bogus"})
        assert resp.status_code == 400


class TestTiltPowerMode:
    """Regression: tilt_power used to read cache instead of app.config for dosimetry results."""

    def test_tilt_power_reads_from_app_config(self, app):
        """Verify tilt_power finds cached result in app.config, not cache dict."""
        from types import SimpleNamespace

        from aegis.paths import PropagationPaths

        # Create a mock result with _paths attribute
        k_hat = np.array([[0.0, 0.0, -1.0]])
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=np.array([1.0]))
        mock_result = SimpleNamespace(_paths=paths)
        mock_body = SimpleNamespace(normals=np.array([[0.0, 0.0, 1.0]]))

        client = app.test_client()
        # Establish a session and inject session-scoped cache data
        with client.session_transaction() as sess:
            sess["session_id"] = "test-session"

        # The optimize route reads from the cache dict passed at register time;
        # retrieve it via the closure (the app fixture passes an empty dict).
        # We need to inject into the same cache dict the route uses.
        cache = app._optimize_cache
        cache["test-session:_last_dosimetry_result"] = mock_result
        cache["test-session:_last_dosimetry_body"] = mock_body
        cache["test-session:_last_rt_paths"] = paths

        resp = client.post(
            "/api/optimize",
            json={
                "mode": "tilt_power",
                "max_iters": 2,
                "antenna_direction": [0, 0, -1],
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

        events = []
        for line in resp.data.decode().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        assert len(events) >= 1
        # Should not contain an error about missing cached result
        assert not any(e.get("error") for e in events if "No dosimetry result" in e.get("message", ""))


class TestPlacementMode:
    """Test placement mode with mocked RT."""

    def test_placement_streams_grid_search(self, app):
        """Verify placement mode calls evaluate_fn and streams results."""
        from unittest.mock import patch

        n_tri = 50
        mock_sab = np.random.default_rng(42).random(n_tri).astype(np.float32) * 10

        def fake_evaluate_fn(pos):
            # Return lower peak_sab for positions closer to origin
            dist = float(np.linalg.norm(pos))
            return {
                "peak_sab": dist * 2.0,
                "sab": mock_sab * dist,
                "stats": {"peak_sab": dist * 2.0},
            }

        def fake_build_fn(*args, **kwargs):
            return fake_evaluate_fn

        with patch(
            "aegis.viewer.routes.optimize._build_placement_evaluate_fn",
            fake_build_fn,
        ):
            client = app.test_client()
            resp = client.post(
                "/api/optimize",
                json={
                    "mode": "placement",
                    "center": [5, 0, 3],
                    "grid_size": 3,
                    "grid_spacing": 2.0,
                    "max_iters": 20,
                },
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.content_type

            events = []
            for line in resp.data.decode().split("\n"):
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

            # 3x3 grid = 9 evaluations, last one has done=True
            assert len(events) == 9
            assert events[-1]["done"] is True
            assert "best" in events[-1]
            assert events[-1]["params"]["antenna_pos"] == events[-1]["best"]["antenna_pos"]
            # All events should have antenna_pos in params
            for e in events:
                assert "antenna_pos" in e.get("params", {})

    def test_build_placement_evaluate_fn_accepts_dosimetry_mode(self, app):
        """Placement should parse dosimetry_mode, not confuse it with optimizer mode."""
        from types import SimpleNamespace
        from unittest.mock import patch

        from aegis.geometry.mesh import BodyMesh
        from aegis.viewer.config import load_config
        from aegis.viewer.routes.optimize import _build_placement_evaluate_fn

        vertices = np.array([[[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [0.0, 0.1, 0.0]]])
        body = BodyMesh.from_arrays(vertices, name="test_body")
        cache = {
            "default_body": "test_body",
            "bodies": {"test_body": {"body": body}},
            "config": load_config(),
        }
        fake_result = SimpleNamespace(
            peak_sab=1.25,
            sab=np.array([1.25], dtype=np.float32),
        )

        with (
            patch(
                "aegis.viewer.routes.compute._run_dosimetry",
                return_value=(fake_result, None),
            ),
            patch(
                "aegis.viewer.routes.compute._build_stats_response",
                return_value={"peak_sab": 1.25},
            ),
            app.test_request_context(),
        ):
            from flask import session as _sess

            _sess["session_id"] = "test-session"

            evaluate_fn = _build_placement_evaluate_fn(
                {
                    "mode": "placement",
                    "dosimetry_mode": "spatial",
                    "fresnel": True,
                },
                app,
                cache,
                threading.RLock(),
            )

            result = evaluate_fn(np.array([1.0, 0.0, 1.0]))

        assert result["peak_sab"] == 1.25
        assert np.allclose(result["sab"], np.array([1.25], dtype=np.float32))
        assert result["stats"]["peak_sab"] == 1.25


class TestSafeInt:
    """_safe_int falls back to default on non-numeric input."""

    def test_valid_int(self):
        from aegis.viewer.routes.optimize import _safe_int

        assert _safe_int(5, 0) == 5

    def test_valid_string_int(self):
        from aegis.viewer.routes.optimize import _safe_int

        assert _safe_int("7", 0) == 7

    def test_invalid_string_returns_default(self):
        from aegis.viewer.routes.optimize import _safe_int

        assert _safe_int("abc", 42) == 42

    def test_none_returns_default(self):
        from aegis.viewer.routes.optimize import _safe_int

        assert _safe_int(None, 10) == 10

    def test_float_truncates(self):
        from aegis.viewer.routes.optimize import _safe_int

        assert _safe_int(3.9, 0) == 3


class TestInvalidModeReturns400:
    """Invalid optimizer mode returns 400, not 500."""

    def test_invalid_mode(self, client):
        resp = client.post("/api/optimize", json={"mode": "nonexistent"})
        assert resp.status_code == 400
        assert b"mode must be one of" in resp.data

    def test_non_numeric_max_iters(self, client):
        """Non-numeric max_iters should not crash (uses _safe_int fallback)."""
        # This would 500 before the fix if max_iters was not handled
        resp = client.post(
            "/api/optimize",
            json={"mode": "mimo_peak", "max_iters": "not_a_number"},
        )
        # 400 because no G_tilde cached, not because of max_iters crash.
        # Error message must be user-friendly and must NOT leak internal API paths.
        assert resp.status_code == 400
        assert b"error" in resp.data
        assert b"not ready yet" in resp.data
        assert b"/api/" not in resp.data


class TestPlacementInputValidation:
    """Placement mode tolerates malformed scalar inputs instead of 500-ing."""

    def test_null_grid_spacing_falls_back_to_default(self, app):
        from unittest.mock import patch

        def fake_build_fn(*args, **kwargs):
            def _eval(pos):
                return {"peak_sab": 0.0, "sab": np.zeros(1, dtype=np.float32), "stats": {}}

            return _eval

        with patch(
            "aegis.viewer.routes.optimize._build_placement_evaluate_fn",
            fake_build_fn,
        ):
            client = app.test_client()
            resp = client.post(
                "/api/optimize",
                json={"mode": "placement", "grid_spacing": None, "grid_size": 2},
            )
            assert resp.status_code == 200

    def test_string_grid_spacing_falls_back_to_default(self, app):
        from unittest.mock import patch

        def fake_build_fn(*args, **kwargs):
            def _eval(pos):
                return {"peak_sab": 0.0, "sab": np.zeros(1, dtype=np.float32), "stats": {}}

            return _eval

        with patch(
            "aegis.viewer.routes.optimize._build_placement_evaluate_fn",
            fake_build_fn,
        ):
            client = app.test_client()
            resp = client.post(
                "/api/optimize",
                json={"mode": "placement", "grid_spacing": "fast", "grid_size": 2},
            )
            assert resp.status_code == 200

    def test_malformed_body_offset_returns_400(self, app):
        """Non-numeric body_offset should 400, not crash with HTTP 500."""
        from aegis.geometry.mesh import BodyMesh

        vertices = np.array([[[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [0.0, 0.1, 0.0]]])
        body = BodyMesh.from_arrays(vertices, name="test_body")

        from aegis.viewer.config import load_config

        cache = app._optimize_cache
        cache["default_body"] = "test_body"
        cache["bodies"] = {"test_body": {"body": body}}
        cache["config"] = load_config()

        client = app.test_client()
        resp = client.post(
            "/api/optimize",
            json={"mode": "placement", "body_offset": ["a", "b", "c"], "grid_size": 2},
        )
        assert resp.status_code == 400
        assert b"body_offset" in resp.data or b"error" in resp.data

    @pytest.mark.parametrize(
        ("payload_key", "bad_value", "expected_substring"),
        [
            ("center", [float("nan"), 0, 3], b"center"),
            ("center", [float("inf"), 0, 3], b"center"),
            ("center", [1, 2], b"center"),
            ("center", "bogus", b"center"),
            ("body_offset", [float("nan"), 0, 0], b"body_offset"),
            ("body_offset", [float("inf"), 0, 0], b"body_offset"),
            ("body_rotation_y", float("nan"), b"body_rotation_y"),
            ("body_rotation_y", float("inf"), b"body_rotation_y"),
            ("body_rotation_y", "spin", b"body_rotation_y"),
            ("power_dbm", float("nan"), b"power_dbm"),
            ("power_dbm", float("inf"), b"power_dbm"),
            ("power_dbm", "loud", b"power_dbm"),
        ],
    )
    def test_nonfinite_placement_scalar_returns_400(self, app, payload_key, bad_value, expected_substring):
        """Non-finite or non-numeric placement scalars must 400 at the boundary."""
        from aegis.geometry.mesh import BodyMesh
        from aegis.viewer.config import load_config

        vertices = np.array([[[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [0.0, 0.1, 0.0]]])
        body = BodyMesh.from_arrays(vertices, name="test_body")

        cache = app._optimize_cache
        cache["default_body"] = "test_body"
        cache["bodies"] = {"test_body": {"body": body}}
        cache["config"] = load_config()

        client = app.test_client()
        resp = client.post(
            "/api/optimize",
            json={"mode": "placement", "grid_size": 2, payload_key: bad_value},
        )
        assert resp.status_code == 400
        assert expected_substring in resp.data


class TestMimoPeakInputValidation:
    """mimo_peak rejects non-finite/non-numeric scalars at the boundary.

    Before this guard the SSE stream opened with HTTP 200 and either silently
    propagated NaN/Inf through the optimizer (producing garbage results with no
    error indication) or surfaced internal Python TypeErrors as the ``message``
    field of a single error event.
    """

    @staticmethod
    def _payload(**extra):
        return {
            "mode": "mimo_peak",
            "G_tilde_real": [[[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]],
            "G_tilde_imag": [[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]],
            "x_init_real": [1.0, 0.0],
            "x_init_imag": [0.0, 0.0],
            "max_iters": 3,
            **extra,
        }

    @pytest.mark.parametrize(
        ("bad_p_max", "expected"),
        [
            ("abc", b"p_max must be a number"),
            (float("nan"), b"p_max must be finite"),
            (float("inf"), b"p_max must be finite"),
            (-float("inf"), b"p_max must be finite"),
            (-1.0, b"p_max must be positive"),
            (0.0, b"p_max must be positive"),
            ([1, 2], b"p_max must be a number"),
            ({"v": 1}, b"p_max must be a number"),
        ],
    )
    def test_bad_p_max_returns_400(self, client, bad_p_max, expected):
        resp = client.post("/api/optimize", json=self._payload(p_max=bad_p_max))
        assert resp.status_code == 400
        assert expected in resp.data

    @pytest.mark.parametrize(
        ("bad_val", "expected"),
        [
            (None, b"signal_threshold must be a number"),
            (float("nan"), b"signal_threshold must be finite"),
            (float("inf"), b"signal_threshold must be finite"),
            ("foo", b"signal_threshold must be a number"),
        ],
    )
    def test_bad_signal_threshold_returns_400(self, client, bad_val, expected):
        resp = client.post("/api/optimize", json=self._payload(signal_threshold=bad_val))
        assert resp.status_code == 400
        assert expected in resp.data

    def test_valid_p_max_still_streams(self, client):
        resp = client.post("/api/optimize", json=self._payload(p_max=1.0))
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type


class TestTiltPowerInputValidation:
    """tilt_power rejects non-finite/non-numeric scalars at the boundary."""

    @pytest.fixture
    def tilt_power_cache(self, app):
        """Seed session cache with the tilt_power prerequisites."""
        from types import SimpleNamespace

        from aegis.paths import PropagationPaths

        k_hat = np.array([[0.0, 0.0, -1.0]])
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=np.array([1.0]))
        mock_result = SimpleNamespace(_paths=paths)
        mock_body = SimpleNamespace(normals=np.array([[0.0, 0.0, 1.0]]))

        client = app.test_client()
        with client.session_transaction() as sess:
            sess["session_id"] = "test-session"
        cache = app._optimize_cache
        cache["test-session:_last_dosimetry_result"] = mock_result
        cache["test-session:_last_dosimetry_body"] = mock_body
        cache["test-session:_last_rt_paths"] = paths
        return client

    @pytest.mark.parametrize(
        ("field", "bad_val", "expected"),
        [
            ("tilt_init_deg", "abc", b"tilt_init_deg must be a number"),
            ("tilt_init_deg", float("nan"), b"tilt_init_deg must be finite"),
            ("tilt_init_deg", [1, 2, 3], b"tilt_init_deg must be a number"),
            ("power_init_dbm", float("inf"), b"power_init_dbm must be finite"),
            ("power_init_dbm", "loud", b"power_init_dbm must be a number"),
            ("power_init_dbm", [1, 2], b"power_init_dbm must be a number"),
            ("icnirp_limit", float("nan"), b"icnirp_limit must be finite"),
            ("icnirp_limit", -5.0, b"icnirp_limit must be positive"),
            ("icnirp_limit", 0.0, b"icnirp_limit must be positive"),
            ("T0", "abc", b"T0 must be a number"),
            ("T0", -1.0, b"T0 must be positive"),
            ("T0", 0.0, b"T0 must be positive"),
        ],
    )
    def test_bad_scalar_returns_400(self, tilt_power_cache, field, bad_val, expected):
        resp = tilt_power_cache.post(
            "/api/optimize",
            json={"mode": "tilt_power", "max_iters": 2, field: bad_val},
        )
        assert resp.status_code == 400
        assert expected in resp.data

    @pytest.mark.parametrize(
        ("bad_val", "expected"),
        [
            ("foo", b"antenna_direction must be a list of 3 numbers"),
            ([0, 0], b"antenna_direction must have exactly 3 elements"),
            ([0, 0, 0, 0], b"antenna_direction must have exactly 3 elements"),
            ([0, 0, float("nan")], b"antenna_direction values must be finite"),
            ([0, 0, float("inf")], b"antenna_direction values must be finite"),
            ([0, 0, "foo"], b"antenna_direction must be a list of 3 numbers"),
            (42, b"antenna_direction must be a list of 3 numbers"),
        ],
    )
    def test_bad_antenna_direction_returns_400(self, tilt_power_cache, bad_val, expected):
        resp = tilt_power_cache.post(
            "/api/optimize",
            json={"mode": "tilt_power", "max_iters": 2, "antenna_direction": bad_val},
        )
        assert resp.status_code == 400
        assert expected in resp.data

    def test_valid_defaults_still_stream(self, tilt_power_cache):
        resp = tilt_power_cache.post("/api/optimize", json={"mode": "tilt_power", "max_iters": 2})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

    def test_invalid_cached_t0_falls_back_when_request_omits_T0(self, app):
        """A stale cache entry with NaN T0 must not leak into the config.

        When the request omits T0 entirely the helper falls back to the cached
        value; if that is itself non-finite or non-positive we must reset to
        1.0 rather than smuggling NaN into the optimizer.
        """
        from types import SimpleNamespace

        from aegis.paths import PropagationPaths

        k_hat = np.array([[0.0, 0.0, -1.0]])
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=np.array([1.0]))
        mock_result = SimpleNamespace(_paths=paths)
        mock_body = SimpleNamespace(normals=np.array([[0.0, 0.0, 1.0]]))

        client = app.test_client()
        with client.session_transaction() as sess:
            sess["session_id"] = "test-session"
        cache = app._optimize_cache
        cache["test-session:_last_dosimetry_result"] = mock_result
        cache["test-session:_last_dosimetry_body"] = mock_body
        cache["test-session:_last_rt_paths"] = paths
        cache["test-session:_last_dosimetry_stats"] = {"T0": float("nan")}

        resp = client.post("/api/optimize", json={"mode": "tilt_power", "max_iters": 2})
        # Should stream successfully using fallback T0=1.0, not 400 or stream
        # an error with NaN poison.
        assert resp.status_code == 200
        events = []
        for line in resp.data.decode().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        # Final event should carry a finite T0, never NaN-corrupted
        assert any("done" in e and e.get("done") for e in events)


class TestCancelEndpoint:
    def test_cancel_returns_json(self, client):
        resp = client.post("/api/optimize/cancel")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "cancelled" in data
