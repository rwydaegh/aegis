"""Data-serving routes: body mesh, voxels, tiles, config, and static pages."""

from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach data-serving routes to *app*."""

    @app.route("/")
    def index():
        static_dir = Path(__file__).parent.parent / "static"
        if (static_dir / "index.html").exists():
            from flask import send_from_directory

            return send_from_directory(str(static_dir), "index.html")
        return render_template("index.html", viewer_config=json.dumps(cache["config"]))

    @app.route("/assets/<path:filename>")
    def static_assets(filename):
        from flask import send_from_directory

        static_dir = Path(__file__).parent.parent / "static" / "assets"
        return send_from_directory(str(static_dir), filename)

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
        """Return list of available GLB tile files."""
        td = cache.get("tiles_dir")
        if td is None:
            return jsonify({"tiles": [], "transform": None})

        tile_names = sorted(p.name for p in Path(td).glob("*.glb"))
        return jsonify({"tiles": tile_names, "transform": None})

    @app.route("/api/tiles/<path:filename>")
    def api_tiles_file(filename: str):
        """Serve an individual GLB tile file."""
        from flask import send_from_directory

        td = cache.get("tiles_dir")
        if td is None:
            return jsonify({"error": "No tiles directory"}), 404
        return send_from_directory(str(td), filename)

    @app.route("/api/body/switch", methods=["POST"])
    def api_body_switch():
        """Switch the active body mesh at runtime."""
        from aegis.viewer.scene_data import body_to_binary, load_body

        body_name = request.json.get("name") if request.is_json else None
        if not body_name:
            return jsonify({"error": "Missing 'name' in request body"}), 400

        data_dir = cache.get("data_dir")
        if not data_dir:
            return jsonify({"error": "No data directory configured"}), 500

        try:
            body = load_body(body_name, data_dir)
        except FileNotFoundError:
            return jsonify({"error": f"Body mesh '{body_name}' not found"}), 404

        with cache_lock:
            cache["body"] = body
            cache["body_binary"], cache["body_meta"] = body_to_binary(body)

        return jsonify({"ok": True, "meta": cache["body_meta"]})

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

        # Check for Sionna RT without importing it (avoids TF/NumPy crashes).
        # Just check if the top-level 'sionna' package directory exists on disk.
        has_sionna = False
        try:
            import importlib.util

            has_sionna = importlib.util.find_spec("sionna") is not None
        except Exception:
            pass

        # Check location loader availability
        from aegis.viewer.pipeline import find_pipeline

        has_pipeline = find_pipeline(cache.get("pipeline_dir")) is not None
        has_api_key = bool(os.environ.get("GOOGLE_API_KEY"))

        cfg = cache["config"]
        levels = [lv["value"] for lv in cfg["dosimetry"]["fidelity_levels"]]

        has_voxels = cache.get("voxel_binary") is not None
        tiles_dir = cache.get("tiles_dir")
        n_tiles = 0
        if tiles_dir:
            n_tiles = len(list(Path(tiles_dir).glob("*.glb")))
        # Report which body is currently loaded and sort body list
        current_body = cache["body"].name if cache.get("body") else ""
        bodies.sort()

        return jsonify(
            {
                "bodies": bodies,
                "body_name": current_body,
                "tissues": sorted(TISSUE_PRESETS.keys()),
                "levels": levels,
                "has_voxels": has_voxels,
                "has_differt": has_differt,
                "has_sionna": has_sionna,
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
