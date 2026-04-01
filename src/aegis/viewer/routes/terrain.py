"""Terrain elevation route: generates a flat/SRTM terrain mesh and returns binary."""

from __future__ import annotations

import json

from flask import Flask, Response, jsonify, request


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach terrain routes to *app*."""

    @app.route("/api/terrain/elevation", methods=["POST"])
    def api_terrain_elevation():
        """Generate a terrain mesh from SRTM elevation data and return binary.

        Downloads SRTM1 tiles from AWS open data on first access (cached
        locally). Falls back to flat terrain for ocean/polar areas.

        Binary layout (same as environment meshes):
            float32 vertices (N*3) | uint32 triangles (M*3)

        Response header ``X-Meta`` carries JSON with ``n_vertices``,
        ``n_triangles``, ``width``, ``height``, and ``has_elevation``.
        """
        import numpy as np

        from aegis.environment.terrain import generate_terrain_mesh, terrain_grid_for_location

        body = request.get_json(silent=True) or {}
        lat = body.get("lat")
        lon = body.get("lon")
        if lat is None or lon is None:
            return jsonify({"error": "lat and lon are required"}), 400
        try:
            lat = float(lat)
            lon = float(lon)
            radius = float(body.get("radius", 200))
        except (TypeError, ValueError):
            return jsonify({"error": "lat, lon, and radius must be numbers"}), 400
        if not (-90 <= lat <= 90):
            return jsonify({"error": "lat must be between -90 and 90"}), 400
        if not (-180 <= lon <= 180):
            return jsonify({"error": "lon must be between -180 and 180"}), 400
        if radius <= 0 or radius > 5000:
            return jsonify({"error": "radius must be between 0 and 5000 meters"}), 400

        cell_size = 10.0  # metres between grid points

        grid = terrain_grid_for_location(
            lat=lat,
            lon=lon,
            radius_m=radius,
            cell_size_m=cell_size,
        )

        n_cells = grid.elevations.shape[0]
        vertices, triangles = generate_terrain_mesh(grid)

        # Centre the mesh on (0, 0) in the XZ plane (Three.js Y-up).
        # generate_terrain_mesh returns X = col*cell, Y = row*cell, Z = elevation.
        # We map to Three.js coords: TX = X - half, TY = Z (elevation), TZ = -(Y - half).
        half = (n_cells - 1) * cell_size / 2.0
        vx = vertices[:, 0] - half
        vy = vertices[:, 2]  # elevation -> Y
        vz = -(vertices[:, 1] - half)

        verts_yup = np.column_stack([vx, vy, vz]).astype(np.float32)
        tris = triangles.astype(np.uint32)

        blob = verts_yup.tobytes() + tris.tobytes()

        elev_range = float(vy.max() - vy.min())
        meta = {
            "n_vertices": len(verts_yup),
            "n_triangles": len(tris),
            "width": int(n_cells),
            "height": int(n_cells),
            "cell_size_m": cell_size,
            "origin_lat": float(lat),
            "origin_lon": float(lon),
            "has_elevation": elev_range > 0.1,
            "elevation_range_m": round(elev_range, 1),
        }

        with cache_lock:
            cache["terrain_mesh"] = {"vertices": verts_yup, "triangles": tris, "meta": meta}

        resp = Response(blob, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
        return resp
