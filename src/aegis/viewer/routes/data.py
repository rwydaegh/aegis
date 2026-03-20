"""Data-serving routes: body mesh, voxels, tiles, config, and static pages."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from flask import Flask, Response, jsonify, render_template


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach data-serving routes to *app*."""

    @app.route("/")
    def index():
        return render_template("index.html", viewer_config=json.dumps(cache["config"]))

    @app.route("/api/viewer-config")
    def api_viewer_config():
        """Return the full viewer configuration."""
        return jsonify(cache["config"])

    @app.route("/api/body")
    def api_body():
        """Return body mesh as binary (positions + normals, float32)."""
        if cache.get("body") is None:
            return jsonify({"error": "No body mesh loaded"}), 404

        data = cache["body_binary"]
        meta = cache["body_meta"]

        resp = Response(data, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp

    @app.route("/api/voxels")
    def api_voxels():
        """Return voxel data as binary (positions float32 + colors uint8 + materials uint8)."""
        if cache.get("voxel_binary") is None:
            return jsonify({"error": "No voxel data loaded"}), 404

        data = cache["voxel_binary"]
        meta = cache["voxel_meta"]

        resp = Response(data, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp

    @app.route("/api/tiles")
    def api_tiles_list():
        """Return list of available GLB tile files and the ECEF->local transform."""
        td = cache.get("tiles_dir")
        if td is None:
            return jsonify({"tiles": [], "transform": None})

        tile_names = sorted(p.name for p in Path(td).glob("*.glb"))

        # Compose Python Z-up transform with Z-up -> Y-up swap for Three.js
        transform = cache.get("voxel_transform")
        if transform is not None:
            z_to_y = np.array(
                [[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]],
                dtype=np.float64,
            )
            combined = z_to_y @ transform
            # Three.js Matrix4.fromArray expects column-major order
            transform_list = combined.T.flatten().tolist()
        else:
            transform_list = None

        return jsonify({"tiles": tile_names, "transform": transform_list})

    @app.route("/api/tiles/<path:filename>")
    def api_tiles_file(filename: str):
        """Serve an individual GLB tile file."""
        from flask import send_from_directory

        td = cache.get("tiles_dir")
        if td is None:
            return jsonify({"error": "No tiles directory"}), 404
        return send_from_directory(str(td), filename)

    @app.route("/api/config")
    def api_config():
        """Return available configuration options."""
        from aegis.viewer.compute import TISSUE_PRESETS

        bodies = []
        data_dir = cache.get("data_dir")
        if data_dir:
            data_path = Path(data_dir)
            if data_path.exists():
                bodies = [p.stem for p in data_path.glob("*.stl")]

        # Check for DiffeRT and available scenes
        has_differt = False
        scenes = []
        try:
            from aegis.viewer.raytracer import list_available_scenes

            has_differt = True
            scenes = list_available_scenes()
        except ImportError:
            pass

        # Check location loader availability
        from aegis.viewer.pipeline import find_pipeline

        has_pipeline = find_pipeline() is not None
        has_api_key = bool(os.environ.get("GOOGLE_API_KEY"))

        cfg = cache["config"]
        levels = [lv["value"] for lv in cfg["dosimetry"]["fidelity_levels"]]

        has_voxels = cache.get("voxel_binary") is not None
        tiles_dir = cache.get("tiles_dir")
        n_tiles = 0
        if tiles_dir:
            n_tiles = len(list(Path(tiles_dir).glob("*.glb")))
        return jsonify(
            {
                "bodies": bodies,
                "tissues": sorted(TISSUE_PRESETS.keys()),
                "levels": levels,
                "has_voxels": has_voxels,
                "has_differt": has_differt,
                "voxel_rt_available": has_voxels and has_differt,
                "has_tiles": n_tiles > 0,
                "n_tiles": n_tiles,
                "scenes": scenes,
                "body_meta": cache.get("body_meta"),
                "voxel_meta": cache.get("voxel_meta"),
                "has_location_loader": has_pipeline and has_api_key,
                "has_api_key": has_api_key,
                "body_placement": cache.get("body_placement"),
            }
        )
