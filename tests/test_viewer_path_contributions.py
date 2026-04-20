"""Tests for /api/analyze/path-contributions route."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("flask")

from aegis.paths import PropagationPaths
from aegis.tissue import SKIN_28GHZ


def _mock_body(n_triangles: int = 6):
    """A minimal BodyMesh-like object compatible with `path_contributions`.

    Uses `BodyMesh.from_vertices` would require real triangles; the analysis
    kernel only touches `normals`, `areas`, and `n_triangles` so a small stub
    is enough and keeps the test fast.
    """
    from types import SimpleNamespace

    rng = np.random.default_rng(0)
    # Normals: mostly +x-facing (3 triangles) so LOS paths from -x illuminate them;
    # 2 triangles facing -x; 1 edge-on to spice up the ReLU mask.
    normals = np.array(
        [
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
    )
    return SimpleNamespace(
        normals=normals[:n_triangles],
        areas=np.full(n_triangles, 1e-4),
        n_triangles=n_triangles,
        centroids=rng.standard_normal((n_triangles, 3)),
        triangles=rng.standard_normal((n_triangles, 3, 3)),
    )


def _mock_paths():
    """Three paths: strong LOS from -x, weaker LOS from above, weak NLOS from -x tilt."""
    k_hat = np.array(
        [
            [1.0, 0.0, 0.0],  # hits +x normals strongly
            [0.8, 0.6, 0.0],  # oblique, weaker contribution
            [0.6, -0.2, 0.77459666924],  # NLOS, even weaker
        ]
    )
    k_hat = k_hat / np.linalg.norm(k_hat, axis=1, keepdims=True)
    # Powers chosen so path 0 dominates clearly
    powers = np.array([10.0, 2.0, 0.5])
    is_los = np.array([True, True, False])
    paths = PropagationPaths.from_powers(k_hat, powers)
    # `from_powers` sets is_los=False for all — patch it for our test.
    return PropagationPaths(
        k_hat=paths.k_hat,
        psi=paths.psi,
        element_index=paths.element_index,
        delay=paths.delay,
        is_los=is_los,
    )


def _inject_rt_cache(viewer_app, body, paths, tissue, sid: str = "test-session"):
    """Seed the session-scoped cache the RT routes normally populate."""
    from aegis.viewer.server import _cache, _cache_lock

    with _cache_lock:
        _cache[f"{sid}:_last_rt_paths"] = paths
        _cache[f"{sid}:_last_dosimetry_body"] = body
        _cache[f"{sid}:_last_rt_tissue"] = tissue


def _clear_rt_cache(sid: str = "test-session"):
    from aegis.viewer.server import _cache, _cache_lock

    with _cache_lock:
        for key in ("_last_rt_paths", "_last_dosimetry_body", "_last_rt_tissue"):
            _cache.pop(f"{sid}:{key}", None)


class TestPathContributionsRoute:
    def test_returns_404_without_cache(self, viewer_app):
        _clear_rt_cache()
        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            resp = c.get("/api/analyze/path-contributions")
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_ranks_paths_by_contribution(self, viewer_app):
        body = _mock_body()
        paths = _mock_paths()
        try:
            with viewer_app.test_client() as c:
                with c.session_transaction() as sess:
                    sess["session_id"] = "test-session"
                _inject_rt_cache(viewer_app, body, paths, SKIN_28GHZ)
                resp = c.get("/api/analyze/path-contributions?top_k=3")
        finally:
            _clear_rt_cache()
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["n_paths"] == 3
        assert data["n_los"] == 2
        assert data["n_nlos"] == 1
        assert len(data["paths"]) == 3
        # Path 0 (direct, high power) must dominate.
        assert data["paths"][0]["index"] == 0
        # Fractions sorted descending and sum to ~1.
        fracs = [p["fraction"] for p in data["paths"]]
        assert fracs == sorted(fracs, reverse=True)
        assert abs(sum(fracs) - 1.0) < 1e-6
        # Cumulative is monotonic.
        cums = [p["cumulative"] for p in data["paths"]]
        assert cums == sorted(cums)
        # k_hat is a length-3 triple of floats.
        assert len(data["paths"][0]["k_hat"]) == 3

    def test_top_k_clamped_and_importance(self, viewer_app):
        body = _mock_body()
        paths = _mock_paths()
        try:
            with viewer_app.test_client() as c:
                with c.session_transaction() as sess:
                    sess["session_id"] = "test-session"
                _inject_rt_cache(viewer_app, body, paths, SKIN_28GHZ)
                # Ask for 100 paths, only 3 exist.
                resp = c.get("/api/analyze/path-contributions?top_k=100")
        finally:
            _clear_rt_cache()
        data = resp.get_json()
        assert len(data["paths"]) == 3
        # Importance top list also bounded by n_paths.
        assert len(data["importance"]["top"]) == 3
        assert data["importance"]["p_abs_total"] > 0

    def test_custom_triangle_index(self, viewer_app):
        body = _mock_body()
        paths = _mock_paths()
        try:
            with viewer_app.test_client() as c:
                with c.session_transaction() as sess:
                    sess["session_id"] = "test-session"
                _inject_rt_cache(viewer_app, body, paths, SKIN_28GHZ)
                resp = c.get("/api/analyze/path-contributions?triangle_index=0")
        finally:
            _clear_rt_cache()
        data = resp.get_json()
        assert data["triangle_index"] == 0

    def test_empty_paths_returns_empty_list(self, viewer_app):
        """n_paths == 0 path: must not crash, returns empty structure."""
        body = _mock_body()
        empty_paths = PropagationPaths.from_powers(np.zeros((0, 3)), np.zeros(0))
        try:
            with viewer_app.test_client() as c:
                with c.session_transaction() as sess:
                    sess["session_id"] = "test-session"
                _inject_rt_cache(viewer_app, body, empty_paths, SKIN_28GHZ)
                resp = c.get("/api/analyze/path-contributions")
        finally:
            _clear_rt_cache()
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["paths"] == []
        assert data["n_paths"] == 0

    def test_json_no_infinity_nan(self, viewer_app):
        body = _mock_body()
        paths = _mock_paths()
        try:
            with viewer_app.test_client() as c:
                with c.session_transaction() as sess:
                    sess["session_id"] = "test-session"
                _inject_rt_cache(viewer_app, body, paths, SKIN_28GHZ)
                resp = c.get("/api/analyze/path-contributions")
        finally:
            _clear_rt_cache()
        raw = resp.get_data(as_text=True)
        assert "Infinity" not in raw
        assert "NaN" not in raw

    def test_stale_cache_cleared_after_non_rt_compute(self, viewer_app):
        """A non-RT /api/compute must invalidate stale _last_rt_paths / _last_rt_tissue.

        Without invalidation, the PathInsightsSection in the Analysis panel
        surfaces the prior RT compute's paths against the *new* (non-RT) body,
        producing misleading "top contributors" for the current compute.
        """
        body = _mock_body()
        paths = _mock_paths()
        try:
            with viewer_app.test_client() as c:
                with c.session_transaction() as sess:
                    sess["session_id"] = "test-session"
                _inject_rt_cache(viewer_app, body, paths, SKIN_28GHZ)
                # Run a non-RT compute. /api/compute/dosimetry writes a fresh body
                # and stats but previously left _last_rt_paths / _last_rt_tissue
                # untouched; they must now be invalidated.
                compute_resp = c.post(
                    "/api/compute",
                    json={
                        "antenna_pos": [1.0, 0.0, 0.5],
                        "power_dbm": 23.0,
                        "level": 2,
                        "freq_hz": 28e9,
                    },
                )
                assert compute_resp.status_code == 200
                resp = c.get("/api/analyze/path-contributions")
        finally:
            _clear_rt_cache()
        assert resp.status_code == 404
        assert "error" in resp.get_json()
