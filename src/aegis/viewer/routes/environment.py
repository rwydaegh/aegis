"""Environment mesh routes: OSM, 3D Tiles, voxel-derived, combine, export."""

from __future__ import annotations

import json

from flask import Flask, Response, jsonify, request

from aegis.viewer.cache import EnvironmentCache

_env_cache = EnvironmentCache()


def _handle_environment_osm(cache: dict, cache_lock) -> Response:
    """Implementation for POST /api/environment/osm."""
    from aegis.environment.osm import (
        OverpassRateLimitError,
        OverpassResponseTooLarge,
        OverpassTimeoutError,
        build_environment_from_osm,
        fetch_osm,
    )

    body = request.get_json(silent=True) or {}
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
    if radius <= 0 or radius > 5000:
        return jsonify({"error": "radius must be between 0 and 5000 meters"}), 400

    cfg_env = cache.get("config", {}).get("environment", {})
    osm_cfg = cfg_env.get("osm", {})
    # Frontend sends options nested under "options" key
    options = body.get("options", {})
    default_building_height = (
        options.get("default_building_height")
        or body.get("default_building_height")
        or osm_cfg.get("default_building_height", 10)
    )
    detail = bool(body.get("detail", False))

    cache_opts = {
        "default_building_height": float(default_building_height),
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

    binary, meta = mesh.to_binary()
    with cache_lock:
        cache["env_mesh_osm"] = mesh
        cache["env_mesh"] = mesh

    # Persist to file-based cache
    _env_cache.put_binary("osm", lat, lon, radius, cache_opts, binary, meta)

    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_3dtiles(cache: dict, cache_lock) -> Response:
    """Implementation for POST /api/environment/3dtiles."""
    from aegis.environment.tiles import TileTraverser

    body = request.get_json(silent=True) or {}
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
    if radius <= 0 or radius > 5000:
        return jsonify({"error": "radius must be between 0 and 5000 meters"}), 400

    api_key = body.get("api_key")
    if not api_key:
        import os

        api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return jsonify({"error": "Google API key required for 3D Tiles. Set GOOGLE_API_KEY or pass api_key."}), 400

    cfg_env = cache.get("config", {}).get("environment", {})
    tiles_cfg = cfg_env.get("tiles", {})
    geometric_error = body.get("geometric_error", tiles_cfg.get("geometric_error", 30.0))

    root_url = "https://tile.googleapis.com/v1/3dtiles/root.json"
    traverser = TileTraverser(
        root_url=root_url,
        api_key=api_key,
        geometric_error=float(geometric_error),
    )

    try:
        mesh = traverser.traverse(lat=lat, lon=lon, radius_m=radius)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    binary, meta = mesh.to_binary()
    with cache_lock:
        cache["env_mesh_tiles"] = mesh
        cache["env_mesh"] = mesh

    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_from_voxels(cache: dict, cache_lock) -> Response:
    """Implementation for POST /api/environment/from-voxels."""
    import numpy as np

    from aegis.environment import EnvironmentMesh, MaterialType

    positions = cache.get("voxel_positions")
    materials = cache.get("voxel_materials")
    sizes = cache.get("voxel_sizes")

    if positions is None or len(positions) == 0:
        return jsonify({"error": "No voxel data in cache"}), 404

    body_data = request.get_json(silent=True) or {}
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
        cache["env_mesh_voxels"] = mesh
        cache["env_mesh"] = mesh

    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_combine(cache: dict, cache_lock) -> Response:
    """Implementation for POST /api/environment/combine."""
    from aegis.environment import EnvironmentMesh

    body = request.get_json(silent=True) or {}
    sources = body.get("sources", ["osm", "tiles", "voxels"])

    source_map = {
        "osm": "env_mesh_osm",
        "tiles": "env_mesh_tiles",
        "voxels": "env_mesh_voxels",
    }

    meshes = []
    for src in sources:
        key = source_map.get(src)
        if key and cache.get(key) is not None:
            meshes.append(cache[key])

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
        cache["env_mesh"] = mesh

    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_mesh(cache: dict) -> Response:
    """Implementation for GET /api/environment/mesh."""
    mesh = cache.get("env_mesh")
    if mesh is None:
        return jsonify({"error": "No environment mesh cached"}), 404

    binary, meta = mesh.to_binary()
    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_export_scene(cache: dict) -> Response:
    """Implementation for POST /api/environment/export-scene."""
    import tempfile
    from pathlib import Path

    mesh = cache.get("env_mesh")
    if mesh is None:
        return jsonify({"error": "No environment mesh cached"}), 404

    body = request.get_json(silent=True) or {}
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


def _handle_environment_geojson(cache: dict, cache_lock) -> Response:
    """Implementation for POST /api/environment/geojson."""
    from aegis.environment.geojson import build_environment_from_geojson

    body = request.get_json(silent=True) or {}
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
        cache["env_mesh_osm"] = mesh
        cache["env_mesh"] = mesh

    resp = Response(binary, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_environment_materials() -> Response:
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


def _handle_environment_coverage(cache: dict, cache_lock) -> Response:
    """Implementation for POST /api/environment/coverage."""
    import os
    from io import BytesIO

    api_key = os.environ.get("CLOUDRF_API_KEY")
    if not api_key:
        return jsonify({"error": "CLOUDRF_API_KEY not configured"}), 501

    body = request.get_json(silent=True) or {}
    stations = body.get("stations", [])
    if not stations:
        return jsonify({"error": "stations list is required and must not be empty"}), 400

    station = stations[0]
    radius_km = float(body.get("radius_km", 1.0))
    resolution_m = int(body.get("resolution_m", 10))
    propagation_model = int(body.get("propagation_model", 1))

    try:
        from aegis.integration.cloudrf import CloudRFClient

        tiff_bytes = CloudRFClient(api_key).area(
            lat=float(station["lat"]),
            lon=float(station["lon"]),
            alt=float(station.get("alt", 10)),
            freq_mhz=float(station["freq_mhz"]),
            power_w=float(station.get("power_w", 2.0)),
            gain_dbi=float(station.get("gain_dbi", 0)),
            azimuth=float(station.get("azimuth", 0)),
            tilt=float(station.get("tilt", 0)),
            hbw=float(station.get("hbw", 65)),
            vbw=float(station.get("vbw", 10)),
            radius_km=radius_km,
            res_m=resolution_m,
            propagation_model=propagation_model,
        )
    except Exception as exc:
        return jsonify({"error": f"CloudRF API error: {exc}"}), 502

    try:
        from PIL import Image

        img = Image.open(BytesIO(tiff_bytes))
        buf = BytesIO()
        img.save(buf, "PNG")
        png_bytes = buf.getvalue()
    except Exception as exc:
        return jsonify({"error": f"Image conversion error: {exc}"}), 500

    resp = Response(png_bytes, mimetype="image/png")
    resp.headers["X-Bounds"] = json.dumps({"note": "bounds extraction from GeoTIFF requires rasterio, deferred to V2"})
    resp.headers["Access-Control-Expose-Headers"] = "X-Bounds"
    return resp


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

    @app.route("/api/environment/coverage", methods=["POST"])
    def api_environment_coverage():
        """Call CloudRF to generate a coverage heatmap, return PNG."""
        return _handle_environment_coverage(cache, cache_lock)

    @app.route("/api/cache/environments", methods=["DELETE"])
    def api_clear_environment_cache():
        """Clear the file-based environment cache."""
        _env_cache.clear()
        return jsonify({"ok": True})
