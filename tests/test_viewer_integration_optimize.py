"""Real integration tests for /api/optimize (placement, mimo_peak, tilt_power).

The route streams SSE events from ``run_optimization``. Tests exercise the full
Flask -> optim loop -> DosimetryEngine pipeline with no mocks.

MIMO tests use synthesized G_tilde channel matrices. Tilt-power tests pre-seed
the session cache with real RT-derived paths + normals. Placement tests use the
free-space fallback (no scene) which is fast enough to avoid the ``@slow`` mark.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")


def _sse_events(resp) -> list[dict]:
    """Parse an SSE response body into a list of event dicts."""
    events = []
    for line in resp.data.decode().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# ---------------------------------------------------------------------------
# Invalid payloads (fast)
# ---------------------------------------------------------------------------


class TestOptimizeInvalidPayload:
    def test_missing_mode_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/optimize", json={})
        assert resp.status_code == 400
        assert "mode is required" in resp.get_json()["error"]

    def test_unknown_mode_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/optimize", json={"mode": "turbo"})
        assert resp.status_code == 400
        assert "mode" in resp.get_json()["error"]

    def test_empty_body_returns_400(self, viewer_app):
        """POST with no body -> 400."""
        with viewer_app.test_client() as c:
            resp = c.post("/api/optimize")
        assert resp.status_code == 400

    def test_garbage_body_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/optimize",
                data=b"\xff\xfe\x00",
                content_type="application/json",
            )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Cancel endpoint
# ---------------------------------------------------------------------------


class TestOptimizeCancel:
    def test_cancel_without_running_job(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/optimize/cancel")
        assert resp.status_code == 200
        assert resp.get_json()["cancelled"] is False


# ---------------------------------------------------------------------------
# mimo_peak mode - synthesized G_tilde (cheap, no mesh)
# ---------------------------------------------------------------------------


class TestOptimizeMimoPeak:
    def _synthesize_payload(self, n_tri: int = 20, n_ant: int = 16):
        rng = np.random.default_rng(42)
        G_tilde = (rng.standard_normal((n_tri, 3, n_ant)) + 1j * rng.standard_normal((n_tri, 3, n_ant))) * 0.01
        x_init = np.conj(G_tilde[0, 0, :]) / np.linalg.norm(G_tilde[0, 0, :])
        return {
            "mode": "mimo_peak",
            "G_tilde_real": G_tilde.real.tolist(),
            "G_tilde_imag": G_tilde.imag.tolist(),
            "x_init_real": x_init.real.tolist(),
            "x_init_imag": x_init.imag.tolist(),
            "p_max": 1.0,
            "max_iters": 3,
        }

    def test_mimo_peak_happy_path(self, viewer_app):
        payload = self._synthesize_payload()
        with viewer_app.test_client() as c:
            resp = c.post("/api/optimize", json=payload)
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type
        events = _sse_events(resp)
        assert len(events) >= 2
        iter_events = [e for e in events if "iter" in e and not e.get("done")]
        assert len(iter_events) >= 1
        # Each iter event carries a base64-encoded sab array and an objective
        for ev in iter_events:
            assert "objective" in ev
            assert "sab_b64" in ev
            assert isinstance(ev["objective"], (int, float))
            assert np.isfinite(ev["objective"])
        # Final event with done=True
        done = [e for e in events if e.get("done")]
        assert len(done) == 1

    def test_mimo_peak_missing_G_tilde_and_no_cache(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/optimize", json={"mode": "mimo_peak", "p_max": 1.0, "max_iters": 3})
        assert resp.status_code == 400
        err = resp.get_json()["error"]
        assert "MIMO" in err or "scene" in err.lower()

    def test_mimo_peak_max_iters_clamped(self, viewer_app):
        """max_iters is clamped to [1, 10_000]."""
        payload = self._synthesize_payload()
        payload["max_iters"] = 1_000_000
        with viewer_app.test_client() as c:
            resp = c.post("/api/optimize", json=payload)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# tilt_power mode - requires cached RT result (synthesized)
# ---------------------------------------------------------------------------


class TestOptimizeTiltPower:
    def test_tilt_power_without_cached_result_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/optimize",
                json={"mode": "tilt_power", "max_iters": 2},
            )
        assert resp.status_code == 400
        err = resp.get_json()["error"]
        assert "cached" in err.lower() or "compute" in err.lower()

    def test_tilt_power_with_cached_paths(self, viewer_app):
        """Seed session cache with RT paths, then run tilt_power."""
        from types import SimpleNamespace

        from aegis.paths import PropagationPaths
        from aegis.viewer.server import _cache, _cache_lock

        k_hat = np.array([[0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=np.array([1.0, 0.5]))
        mock_result = SimpleNamespace(_paths=paths)
        mock_body = SimpleNamespace(normals=np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0]]))

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "tilt-power-test"
            with _cache_lock:
                _cache["tilt-power-test:_last_dosimetry_result"] = mock_result
                _cache["tilt-power-test:_last_dosimetry_body"] = mock_body
                _cache["tilt-power-test:_last_rt_paths"] = paths

            try:
                resp = c.post(
                    "/api/optimize",
                    json={
                        "mode": "tilt_power",
                        "max_iters": 3,
                        "antenna_direction": [0, 0, -1],
                        "tilt_init_deg": 0.0,
                        "power_init_dbm": 23.0,
                        "icnirp_limit": 20.0,
                    },
                )
                assert resp.status_code == 200
                events = _sse_events(resp)
                assert len(events) >= 1
                # No error event
                assert not any(e.get("error") for e in events), events
            finally:
                with _cache_lock:
                    for k in list(_cache.keys()):
                        if k.startswith("tilt-power-test:"):
                            _cache.pop(k, None)


# ---------------------------------------------------------------------------
# placement mode - uses free-space fallback (no scene/voxels/env)
# ---------------------------------------------------------------------------


class TestOptimizePlacement:
    def test_placement_default_level_succeeds(self, viewer_app):
        """Regression: placement used to crash when level/mode not supplied.

        ``_parse_placement_engine_params`` forwarded ``level=None`` to
        ``_parse_mode_or_level`` which short-circuits the default-level
        fallback and throws ``int(None)``.
        """
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/optimize",
                json={
                    "mode": "placement",
                    "max_iters": 2,
                    "grid_size": 2,
                    "grid_spacing": 2.0,
                    "center": [5, 0, 3],
                    "body_name": "e2e_icosahedron",
                },
            )
        assert resp.status_code == 200
        events = _sse_events(resp)
        assert len(events) >= 1

    def test_placement_with_explicit_level(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/optimize",
                json={
                    "mode": "placement",
                    "max_iters": 2,
                    "grid_size": 2,
                    "grid_spacing": 2.0,
                    "center": [5, 0, 3],
                    "body_name": "e2e_icosahedron",
                    "level": 2,
                },
            )
        assert resp.status_code == 200
        events = _sse_events(resp)
        # 2x2 grid: grid iteration events plus a final done event
        iter_events = [e for e in events if "iter" in e and not e.get("done")]
        assert len(iter_events) >= 3
        for ev in iter_events:
            assert ev["stats"]["peak_sab"] >= 0.0

    def test_placement_with_spatial_mode(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/optimize",
                json={
                    "mode": "placement",
                    "max_iters": 2,
                    "grid_size": 2,
                    "grid_spacing": 2.0,
                    "center": [5, 0, 3],
                    "body_name": "e2e_icosahedron",
                    "dosimetry_mode": "spatial",
                },
            )
        assert resp.status_code == 200

    def test_placement_unknown_body_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/optimize",
                json={
                    "mode": "placement",
                    "max_iters": 2,
                    "body_name": "ghost_phantom",
                },
            )
        assert resp.status_code == 400

    def test_placement_grid_size_clamped(self, viewer_app):
        """grid_size is clamped to [1, 50]."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/optimize",
                json={
                    "mode": "placement",
                    "max_iters": 1,
                    "grid_size": 1_000_000,  # should clamp to 50
                    "grid_spacing": 2.0,
                    "center": [5, 0, 3],
                    "body_name": "e2e_icosahedron",
                },
            )
        # Note: grid_size=50 * level-2 would take a long time; just verify
        # the endpoint accepts the payload.
        assert resp.status_code == 200

    def test_placement_bogus_body_offset(self, viewer_app):
        """Wrong-length body_offset should fail cleanly."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/optimize",
                json={
                    "mode": "placement",
                    "max_iters": 1,
                    "grid_size": 1,
                    "body_offset": [1, 2],  # wrong length
                    "body_name": "e2e_icosahedron",
                },
            )
        # Either 400 or SSE stream with error event - must not 500
        assert resp.status_code in (200, 400)


# ---------------------------------------------------------------------------
# Coordinate + frequency edge cases
# ---------------------------------------------------------------------------


class TestOptimizeEdges:
    def test_placement_with_freq_100khz(self, viewer_app):
        """Lower ICNIRP bound - should still complete without a 500."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/optimize",
                json={
                    "mode": "placement",
                    "max_iters": 1,
                    "grid_size": 1,
                    "grid_spacing": 2.0,
                    "center": [5, 0, 3],
                    "body_name": "e2e_icosahedron",
                    "freq_hz": 1e5,
                    "level": 2,
                },
            )
        # 100kHz may cascade errors through the engine; accept 200 or 400
        assert resp.status_code in (200, 400)
        assert resp.status_code != 500

    def test_placement_with_freq_nan_rejected(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/optimize",
                json={
                    "mode": "placement",
                    "max_iters": 1,
                    "grid_size": 1,
                    "freq_hz": float("nan"),
                    "body_name": "e2e_icosahedron",
                    "level": 2,
                },
            )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Unicode / malformed
# ---------------------------------------------------------------------------


class TestOptimizeMalformed:
    def test_unicode_keys_ignored(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/optimize",
                json={"mode": "mimo_peak", "résumé": 1, "こんにちは": "x"},
            )
        # missing G_tilde -> 400, never 500
        assert resp.status_code == 400
