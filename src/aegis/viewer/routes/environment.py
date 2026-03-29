"""Environment mesh routes: OSM, 3D Tiles, voxel-derived, combine, export."""

from __future__ import annotations

import json

from flask import Flask, Response, jsonify, request


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach environment routes to *app*."""

    @app.route("/api/environment/osm", methods=["POST"])
    def api_environment_osm():
        """Fetch OSM data, build mesh, cache it, return binary."""
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

        cfg_env = cache.get("config", {}).get("environment", {})
        osm_cfg = cfg_env.get("osm", {})
        default_building_height = body.get(
            "default_building_height",
            osm_cfg.get("default_building_height", 10),
        )
        detail = bool(body.get("detail", False))

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
            return jsonify({"error": "Overpass query timed out."}), 504
        except OverpassResponseTooLarge:
            return jsonify({"error": "Overpass response too large. Reduce the radius."}), 413

        binary, meta = mesh.to_binary()
        with cache_lock:
            cache["env_mesh_osm"] = mesh
            cache["env_mesh"] = mesh

        resp = Response(binary, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp

    @app.route("/api/environment/3dtiles", methods=["POST"])
    def api_environment_3dtiles():
        """Fetch Google Photorealistic 3D Tiles, build mesh, cache, return binary."""
        from aegis.environment.tiles import TileTraverser

        body = request.get_json(silent=True) or {}
        lat = body.get("lat")
        lon = body.get("lon")
        radius = body.get("radius", 200)
        if lat is None or lon is None:
            return jsonify({"error": "lat and lon are required"}), 400

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
        return resp

    @app.route("/api/environment/from-voxels", methods=["POST"])
    def api_environment_from_voxels():
        """Convert cached voxel data to an EnvironmentMesh and cache it."""
        import numpy as np

        from aegis.environment import EnvironmentMesh, MaterialType

        positions = cache.get("voxel_positions")
        materials = cache.get("voxel_materials")
        sizes = cache.get("voxel_sizes")

        if positions is None or len(positions) == 0:
            return jsonify({"error": "No voxel data in cache"}), 404

        # Build a simple box mesh per voxel using default size if needed
        body_data = request.get_json(silent=True) or {}
        lat = float(body_data.get("lat", 0.0))
        lon = float(body_data.get("lon", 0.0))

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

        all_v = np.zeros((total_verts, 3), dtype=np.float32)
        all_t = np.zeros((total_tris, 3), dtype=np.uint32)
        all_n = np.zeros((total_tris, 3), dtype=np.float32)
        all_m = np.zeros(total_tris, dtype=np.uint8)

        for i in range(n_vox):
            s = float(sizes[i]) if i < len(sizes) else 0.244
            v_off = i * n_vert
            t_off = i * n_face
            all_v[v_off : v_off + n_vert] = _cube_verts * s + positions[i]
            all_t[t_off : t_off + n_face] = _cube_faces + v_off
            all_n[t_off : t_off + n_face] = _face_normals
            mat_id = int(materials[i]) if materials is not None and i < len(materials) else MaterialType.UNKNOWN
            all_m[t_off : t_off + n_face] = mat_id

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
        return resp

    @app.route("/api/environment/combine", methods=["POST"])
    def api_environment_combine():
        """Combine cached meshes from multiple sources."""
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
        return resp

    @app.route("/api/environment/mesh", methods=["GET"])
    def api_environment_mesh():
        """Return the most recently cached environment mesh (any source)."""
        mesh = cache.get("env_mesh")
        if mesh is None:
            return jsonify({"error": "No environment mesh cached"}), 404

        binary, meta = mesh.to_binary()
        resp = Response(binary, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp

    @app.route("/api/environment/export-scene", methods=["POST"])
    def api_environment_export_scene():
        """Export the cached environment mesh to DiffeRT or Sionna format."""
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

    @app.route("/api/environment/materials", methods=["GET"])
    def api_environment_materials():
        """Return the material catalog with EM properties."""
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
