"""Terrain elevation route: generates a flat/SRTM terrain mesh and returns binary."""

from __future__ import annotations

import json

from flask import Flask, Response, jsonify, request


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach terrain routes to *app*."""

    @app.route("/api/terrain/elevation", methods=["POST"])
    def api_terrain_elevation():
        """Generate a terrain mesh and return binary.

        For now this generates a flat grid at z=0 (SRTM download not yet
        implemented).  The grid is ``radius_m * 2`` square with 10 m cell
        spacing.

        Binary layout (same as environment meshes):
            float32 vertices (N*3) | uint32 triangles (M*3)

        Response header ``X-Meta`` carries JSON with ``n_vertices``,
        ``n_triangles``, ``width``, and ``height``.
        """
        import numpy as np

        from aegis.environment.terrain import TerrainGrid, generate_terrain_mesh

        body = request.get_json(silent=True) or {}
        lat = body.get("lat")
        lon = body.get("lon")
        radius = float(body.get("radius", 200))

        if lat is None or lon is None:
            return jsonify({"error": "lat and lon are required"}), 400

        cell_size = 10.0  # metres between grid points
        side = radius * 2.0
        n_cells = max(2, int(side / cell_size) + 1)

        elevations = np.zeros((n_cells, n_cells), dtype=np.float64)

        grid = TerrainGrid(
            elevations=elevations,
            origin_lat=float(lat),
            origin_lon=float(lon),
            cell_size_m=cell_size,
        )

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

        meta = {
            "n_vertices": len(verts_yup),
            "n_triangles": len(tris),
            "width": int(n_cells),
            "height": int(n_cells),
            "cell_size_m": cell_size,
            "origin_lat": float(lat),
            "origin_lon": float(lon),
        }

        with cache_lock:
            cache["terrain_mesh"] = {"vertices": verts_yup, "triangles": tris, "meta": meta}

        resp = Response(blob, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp
