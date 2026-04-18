"""Tests for the environment viewer routes (environment.py) and terrain route.

Covers: /api/environment/osm, /api/environment/from-voxels,
/api/environment/combine, /api/environment/mesh, /api/environment/materials,
/api/environment/geojson, /api/environment/export-scene,
/api/terrain/elevation.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("flask")


@pytest.fixture
def app():
    """Create a test Flask app with the e2e_icosahedron body."""
    from aegis.viewer.config import load_config
    from aegis.viewer.server import create_app

    data_dir = str(Path(__file__).parent / "fixtures" / "e2e_lab")
    cfg = load_config()
    cfg["server"]["port"] = 5096
    app = create_app(
        data_dir=data_dir,
        body_name="e2e_icosahedron",
        config=cfg,
    )
    app.config["TESTING"] = True
    return app


# ---------------------------------------------------------------------------
# GET /api/environment/materials
# ---------------------------------------------------------------------------


class TestEnvironmentMaterials:
    def test_returns_material_catalog(self, app):
        with app.test_client() as c:
            resp = c.get("/api/environment/materials")
            assert resp.status_code == 200
            data = resp.get_json()
            assert "materials" in data
            materials = data["materials"]
            assert len(materials) > 0

            # Each material has expected fields
            for mat in materials:
                assert "id" in mat
                assert "name" in mat
                assert isinstance(mat["name"], str)

    def test_materials_include_concrete(self, app):
        """Concrete is a key construction material and should be in the catalog."""
        with app.test_client() as c:
            resp = c.get("/api/environment/materials")
            names = [m["name"] for m in resp.get_json()["materials"]]
            assert "concrete" in names


# ---------------------------------------------------------------------------
# GET /api/environment/mesh (no mesh cached)
# ---------------------------------------------------------------------------


class TestEnvironmentMesh:
    def test_no_cached_mesh_returns_404(self, app):
        with app.test_client() as c:
            resp = c.get("/api/environment/mesh")
            assert resp.status_code == 404
            data = resp.get_json()
            assert "error" in data

    def test_cached_mesh_returns_binary(self, app):
        """Inject an EnvironmentMesh into cache and verify retrieval."""
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

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:env_mesh"] = mesh

            resp = c.get("/api/environment/mesh")
            assert resp.status_code == 200
            assert resp.content_type == "application/octet-stream"
            assert len(resp.data) > 0
            meta = json.loads(resp.headers["X-Meta"])
            assert "n_triangles" in meta

            with _cache_lock:
                _cache.pop("test-session:env_mesh", None)


# ---------------------------------------------------------------------------
# POST /api/environment/osm (mocked)
# ---------------------------------------------------------------------------


class TestEnvironmentOsm:
    def test_missing_lat_lon_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/environment/osm", json={})
            assert resp.status_code == 400
            assert "lat and lon" in resp.get_json()["error"]

    def test_missing_lat_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/environment/osm", json={"lon": 3.72})
            assert resp.status_code == 400

    def test_missing_lon_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/environment/osm", json={"lat": 51.05})
            assert resp.status_code == 400

    def test_rate_limit_returns_503(self, app):
        from unittest.mock import patch

        with (
            app.test_client() as c,
            patch(
                "aegis.environment.osm.fetch_osm",
                side_effect=_import_and_raise("OverpassRateLimitError"),
            ),
        ):
            resp = c.post("/api/environment/osm", json={"lat": 51.05, "lon": 3.72})
            assert resp.status_code == 503
            assert "Retry-After" in resp.headers

    def test_timeout_returns_504(self, app):
        from unittest.mock import patch

        with (
            app.test_client() as c,
            patch(
                "aegis.environment.osm.fetch_osm",
                side_effect=_import_and_raise("OverpassTimeoutError"),
            ),
        ):
            resp = c.post("/api/environment/osm", json={"lat": 51.05, "lon": 3.72})
            assert resp.status_code == 504

    def test_response_too_large_returns_413(self, app):
        from unittest.mock import patch

        with (
            app.test_client() as c,
            patch(
                "aegis.environment.osm.fetch_osm",
                side_effect=_import_and_raise("OverpassResponseTooLarge"),
            ),
        ):
            resp = c.post("/api/environment/osm", json={"lat": 51.05, "lon": 3.72})
            assert resp.status_code == 413


def _import_and_raise(exc_name: str):
    """Return a callable that raises the named Overpass exception."""
    from aegis.environment.osm import (
        OverpassRateLimitError,
        OverpassResponseTooLarge,
        OverpassTimeoutError,
    )

    exc_map = {
        "OverpassRateLimitError": OverpassRateLimitError,
        "OverpassTimeoutError": OverpassTimeoutError,
        "OverpassResponseTooLarge": OverpassResponseTooLarge,
    }

    def _raise(*args, **kwargs):
        raise exc_map[exc_name]()

    return _raise


# ---------------------------------------------------------------------------
# POST /api/environment/3dtiles
# ---------------------------------------------------------------------------


class TestEnvironment3DTiles:
    def test_missing_lat_lon_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/environment/3dtiles", json={})
            assert resp.status_code == 400

    def test_missing_api_key_returns_400(self, app):
        """Without GOOGLE_API_KEY env var, should return 400."""
        import os
        from unittest.mock import patch

        with (
            app.test_client() as c,
            patch.dict(os.environ, {}, clear=True),
        ):
            resp = c.post("/api/environment/3dtiles", json={"lat": 51.05, "lon": 3.72})
            assert resp.status_code == 400
            assert "API key" in resp.get_json()["error"]

    def test_empty_mesh_returns_404(self, app):
        """Regions outside Google's photorealistic coverage produce an empty
        mesh; the route should surface a user-friendly 404 instead of silently
        returning a valid-but-empty binary."""
        from unittest.mock import patch

        from aegis.environment import EnvironmentMesh

        empty_mesh = EnvironmentMesh(
            vertices=np.zeros((0, 3), dtype=np.float64),
            triangles=np.zeros((0, 3), dtype=np.int32),
            normals=np.zeros((0, 3), dtype=np.float64),
            materials=np.zeros(0, dtype=np.int32),
            origin_lat=51.05,
            origin_lon=3.72,
            source="3dtiles",
        )

        with (
            app.test_client() as c,
            patch("aegis.environment.tiles.TileTraverser.traverse", return_value=empty_mesh),
        ):
            resp = c.post(
                "/api/environment/3dtiles",
                json={"lat": 51.05, "lon": 3.72, "api_key": "fake"},
            )
            assert resp.status_code == 404
            assert "No 3D Tiles" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# POST /api/environment/from-voxels
# ---------------------------------------------------------------------------


class TestEnvironmentFromVoxels:
    def test_no_voxels_returns_404(self, app):
        from aegis.viewer.server import _cache, _cache_lock

        with _cache_lock:
            _cache.pop("voxel_positions", None)

        with app.test_client() as c:
            resp = c.post("/api/environment/from-voxels", json={})
            assert resp.status_code == 404

    def test_non_numeric_lat_returns_400(self, app):
        from aegis.viewer.server import _cache, _cache_lock

        positions = np.array([[0, 0, 0]], dtype=np.float32)
        with _cache_lock:
            _cache["voxel_positions"] = positions
            _cache["voxel_materials"] = np.array([1], dtype=np.uint8)
            _cache["voxel_sizes"] = np.array([0.5], dtype=np.float32)

        with app.test_client() as c:
            resp = c.post("/api/environment/from-voxels", json={"lat": "abc"})
            assert resp.status_code == 400
            assert "numbers" in resp.get_json()["error"]

        with _cache_lock:
            _cache.pop("voxel_positions", None)
            _cache.pop("voxel_materials", None)
            _cache.pop("voxel_sizes", None)

    def test_voxels_to_mesh_returns_binary(self, app):
        from aegis.viewer.server import _cache, _cache_lock

        positions = np.array([[0, 0, 0], [2, 0, 0], [0, 2, 0]], dtype=np.float32)
        materials = np.array([1, 2, 1], dtype=np.uint8)
        sizes = np.array([0.5, 0.5, 0.5], dtype=np.float32)

        with _cache_lock:
            _cache["voxel_positions"] = positions
            _cache["voxel_materials"] = materials
            _cache["voxel_sizes"] = sizes

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            resp = c.post("/api/environment/from-voxels", json={"lat": 51.05, "lon": 3.72})
            assert resp.status_code == 200
            assert resp.content_type == "application/octet-stream"
            assert len(resp.data) > 0
            meta = json.loads(resp.headers["X-Meta"])
            assert meta["n_triangles"] == 3 * 12  # 3 voxels * 12 triangles/cube

        with _cache_lock:
            _cache.pop("voxel_positions", None)
            _cache.pop("voxel_materials", None)
            _cache.pop("voxel_sizes", None)
            _cache.pop("test-session:env_mesh_voxels", None)
            _cache.pop("test-session:env_mesh", None)


# ---------------------------------------------------------------------------
# POST /api/environment/combine
# ---------------------------------------------------------------------------


class TestEnvironmentCombine:
    def test_no_meshes_returns_404(self, app):
        with app.test_client() as c:
            resp = c.post("/api/environment/combine", json={})
            assert resp.status_code == 404

    def test_combine_single_source(self, app):
        """With one cached mesh, combine returns it directly."""
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
            source="osm",
        )

        with app.test_client() as c:
            # Trigger session creation
            c.post("/api/environment/combine", json={})
            with c.session_transaction() as sess:
                sid = sess.get("session_id")
            assert sid is not None
            with _cache_lock:
                _cache[f"{sid}:env_mesh_osm"] = mesh

            resp = c.post("/api/environment/combine", json={"sources": ["osm"]})
            assert resp.status_code == 200
            assert resp.content_type == "application/octet-stream"

            with _cache_lock:
                _cache.pop(f"{sid}:env_mesh_osm", None)
                _cache.pop(f"{sid}:env_mesh", None)


# ---------------------------------------------------------------------------
# POST /api/environment/geojson
# ---------------------------------------------------------------------------


class TestEnvironmentGeoJson:
    def test_missing_geojson_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/environment/geojson", json={})
            assert resp.status_code == 400
            assert "geojson" in resp.get_json()["error"]

    def test_invalid_geojson_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/environment/geojson", json={"geojson": "not valid json"})
            assert resp.status_code == 400

    def test_non_numeric_lat_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/environment/geojson", json={"geojson": "{}", "lat": "abc"})
            assert resp.status_code == 400
            assert "numbers" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# POST /api/environment/export-scene
# ---------------------------------------------------------------------------


class TestEnvironmentExportScene:
    def test_no_mesh_returns_404(self, app):
        from aegis.viewer.server import _cache, _cache_lock

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache.pop("test-session:env_mesh", None)

            resp = c.post("/api/environment/export-scene", json={})
            assert resp.status_code == 404

    def test_unknown_format_returns_400(self, app):
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

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:env_mesh"] = mesh

            resp = c.post("/api/environment/export-scene", json={"format": "obj"})
            assert resp.status_code == 400
            assert "Unknown format" in resp.get_json()["error"]

            with _cache_lock:
                _cache.pop("test-session:env_mesh", None)


# ---------------------------------------------------------------------------
# POST /api/terrain/elevation
# ---------------------------------------------------------------------------


class TestTerrainElevation:
    def test_missing_lat_lon_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/terrain/elevation", json={})
            assert resp.status_code == 400
            assert "lat and lon" in resp.get_json()["error"]

    def test_flat_terrain_returns_binary(self, app):
        with app.test_client() as c:
            resp = c.post(
                "/api/terrain/elevation",
                json={"lat": 51.05, "lon": 3.72, "radius": 50},
            )
            assert resp.status_code == 200
            assert resp.content_type == "application/octet-stream"
            assert len(resp.data) > 0

            meta = json.loads(resp.headers["X-Meta"])
            assert meta["n_vertices"] > 0
            assert meta["n_triangles"] > 0
            assert meta["origin_lat"] == pytest.approx(51.05)
            assert meta["origin_lon"] == pytest.approx(3.72)

    def test_terrain_mesh_is_flat_at_zero(self, app):
        """Default (no elevation data) generates a flat grid at y=0."""
        with app.test_client() as c:
            resp = c.post(
                "/api/terrain/elevation",
                json={"lat": 0.0, "lon": 0.0, "radius": 20},
            )
            meta = json.loads(resp.headers["X-Meta"])
            n_verts = meta["n_vertices"]

            # Parse binary: first n_verts * 3 * 4 bytes are float32 vertices
            verts_bytes = resp.data[: n_verts * 3 * 4]
            verts = np.frombuffer(verts_bytes, dtype=np.float32).reshape(-1, 3)

            # Y coordinates (elevation in Three.js Y-up) should all be 0
            np.testing.assert_allclose(verts[:, 1], 0.0, atol=1e-6)

    def test_terrain_cached_after_request(self, app):
        from aegis.viewer.server import _cache

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            c.post("/api/terrain/elevation", json={"lat": 1.0, "lon": 2.0})

        cached = _cache.get("test-session:terrain_mesh")
        assert cached is not None
        assert "vertices" in cached
        assert "triangles" in cached
        assert "meta" in cached

    def test_non_numeric_lat_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/terrain/elevation", json={"lat": "abc", "lon": 3.72})
            assert resp.status_code == 400
            assert "must be numbers" in resp.get_json()["error"]

    def test_non_numeric_radius_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/terrain/elevation", json={"lat": 51.0, "lon": 3.7, "radius": "xyz"})
            assert resp.status_code == 400
            assert "must be numbers" in resp.get_json()["error"]

    def test_lat_out_of_range_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/terrain/elevation", json={"lat": 95.0, "lon": 3.72})
            assert resp.status_code == 400
            assert "lat" in resp.get_json()["error"]

    def test_radius_out_of_range_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/terrain/elevation", json={"lat": 51.0, "lon": 3.7, "radius": 10000})
            assert resp.status_code == 400
            assert "radius" in resp.get_json()["error"]
