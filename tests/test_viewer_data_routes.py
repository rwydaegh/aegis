"""Tests for the data-serving viewer routes (data.py).

Covers: /api/body, /api/voxels, /api/tiles, /api/config, /api/clear-cache,
/api/export-config, /api/viewer-config, /api/body/info, /api/levels.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("flask")


@pytest.fixture()
def app():
    """Create a test Flask app with the e2e_icosahedron body."""
    from aegis.viewer.config import load_config
    from aegis.viewer.server import create_app

    data_dir = str(Path(__file__).parent / "fixtures" / "e2e_lab")
    cfg = load_config()  # full defaults
    cfg["server"]["port"] = 5097
    app = create_app(
        data_dir=data_dir,
        body_name="e2e_icosahedron",
        config=cfg,
    )
    app.config["TESTING"] = True
    return app


# ---------------------------------------------------------------------------
# GET /api/body
# ---------------------------------------------------------------------------


class TestBodyRoute:
    def test_default_body_returns_binary(self, app):
        with app.test_client() as c:
            resp = c.get("/api/body")
            assert resp.status_code == 200
            assert resp.content_type == "application/octet-stream"
            assert len(resp.data) > 0

    def test_body_has_x_meta_header(self, app):
        with app.test_client() as c:
            resp = c.get("/api/body")
            meta_raw = resp.headers.get("X-Meta")
            assert meta_raw is not None
            meta = json.loads(meta_raw)
            assert "n_triangles" in meta
            assert meta["n_triangles"] > 0

    def test_body_by_name(self, app):
        with app.test_client() as c:
            resp = c.get("/api/body?name=e2e_icosahedron")
            assert resp.status_code == 200
            assert resp.content_type == "application/octet-stream"

    def test_unknown_body_returns_404(self, app):
        with app.test_client() as c:
            resp = c.get("/api/body?name=nonexistent_phantom")
            assert resp.status_code == 404
            data = resp.get_json()
            assert "error" in data


# ---------------------------------------------------------------------------
# GET /api/body/info
# ---------------------------------------------------------------------------


class TestBodyInfoRoute:
    def test_body_info_returns_metadata(self, app):
        with app.test_client() as c:
            resp = c.get("/api/body/info")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["name"] == "e2e_icosahedron"
            assert data["n_triangles"] > 0
            assert "total_area" in data
            assert "bounding_box" in data
            assert "min" in data["bounding_box"]
            assert "max" in data["bounding_box"]


# ---------------------------------------------------------------------------
# GET /api/voxels
# ---------------------------------------------------------------------------


class TestVoxelsRoute:
    def test_no_voxels_returns_404(self, app):
        with app.test_client() as c:
            resp = c.get("/api/voxels")
            assert resp.status_code == 404
            data = resp.get_json()
            assert "error" in data

    def test_voxels_returns_binary_when_cached(self, app):
        """Inject voxel data into cache, verify binary response."""
        from aegis.viewer.server import _cache, _cache_lock

        fake_binary = b"\x00" * 120
        fake_meta = {"n_voxels": 10, "median_size": 0.5}
        with _cache_lock:
            _cache["voxel_binary"] = fake_binary
            _cache["voxel_meta"] = fake_meta

        with app.test_client() as c:
            resp = c.get("/api/voxels")
            assert resp.status_code == 200
            assert resp.content_type == "application/octet-stream"
            assert resp.data == fake_binary
            meta = json.loads(resp.headers["X-Meta"])
            assert meta["n_voxels"] == 10

        with _cache_lock:
            _cache["voxel_binary"] = None
            _cache["voxel_meta"] = None


# ---------------------------------------------------------------------------
# GET /api/tiles
# ---------------------------------------------------------------------------


class TestTilesRoute:
    def test_no_tiles_returns_empty_list(self, app):
        with app.test_client() as c:
            resp = c.get("/api/tiles")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["tiles"] == []
            assert data["transform"] is None


# ---------------------------------------------------------------------------
# GET /api/viewer-config
# ---------------------------------------------------------------------------


class TestViewerConfigRoute:
    def test_returns_config_dict(self, app):
        with app.test_client() as c:
            resp = c.get("/api/viewer-config")
            assert resp.status_code == 200
            data = resp.get_json()
            assert isinstance(data, dict)
            # Config should have dosimetry and server sections at minimum
            assert "dosimetry" in data or "server" in data


# ---------------------------------------------------------------------------
# GET /api/config
# ---------------------------------------------------------------------------


class TestConfigRoute:
    def test_config_returns_capabilities(self, app):
        with app.test_client() as c:
            resp = c.get("/api/config")
            assert resp.status_code == 200
            data = resp.get_json()
            assert "bodies" in data
            assert isinstance(data["bodies"], list)
            assert "e2e_icosahedron" in data["bodies"]
            assert "body_name" in data
            assert "skin_models" in data
            assert "levels" in data
            assert isinstance(data["levels"], list)
            assert "has_voxels" in data
            assert "has_differt" in data
            assert "has_sionna" in data


# ---------------------------------------------------------------------------
# GET /api/levels
# ---------------------------------------------------------------------------


class TestLevelsRoute:
    def test_returns_all_nine_levels(self, app):
        with app.test_client() as c:
            resp = c.get("/api/levels")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data) == 9
            levels = [entry["level"] for entry in data]
            assert levels == list(range(9))
            # Each entry has name and description
            for entry in data:
                assert "name" in entry
                assert "description" in entry
                assert len(entry["description"]) > 10


# ---------------------------------------------------------------------------
# POST /api/clear-cache
# ---------------------------------------------------------------------------


class TestClearCacheRoute:
    def test_clear_cache_returns_ok(self, app):
        with app.test_client() as c:
            resp = c.post("/api/clear-cache")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["ok"] is True

    def test_clear_cache_removes_voxel_data(self, app):
        from aegis.viewer.server import _cache, _cache_lock

        with _cache_lock:
            _cache["voxel_binary"] = b"\x00"
            _cache["voxel_meta"] = {"test": True}
            _cache["mimo_scene"] = "dummy"

        with app.test_client() as c:
            c.post("/api/clear-cache")

        assert _cache.get("voxel_binary") is None
        assert _cache.get("voxel_meta") is None
        assert _cache.get("mimo_scene") is None


# ---------------------------------------------------------------------------
# POST /api/export-config
# ---------------------------------------------------------------------------


class TestExportConfigRoute:
    def test_export_config_base(self, app):
        """Without interactive state, returns the base config."""
        with app.test_client() as c:
            resp = c.post("/api/export-config", json={})
            assert resp.status_code == 200
            data = resp.get_json()
            assert isinstance(data, dict)

    def test_export_config_overlays_freq(self, app):
        with app.test_client() as c:
            resp = c.post("/api/export-config", json={"freqGhz": 28.0})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["dosimetry"]["freq_hz"] == pytest.approx(28.0e9)

    def test_export_config_overlays_power(self, app):
        with app.test_client() as c:
            resp = c.post("/api/export-config", json={"powerDbm": 40.0})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["dosimetry"]["default_power_dbm"] == pytest.approx(40.0)

    def test_export_config_mode_bound(self, app):
        with app.test_client() as c:
            resp = c.post("/api/export-config", json={"mode": "bound"})
            data = resp.get_json()
            assert data["dosimetry"]["default_level"] == 0

    def test_export_config_mode_aggregate(self, app):
        with app.test_client() as c:
            resp = c.post("/api/export-config", json={"mode": "aggregate"})
            data = resp.get_json()
            assert data["dosimetry"]["default_level"] == 1

    def test_export_config_mode_detailed_with_toggles(self, app):
        with app.test_client() as c:
            resp = c.post(
                "/api/export-config",
                json={
                    "mode": "detailed",
                    "fresnel": True,
                    "polarisation": True,
                    "curvature": True,
                },
            )
            data = resp.get_json()
            assert data["dosimetry"]["default_level"] == 5

    def test_export_config_body_name(self, app):
        with app.test_client() as c:
            resp = c.post("/api/export-config", json={"bodyName": "duke"})
            data = resp.get_json()
            assert data["body"]["default_name"] == "duke"

    def test_export_config_skin_model(self, app):
        with app.test_client() as c:
            resp = c.post("/api/export-config", json={"skinModel": "itis"})
            data = resp.get_json()
            assert data["dosimetry"]["skin_model"] == "itis"
