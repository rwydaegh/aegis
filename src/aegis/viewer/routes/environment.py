"""Environment mesh routes: OSM, 3D Tiles, voxel-derived, combine, export."""

from __future__ import annotations

import json
import logging

from flask import Flask, Response, jsonify

from aegis.viewer.cache import EnvironmentCache
from aegis.viewer.routes._helpers import get_json_dict
from aegis.viewer.routes._types import RouteResponse
from aegis.viewer.server import scoped_cache_get, scoped_cache_set

logger = logging.getLogger(__name__)

_env_cache = EnvironmentCache()


def _handle_environment_osm(cache: dict, cache_lock) -> RouteResponse:
    """Implementation for POST /api/environment/osm."""
    import xml.etree.ElementTree as ET

    from aegis.environment.osm import (
        OverpassHTTPError,
        OverpassRateLimitError,
        OverpassResponseTooLarge,
        OverpassTimeoutError,
        build_environment_from_osm,
        fetch_osm,
    )

    body, err = get_json_dict()
    if err is not None:
        return err
    lat = body.get("lat")
    lon = body.get("lon")
    radius = body.get("radius", 200)
    if lat is None or lon is None:
        return jsonify({"error": "lat and lon are required"}), 400
    try:
        lat, lon, radius = float(lat), float(lon), float(radius)
    except (TypeError, ValueError):
        return jsonify({"error": "lat, lon, and radius must be numbers"}), 400
    if not (-90 <= lat <= 90):
        return jsonify({"error": "lat must be between -90 and 90"}), 400
    if not (-180 <= lon <= 180):
        return jsonify({"error": "lon must be between -180 and 180"}), 400
    max_radius = cache.get("config", {}).get("location", {}).get("osm_radius_max_m", 5000)
    if radius <= 0 or radius > max_radius:
        return jsonify({"error": f"radius must be between 0 and {int(max_radius)} meters"}), 400

    cfg_env = cache.get("config", {}).get("environment", {})
    osm_cfg = cfg_env.get("osm", {})
    # Frontend sends options nested under "options" key
    options = body.get("options", {})
    if not isinstance(options, dict):
        return jsonify({"error": "options must be an object"}), 400
    default_building_height = (
        options.get("default_building_height")
        or body.get("default_building_height")
        or osm_cfg.get("default_building_height", 10)
    )
    detail = bool(body.get("detail", False))

    default_building_height = max(0.1, min(float(default_building_height), 500.0))

    cache_opts = {
        "default_building_height": default_building_height,
        "detail": detail,
    }

    # Check the file-based cache first
    cached = _env_cache.get_binary("osm", lat, lon, radius, cache_opts)
    if cached is not None:
        binary, meta = cached
        resp = Response(binary, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
        return resp

    try:
        xml_str = fetch_osm(lat, lon, radius_m=radius)
        mesh = build_environment_from_osm(
            xml_str,
            origin_lat=lat,
            origin_lon=lon,
            default_building_height=float(default_building_height),
            detail=detail,
        )
    except OverpassRateLimitError:
        resp = jsonify({"error": "Overpass rate limit exceeded. Try again later."})
        resp.status_code = 503
        resp.headers["Retry-After"] = "60"
        return resp
    except OverpassTimeoutError:
        return (
            jsonify({"error": "Overpass query timed out. Try a smaller radius or try again later."}),
            504,
        )
    except OverpassResponseTooLarge:
        return jsonify({"error": "Overpass response too large. Reduce the radius."}), 413
    except OverpassHTTPError as exc:
        logger.warning("Overpass mirrors returned unexpected HTTP status: %s", exc)
        return (
            jsonify({"error": "Overpass API returned an unexpected error. Try again later."}),
            502,
        )
    except ET.ParseError as exc:
        logger.warning("Overpass returned malformed XML: %s", exc)
        return (
            jsonify({"error": "Overpass returned malformed XML. Try again later."}),
            502,
        )

    binary, meta = mesh.to_binary()
    with cache_lock:
        scoped_cache_set(cache, "env_mesh_osm", mesh)
        scoped_cache_set(cache, "env_mesh", mesh)

    # Persist to file-based cache
    _env_cache.put_binary("osm", lat, lon, radius, cache_opts, binary, meta)

    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_3dtiles(cache: dict, cache_lock) -> RouteResponse:
    """Implementation for POST /api/environment/3dtiles."""
    from aegis.environment.tiles import TileTraverser

    body, err = get_json_dict()
    if err is not None:
        return err
    lat = body.get("lat")
    lon = body.get("lon")
    radius = body.get("radius", 200)
    if lat is None or lon is None:
        return jsonify({"error": "lat and lon are required"}), 400
    try:
        lat, lon, radius = float(lat), float(lon), float(radius)
    except (TypeError, ValueError):
        return jsonify({"error": "lat, lon, and radius must be numbers"}), 400
    if not (-90 <= lat <= 90):
        return jsonify({"error": "lat must be between -90 and 90"}), 400
    if not (-180 <= lon <= 180):
        return jsonify({"error": "lon must be between -180 and 180"}), 400
    max_radius = cache.get("config", {}).get("location", {}).get("osm_radius_max_m", 5000)
    if radius <= 0 or radius > max_radius:
        return jsonify({"error": f"radius must be between 0 and {int(max_radius)} meters"}), 400

    api_key = body.get("api_key")
    if not api_key:
        import os

        api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return jsonify({"error": "Google API key required for 3D Tiles. Set GOOGLE_API_KEY or pass api_key."}), 400

    cfg_env = cache.get("config", {}).get("environment", {})
    tiles_cfg = cfg_env.get("tiles", {})
    geometric_error = float(body.get("geometric_error", tiles_cfg.get("geometric_error", 30.0)))
    geometric_error = max(0.1, min(geometric_error, 1000.0))

    root_url = "https://tile.googleapis.com/v1/3dtiles/root.json"
    traverser = TileTraverser(
        root_url=root_url,
        api_key=api_key,
        geometric_error=geometric_error,
    )

    try:
        mesh = traverser.traverse(lat=lat, lon=lon, radius_m=radius)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    if mesh.triangles.shape[0] == 0:
        return (
            jsonify(
                {
                    "error": (
                        "No 3D Tiles cover this region. Google's photorealistic "
                        "tiles are only available for major cities. Try a different "
                        "location or switch the source to OSM."
                    )
                }
            ),
            404,
        )

    binary, meta = mesh.to_binary()
    with cache_lock:
        scoped_cache_set(cache, "env_mesh_tiles", mesh)
        scoped_cache_set(cache, "env_mesh", mesh)

    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_from_voxels(cache: dict, cache_lock) -> RouteResponse:
    """Implementation for POST /api/environment/from-voxels."""
    import numpy as np

    from aegis.environment import EnvironmentMesh, MaterialType

    positions = cache.get("voxel_positions")
    materials = cache.get("voxel_materials")
    sizes = cache.get("voxel_sizes")

    if positions is None or len(positions) == 0:
        return jsonify({"error": "No voxel data in cache"}), 404

    body_data, err = get_json_dict()
    if err is not None:
        return err
    try:
        lat = float(body_data.get("lat", 0.0))
        lon = float(body_data.get("lon", 0.0))
    except (TypeError, ValueError):
        return jsonify({"error": "lat and lon must be numbers"}), 400

    if sizes is None or len(sizes) == 0:
        cfg_vox = cache.get("config", {}).get("voxels", {})
        default_size = float(cfg_vox.get("default_size_fallback", 0.244))
        sizes = np.full(len(positions), default_size, dtype=np.float32)

    # Generate a cube mesh for every voxel: 8 vertices, 12 triangles per cube
    # Unit cube face definitions (6 faces, 2 triangles each)
    # Vertices: corners of [-0.5, 0.5]^3
    _cube_verts = (
        np.array(
            [
                [-1, -1, -1],
                [1, -1, -1],
                [1, 1, -1],
                [-1, 1, -1],
                [-1, -1, 1],
                [1, -1, 1],
                [1, 1, 1],
                [-1, 1, 1],
            ],
            dtype=np.float32,
        )
        * 0.5
    )

    _cube_faces = np.array(
        [
            [0, 2, 1],
            [0, 3, 2],  # -Z
            [4, 5, 6],
            [4, 6, 7],  # +Z
            [0, 1, 5],
            [0, 5, 4],  # -Y
            [3, 6, 2],
            [3, 7, 6],  # +Y
            [0, 4, 7],
            [0, 7, 3],  # -X
            [1, 2, 6],
            [1, 6, 5],  # +X
        ],
        dtype=np.uint32,
    )

    _face_normals = np.array(
        [
            [0, 0, -1],
            [0, 0, -1],
            [0, 0, 1],
            [0, 0, 1],
            [0, -1, 0],
            [0, -1, 0],
            [0, 1, 0],
            [0, 1, 0],
            [-1, 0, 0],
            [-1, 0, 0],
            [1, 0, 0],
            [1, 0, 0],
        ],
        dtype=np.float32,
    )

    n_vox = len(positions)
    n_face = len(_cube_faces)
    n_vert = len(_cube_verts)
    total_verts = n_vox * n_vert
    total_tris = n_vox * n_face

    positions = np.asarray(positions, dtype=np.float32)
    sizes = np.asarray(sizes, dtype=np.float32)

    # Vectorized vertex construction: scale cube template per voxel and translate
    # all_v shape: (n_vox, n_vert, 3)
    all_v = (_cube_verts[np.newaxis, :, :] * sizes[:, np.newaxis, np.newaxis] + positions[:, np.newaxis, :]).reshape(
        total_verts, 3
    )

    # Vectorized triangle indices: offset cube faces per voxel
    v_offsets = (np.arange(n_vox) * n_vert).astype(np.uint32)
    all_t = (_cube_faces[np.newaxis, :, :] + v_offsets[:, np.newaxis, np.newaxis]).reshape(total_tris, 3)

    # Tile normals for all voxels
    all_n = np.tile(_face_normals, (n_vox, 1))

    # Vectorized material assignment
    if materials is not None:
        mat_ids = np.asarray(materials[:n_vox], dtype=np.uint8)
    else:
        mat_ids = np.full(n_vox, MaterialType.UNKNOWN, dtype=np.uint8)
    all_m = np.repeat(mat_ids, n_face)

    mesh = EnvironmentMesh(
        vertices=all_v,
        triangles=all_t,
        normals=all_n,
        materials=all_m,
        origin_lat=lat,
        origin_lon=lon,
        source="voxels",
    )

    binary, meta = mesh.to_binary()
    with cache_lock:
        scoped_cache_set(cache, "env_mesh_voxels", mesh)
        scoped_cache_set(cache, "env_mesh", mesh)

    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_combine(cache: dict, cache_lock) -> RouteResponse:
    """Implementation for POST /api/environment/combine."""
    from aegis.environment import EnvironmentMesh

    body, err = get_json_dict()
    if err is not None:
        return err
    sources = body.get("sources", ["osm", "tiles", "voxels"])
    if not isinstance(sources, list):
        return jsonify({"error": "sources must be a list of strings"}), 400

    source_map = {
        "osm": "env_mesh_osm",
        "tiles": "env_mesh_tiles",
        "voxels": "env_mesh_voxels",
    }

    meshes = []
    for src in sources:
        if not isinstance(src, str):
            continue
        key = source_map.get(src)
        if key:
            m = scoped_cache_get(cache, key)
            if m is not None:
                meshes.append(m)

    if not meshes:
        return jsonify({"error": "No cached environment meshes to combine"}), 404

    if len(meshes) == 1:
        mesh = meshes[0]
    else:
        try:
            mesh = EnvironmentMesh.combine(*meshes)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    binary, meta = mesh.to_binary()
    with cache_lock:
        scoped_cache_set(cache, "env_mesh", mesh)

    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_mesh(cache: dict) -> RouteResponse:
    """Implementation for GET /api/environment/mesh."""
    mesh = scoped_cache_get(cache, "env_mesh")
    if mesh is None:
        return jsonify({"error": "No environment mesh cached"}), 404

    binary, meta = mesh.to_binary()
    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_export_scene(cache: dict) -> RouteResponse:
    """Implementation for POST /api/environment/export-scene."""
    import tempfile
    from pathlib import Path

    mesh = scoped_cache_get(cache, "env_mesh")
    if mesh is None:
        return jsonify({"error": "No environment mesh cached"}), 404

    body, err = get_json_dict()
    if err is not None:
        return err
    fmt = body.get("format", "differt")

    if fmt == "differt":
        try:
            mesh.to_differt_scene()
            return jsonify({"ok": True, "format": "differt", "n_triangles": len(mesh.triangles)})
        except ImportError as exc:
            return jsonify({"error": f"DiffeRT not installed: {exc}"}), 400
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    if fmt == "sionna":
        try:
            with tempfile.TemporaryDirectory() as td:
                out_path = mesh.to_sionna_xml(Path(td) / "scene.xml")
                xml_bytes = out_path.read_bytes()
            return Response(xml_bytes, mimetype="application/xml")
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    return jsonify({"error": f"Unknown format '{fmt}'. Use 'differt' or 'sionna'."}), 400


def _handle_environment_geojson(cache: dict, cache_lock) -> RouteResponse:
    """Implementation for POST /api/environment/geojson."""
    from aegis.environment.geojson import build_environment_from_geojson

    body, err = get_json_dict()
    if err is not None:
        return err
    geojson_str = body.get("geojson", "")
    if not geojson_str:
        return jsonify({"error": "geojson field is required"}), 400

    try:
        lat = float(body.get("lat", 0))
        lon = float(body.get("lon", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "lat and lon must be numbers"}), 400

    try:
        mesh = build_environment_from_geojson(geojson_str, lat, lon)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    binary, meta = mesh.to_binary()
    with cache_lock:
        scoped_cache_set(cache, "env_mesh_osm", mesh)
        scoped_cache_set(cache, "env_mesh", mesh)

    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_materials() -> RouteResponse:
    """Implementation for GET /api/environment/materials."""
    from aegis.environment import MATERIAL_EM_PROPERTIES, MaterialType

    catalog = []
    for mat in MaterialType:
        props = MATERIAL_EM_PROPERTIES.get(mat, {})
        catalog.append(
            {
                "id": int(mat),
                "name": mat.name.lower(),
                "eps_r": props.get("eps_r"),
                "sigma": props.get("sigma"),
            }
        )
    return jsonify({"materials": catalog})


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach environment routes to *app*."""

    @app.route("/api/environment/osm", methods=["POST"])
    def api_environment_osm():
        """Fetch OSM data, build mesh, cache it, return binary."""
        return _handle_environment_osm(cache, cache_lock)

    @app.route("/api/environment/3dtiles", methods=["POST"])
    def api_environment_3dtiles():
        """Fetch Google Photorealistic 3D Tiles, build mesh, cache, return binary."""
        return _handle_environment_3dtiles(cache, cache_lock)

    @app.route("/api/environment/from-voxels", methods=["POST"])
    def api_environment_from_voxels():
        """Convert cached voxel data to an EnvironmentMesh and cache it."""
        return _handle_environment_from_voxels(cache, cache_lock)

    @app.route("/api/environment/combine", methods=["POST"])
    def api_environment_combine():
        """Combine cached meshes from multiple sources."""
        return _handle_environment_combine(cache, cache_lock)

    @app.route("/api/environment/mesh", methods=["GET"])
    def api_environment_mesh():
        """Return the most recently cached environment mesh (any source)."""
        return _handle_environment_mesh(cache)

    @app.route("/api/environment/export-scene", methods=["POST"])
    def api_environment_export_scene():
        """Export the cached environment mesh to DiffeRT or Sionna format."""
        return _handle_environment_export_scene(cache)

    @app.route("/api/environment/geojson", methods=["POST"])
    def api_environment_geojson():
        """Parse a GeoJSON string, build mesh, cache it, return binary."""
        return _handle_environment_geojson(cache, cache_lock)

    @app.route("/api/environment/materials", methods=["GET"])
    def api_environment_materials():
        """Return the material catalog with EM properties."""
        return _handle_environment_materials()

    @app.route("/api/cache/environments", methods=["DELETE"])
    def api_clear_environment_cache():
        """Clear the file-based environment cache."""
        _env_cache.clear()
        return jsonify({"ok": True})
