"""Real integration tests for /api/environment/* routes.

Exercises mesh construction from voxels/GeoJSON, binary serialization,
the mesh cache, format export (DiffeRT/Sionna), and the material catalog.
OSM and 3D-Tiles calls require network access; those are marked ``@slow``
and skipped when the network backing is unavailable.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")


# ---------------------------------------------------------------------------
# /api/environment/materials
# ---------------------------------------------------------------------------


class TestEnvironmentMaterials:
    def test_returns_material_catalog(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/environment/materials")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "materials" in data
        assert len(data["materials"]) > 0
        for mat in data["materials"]:
            assert "id" in mat
            assert "name" in mat
            assert isinstance(mat["name"], str)

    def test_catalog_includes_known_materials(self, viewer_app):
        """Common building materials must be in the catalog."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/environment/materials")
        names = {m["name"] for m in resp.get_json()["materials"]}
        assert "concrete" in names
        assert "glass" in names


# ---------------------------------------------------------------------------
# /api/environment/mesh (GET)
# ---------------------------------------------------------------------------


class TestEnvironmentMeshCached:
    def test_no_cached_mesh_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/environment/mesh")
        assert resp.status_code == 404

    def test_cached_mesh_returns_binary(self, viewer_app):
        from aegis.environment import EnvironmentMesh
        from aegis.viewer.server import _cache, _cache_lock

        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        tris = np.array([[0, 1, 2]], dtype=np.uint32)
        normals = np.array([[0, 0, 1]], dtype=np.float32)
        materials = np.array([0], dtype=np.uint8)

        mesh = EnvironmentMesh(
            vertices=verts,
            triangles=tris,
            normals=normals,
            materials=materials,
            origin_lat=51.05,
            origin_lon=3.72,
            source="test",
        )

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "mesh-get-test"
            with _cache_lock:
                _cache["mesh-get-test:env_mesh"] = mesh
            try:
                resp = c.get("/api/environment/mesh")
                assert resp.status_code == 200
                assert resp.content_type == "application/octet-stream"
                meta = json.loads(resp.headers["X-Meta"])
                assert meta.get("n_triangles") == 1
            finally:
                with _cache_lock:
                    _cache.pop("mesh-get-test:env_mesh", None)


# ---------------------------------------------------------------------------
# /api/environment/from-voxels (POST)
# ---------------------------------------------------------------------------


class TestEnvironmentFromVoxels:
    def test_no_voxel_data_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/from-voxels", json={"lat": 0, "lon": 0})
        assert resp.status_code == 404

    def test_from_voxels_happy_path(self, viewer_app):
        """Inject voxel positions and produce a cube mesh."""
        from aegis.viewer.server import _cache, _cache_lock

        with _cache_lock:
            _cache["voxel_positions"] = np.array([[0, 0, 0], [1, 1, 1], [2, 0, 0.5]], dtype=np.float32)
            _cache["voxel_sizes"] = np.array([0.5, 0.5, 0.5], dtype=np.float32)
            _cache["voxel_materials"] = np.array([0, 1, 2], dtype=np.uint8)

        try:
            with viewer_app.test_client() as c:
                resp = c.post("/api/environment/from-voxels", json={"lat": 51.05, "lon": 3.72})
            assert resp.status_code == 200
            assert resp.content_type == "application/octet-stream"
            meta = json.loads(resp.headers["X-Meta"])
            # 3 voxels * 12 triangles each = 36 triangles
            assert meta["n_triangles"] == 36
        finally:
            with _cache_lock:
                for key in ("voxel_positions", "voxel_sizes", "voxel_materials"):
                    _cache.pop(key, None)

    def test_from_voxels_uses_default_size_when_missing(self, viewer_app):
        """When voxel_sizes is absent, falls back to config default."""
        from aegis.viewer.server import _cache, _cache_lock

        with _cache_lock:
            _cache["voxel_positions"] = np.array([[0, 0, 0]], dtype=np.float32)
            _cache.pop("voxel_sizes", None)
            _cache.pop("voxel_materials", None)

        try:
            with viewer_app.test_client() as c:
                resp = c.post("/api/environment/from-voxels", json={"lat": 0, "lon": 0})
            assert resp.status_code == 200
        finally:
            with _cache_lock:
                for key in ("voxel_positions", "voxel_sizes", "voxel_materials"):
                    _cache.pop(key, None)

    def test_from_voxels_invalid_lat_type(self, viewer_app):
        from aegis.viewer.server import _cache, _cache_lock

        with _cache_lock:
            _cache["voxel_positions"] = np.array([[0, 0, 0]], dtype=np.float32)

        try:
            with viewer_app.test_client() as c:
                resp = c.post("/api/environment/from-voxels", json={"lat": "abc", "lon": 0})
            assert resp.status_code == 400
            assert "numbers" in resp.get_json()["error"]
        finally:
            with _cache_lock:
                _cache.pop("voxel_positions", None)


# ---------------------------------------------------------------------------
# /api/environment/combine (POST)
# ---------------------------------------------------------------------------


class TestEnvironmentCombine:
    def test_combine_no_sources_cached_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/combine", json={})
        assert resp.status_code == 404

    def test_combine_single_source(self, viewer_app):
        """Cache a single source mesh, combine returns it verbatim."""
        from aegis.environment import EnvironmentMesh
        from aegis.viewer.server import _cache, _cache_lock

        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        tris = np.array([[0, 1, 2]], dtype=np.uint32)
        normals = np.array([[0, 0, 1]], dtype=np.float32)
        mats = np.array([0], dtype=np.uint8)

        mesh = EnvironmentMesh(
            vertices=verts,
            triangles=tris,
            normals=normals,
            materials=mats,
            origin_lat=51.05,
            origin_lon=3.72,
            source="osm",
        )

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "combine-test"
            with _cache_lock:
                _cache["combine-test:env_mesh_osm"] = mesh
            try:
                resp = c.post(
                    "/api/environment/combine",
                    json={"sources": ["osm", "tiles", "voxels"]},
                )
                assert resp.status_code == 200
                meta = json.loads(resp.headers["X-Meta"])
                assert meta["n_triangles"] == 1
            finally:
                with _cache_lock:
                    for k in list(_cache.keys()):
                        if k.startswith("combine-test:"):
                            _cache.pop(k, None)


# ---------------------------------------------------------------------------
# /api/environment/geojson (POST)
# ---------------------------------------------------------------------------


class TestEnvironmentGeojson:
    def test_missing_geojson_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/geojson", json={})
        assert resp.status_code == 400
        assert "geojson" in resp.get_json()["error"]

    def test_invalid_lat_lon_type(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/environment/geojson",
                json={"geojson": "{}", "lat": "north", "lon": 0},
            )
        assert resp.status_code == 400
        assert "numbers" in resp.get_json()["error"]

    def test_geojson_string_with_numeric_height(self, viewer_app):
        """A GeoJSON feature with numeric 'height' property.

        Regression: the backend helper ``_parse_height`` used to call
        ``.split()`` on whatever ``tags["height"]`` held, which broke for
        numeric heights (fine from OSM XML but not GeoJSON).
        """
        gj = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]]],
                        },
                        "properties": {"height": "10", "building": "yes"},
                    }
                ],
            }
        )
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/environment/geojson",
                json={"geojson": gj, "lat": 51.05, "lon": 3.72},
            )
        # Should succeed for string height (OSM-compatible)
        assert resp.status_code == 200
        meta = json.loads(resp.headers["X-Meta"])
        assert meta["n_triangles"] > 0

    def test_geojson_with_int_height(self, viewer_app):
        """A GeoJSON property with an integer height (common in JSON bodies).

        Regression: ``_parse_height`` used to crash with
        ``AttributeError: 'int' object has no attribute 'split'``.
        """
        gj = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]]],
                        },
                        "properties": {"height": 10, "building": "yes"},
                    }
                ],
            }
        )
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/environment/geojson",
                json={"geojson": gj, "lat": 51.05, "lon": 3.72},
            )
        assert resp.status_code == 200
        meta = json.loads(resp.headers["X-Meta"])
        assert meta["n_triangles"] > 0

    def test_empty_geojson_collection(self, viewer_app):
        """An empty FeatureCollection returns 200 with zero triangles or a
        graceful 400 - never a 500."""
        gj = json.dumps({"type": "FeatureCollection", "features": []})
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/environment/geojson",
                json={"geojson": gj, "lat": 51.05, "lon": 3.72},
            )
        assert resp.status_code in (200, 400)


# ---------------------------------------------------------------------------
# /api/environment/export-scene (POST)
# ---------------------------------------------------------------------------


class TestEnvironmentExportScene:
    def test_no_cached_mesh_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/export-scene", json={"format": "differt"})
        assert resp.status_code == 404

    def test_export_differt(self, viewer_app):
        from aegis.environment import EnvironmentMesh
        from aegis.viewer.server import _cache, _cache_lock

        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.float32)
        tris = np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32)
        normals = np.array([[0, 0, 1], [0, 0, 1]], dtype=np.float32)
        mats = np.array([0, 0], dtype=np.uint8)

        mesh = EnvironmentMesh(
            vertices=verts,
            triangles=tris,
            normals=normals,
            materials=mats,
            origin_lat=0,
            origin_lon=0,
            source="test",
        )

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "export-differt"
            with _cache_lock:
                _cache["export-differt:env_mesh"] = mesh
            try:
                resp = c.post(
                    "/api/environment/export-scene",
                    json={"format": "differt"},
                )
                assert resp.status_code == 200
                data = resp.get_json()
                assert data["ok"] is True
                assert data["format"] == "differt"
                assert data["n_triangles"] == 2
            finally:
                with _cache_lock:
                    _cache.pop("export-differt:env_mesh", None)

    def test_export_sionna(self, viewer_app):
        from aegis.environment import EnvironmentMesh
        from aegis.viewer.server import _cache, _cache_lock

        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        tris = np.array([[0, 1, 2]], dtype=np.uint32)
        normals = np.array([[0, 0, 1]], dtype=np.float32)
        mats = np.array([0], dtype=np.uint8)

        mesh = EnvironmentMesh(
            vertices=verts,
            triangles=tris,
            normals=normals,
            materials=mats,
            origin_lat=0,
            origin_lon=0,
            source="test",
        )

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "export-sionna"
            with _cache_lock:
                _cache["export-sionna:env_mesh"] = mesh
            try:
                resp = c.post(
                    "/api/environment/export-scene",
                    json={"format": "sionna"},
                )
                # Either 200 with XML or 500 if mitsuba not available
                assert resp.status_code in (200, 500)
                if resp.status_code == 200:
                    assert "xml" in resp.content_type
                    assert b"<scene" in resp.data or b"<?xml" in resp.data
            finally:
                with _cache_lock:
                    _cache.pop("export-sionna:env_mesh", None)

    def test_export_unknown_format(self, viewer_app):
        from aegis.environment import EnvironmentMesh
        from aegis.viewer.server import _cache, _cache_lock

        verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        mesh = EnvironmentMesh(
            vertices=verts,
            triangles=np.array([[0, 1, 2]], dtype=np.uint32),
            normals=np.array([[0, 0, 1]], dtype=np.float32),
            materials=np.array([0], dtype=np.uint8),
            origin_lat=0,
            origin_lon=0,
            source="test",
        )

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "export-unknown"
            with _cache_lock:
                _cache["export-unknown:env_mesh"] = mesh
            try:
                resp = c.post("/api/environment/export-scene", json={"format": "blender"})
                assert resp.status_code == 400
                assert "Unknown format" in resp.get_json()["error"]
            finally:
                with _cache_lock:
                    _cache.pop("export-unknown:env_mesh", None)


# ---------------------------------------------------------------------------
# /api/environment/osm (POST) - validation only (no network)
# ---------------------------------------------------------------------------


class TestEnvironmentOsmValidation:
    def test_missing_lat_lon_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/osm", json={})
        assert resp.status_code == 400

    def test_lat_out_of_range(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/osm", json={"lat": 200, "lon": 0})
        assert resp.status_code == 400
        assert "-90" in resp.get_json()["error"]

    def test_lon_out_of_range(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/osm", json={"lat": 0, "lon": 200})
        assert resp.status_code == 400

    def test_nan_lat_rejected(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/osm", json={"lat": float("nan"), "lon": 0})
        assert resp.status_code == 400

    def test_inf_lat_rejected(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/osm", json={"lat": float("inf"), "lon": 0})
        assert resp.status_code == 400

    def test_radius_out_of_range(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/osm", json={"lat": 0, "lon": 0, "radius": 1e9})
        assert resp.status_code == 400

    def test_negative_radius(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/osm", json={"lat": 0, "lon": 0, "radius": -50})
        assert resp.status_code == 400

    def test_non_numeric_types(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/osm", json={"lat": "north", "lon": "east"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /api/environment/3dtiles (POST) - validation only
# ---------------------------------------------------------------------------


class TestEnvironment3DTilesValidation:
    def test_missing_lat_lon(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/3dtiles", json={})
        assert resp.status_code == 400

    def test_missing_api_key(self, viewer_app, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with viewer_app.test_client() as c:
            resp = c.post("/api/environment/3dtiles", json={"lat": 51.05, "lon": 3.72})
        assert resp.status_code == 400
        assert "API key" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# /api/cache/environments (DELETE)
# ---------------------------------------------------------------------------


class TestClearEnvironmentCache:
    def test_delete_clears_cache(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.delete("/api/cache/environments")
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True


# ---------------------------------------------------------------------------
# Unicode / malformed
# ---------------------------------------------------------------------------


class TestEnvironmentMalformed:
    def test_binary_body_to_osm(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/environment/osm",
                data=b"\xff\xfe",
                content_type="application/json",
            )
        # get_json(silent=True) gives None; defaults to {} so lat is missing -> 400
        assert resp.status_code == 400

    def test_unicode_keys_ignored(self, viewer_app):
        """Unknown unicode keys don't crash the route."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/environment/osm",
                json={"résumé": 1, "こんにちは": "x", "lat": 0, "lon": 0, "radius": 100},
            )
        # valid params despite unknown unicode siblings - may hit network or
        # validate and 400, but never 500
        assert resp.status_code != 500
