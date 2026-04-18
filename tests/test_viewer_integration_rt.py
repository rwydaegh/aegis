"""Real integration tests for /api/compute/rt (DiffeRT ray-traced dosimetry).

These tests exercise the full Flask -> DiffeRT -> DosimetryEngine stack with
no mocks. They use the bundled ``data/scenes/box/box.xml`` scene and the
``e2e_icosahedron`` body fixture so they run without network access.

RT computes are slow (~2-5s per call) so most tests carry the ``@slow``
marker.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")

# Skip entire module when DiffeRT is not installed
_differt = pytest.importorskip("differt", reason="RT tests require DiffeRT (pip install aegis[rt])")


_BOX_SCENE = "/home/user/aegis/data/scenes/box/box.xml"


def _scene_available() -> bool:
    from pathlib import Path

    return Path(_BOX_SCENE).exists()


# ---------------------------------------------------------------------------
# Invalid payloads (fast, no RT invocation)
# ---------------------------------------------------------------------------


class TestComputeRtInvalidPayload:
    def test_garbage_body_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute/rt", data=b"\xff\xfe", content_type="application/json")
        assert resp.status_code == 400
        assert "JSON" in resp.get_json()["error"]

    def test_null_body_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute/rt", data=b"null", content_type="application/json")
        assert resp.status_code == 400

    def test_array_body_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute/rt", data=b"[1,2,3]", content_type="application/json")
        assert resp.status_code == 400

    def test_no_scene_or_voxels_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute/rt", json={"antenna_pos": [5, 0, 1]})
        assert resp.status_code == 400
        assert "scene" in resp.get_json()["error"].lower() or "voxel" in resp.get_json()["error"].lower()

    def test_path_traversal_rejected(self, viewer_app):
        """Scene path outside allowlist must return 400, not read arbitrary files."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"scene_path": "/etc/passwd", "antenna_pos": [5, 0, 1]},
            )
        assert resp.status_code == 400
        assert "Invalid scene path" in resp.get_json()["error"]

    def test_unknown_body_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"body_name": "ghost_phantom", "antenna_pos": [5, 0, 1]},
            )
        assert resp.status_code == 404

    @pytest.mark.skipif(not _scene_available(), reason="box scene not available")
    def test_invalid_mode(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"scene_path": _BOX_SCENE, "mode": "turbo"},
            )
        assert resp.status_code == 400
        assert "mode" in resp.get_json()["error"]

    @pytest.mark.skipif(not _scene_available(), reason="box scene not available")
    def test_invalid_level_string(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"scene_path": _BOX_SCENE, "level": "abc"},
            )
        assert resp.status_code == 400

    @pytest.mark.skipif(not _scene_available(), reason="box scene not available")
    def test_level_out_of_range(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"scene_path": _BOX_SCENE, "level": 99},
            )
        assert resp.status_code == 400

    @pytest.mark.skipif(not _scene_available(), reason="box scene not available")
    def test_power_dbm_nan_rejected(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"scene_path": _BOX_SCENE, "power_dbm": float("nan")},
            )
        assert resp.status_code == 400
        assert "finite" in resp.get_json()["error"]

    @pytest.mark.skipif(not _scene_available(), reason="box scene not available")
    def test_power_dbm_inf_rejected(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"scene_path": _BOX_SCENE, "power_dbm": float("inf")},
            )
        assert resp.status_code == 400

    @pytest.mark.skipif(not _scene_available(), reason="box scene not available")
    def test_power_dbm_out_of_range(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"scene_path": _BOX_SCENE, "power_dbm": 150},
            )
        assert resp.status_code == 400
        assert "100" in resp.get_json()["error"]

    @pytest.mark.skipif(not _scene_available(), reason="box scene not available")
    def test_antenna_pos_wrong_length(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"scene_path": _BOX_SCENE, "antenna_pos": [1, 2]},
            )
        assert resp.status_code == 400

    @pytest.mark.skipif(not _scene_available(), reason="box scene not available")
    def test_freq_hz_non_numeric(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"scene_path": _BOX_SCENE, "freq_hz": "loud"},
            )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Happy path (slow, requires DiffeRT + box scene)
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not _scene_available(), reason="box scene not available")
class TestComputeRtHappyPath:
    def test_basic_rt_compute_box_scene(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={
                    "antenna_pos": [5.0, 0.0, 1.0],
                    "scene_path": _BOX_SCENE,
                    "power_dbm": 23.0,
                    "level": 2,
                    "freq_hz": 28e9,
                },
            )
        assert resp.status_code == 200, resp.data[:300]
        assert resp.content_type == "application/octet-stream"
        stats = json.loads(resp.headers["X-Stats"])
        assert stats["n_triangles"] == 20
        assert stats["n_rt_paths"] >= 1  # at least LoS
        assert stats["peak_sab"] >= 0.0
        assert np.isfinite(stats["peak_sab"])
        assert "path_viz" in stats
        assert "timings" in stats
        assert "rt_ms" in stats["timings"]

    def test_rt_with_voxel_scene(self, viewer_app):
        """Use cached voxels as the scene (no explicit scene_path)."""
        from aegis.viewer.server import _cache, _cache_lock

        with _cache_lock:
            _cache["voxel_positions"] = np.array([[0, 0, 0.5], [2, 0, 0.5]], dtype=np.float32)
            _cache["voxel_sizes"] = np.array([0.5, 0.5], dtype=np.float32)
            _cache["voxel_materials"] = np.array([0, 0], dtype=np.uint8)

        try:
            with viewer_app.test_client() as c:
                resp = c.post(
                    "/api/compute/rt",
                    json={
                        "antenna_pos": [5.0, 0.0, 1.0],
                        "power_dbm": 23.0,
                        "level": 2,
                    },
                )
            assert resp.status_code == 200, resp.data[:300]
            stats = json.loads(resp.headers["X-Stats"])
            assert stats["n_rt_paths"] >= 0  # may be zero if LoS is blocked
        finally:
            with _cache_lock:
                for key in ("voxel_positions", "voxel_sizes", "voxel_materials"):
                    _cache.pop(key, None)

    def test_rt_bound_mode(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={
                    "scene_path": _BOX_SCENE,
                    "mode": "bound",
                    "antenna_pos": [5, 0, 1],
                },
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert stats["mode"] == "bound"

    def test_rt_caches_result_for_csv_export(self, viewer_app):
        """After RT compute, the export cache should be populated."""
        from aegis.viewer.server import _cache, _cache_lock

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "rt-export-test"
            resp = c.post(
                "/api/compute/rt",
                json={
                    "scene_path": _BOX_SCENE,
                    "antenna_pos": [5, 0, 1],
                    "level": 2,
                },
            )
            assert resp.status_code == 200

            # CSV export should now succeed
            resp_csv = c.get("/api/export/dosimetry-csv")
        assert resp_csv.status_code == 200
        assert "text/csv" in resp_csv.content_type

        # Clean up
        with _cache_lock:
            for k in list(_cache.keys()):
                if k.startswith("rt-export-test:"):
                    _cache.pop(k, None)


# ---------------------------------------------------------------------------
# Coordinate-frame boundaries
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not _scene_available(), reason="box scene not available")
class TestComputeRtBoundaries:
    def test_antenna_at_ground_level(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={
                    "scene_path": _BOX_SCENE,
                    "antenna_pos": [3.0, 0.0, 0.0],
                    "power_dbm": 23,
                    "level": 2,
                },
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert np.isfinite(stats["peak_sab"])

    def test_antenna_far_distance(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={
                    "scene_path": _BOX_SCENE,
                    "antenna_pos": [100.0, 0.0, 1.0],
                    "power_dbm": 23,
                    "level": 2,
                },
            )
        # Either valid result or 200 with zero paths (scene may be small)
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert stats["peak_sab"] >= 0.0

    def test_rt_with_body_offset_and_rotation(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={
                    "scene_path": _BOX_SCENE,
                    "antenna_pos": [5, 0, 1],
                    "body_offset": [0.2, -0.1, 0.3],
                    "body_rotation_y": 0.5,
                },
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Frequency edges
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not _scene_available(), reason="box scene not available")
class TestComputeRtFrequencyEdges:
    def test_rt_at_2ghz(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"scene_path": _BOX_SCENE, "freq_hz": 2e9, "antenna_pos": [5, 0, 1]},
            )
        assert resp.status_code == 200

    def test_rt_at_60ghz(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"scene_path": _BOX_SCENE, "freq_hz": 60e9, "antenna_pos": [5, 0, 1]},
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Unicode / malformed
# ---------------------------------------------------------------------------


class TestComputeRtMalformed:
    def test_unicode_body_keys_graceful(self, viewer_app):
        """Unknown unicode keys in body are ignored; missing scene -> 400, not 500."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"résumé": 1, "こんにちは": "x", "antenna_pos": [5, 0, 1]},
            )
        # No scene/voxels loaded -> 400
        assert resp.status_code == 400
        assert resp.status_code != 500
