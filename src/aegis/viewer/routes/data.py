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
        # Serve React build if available (primary frontend)
        static_dir = Path(__file__).parent.parent / "static"
        if (static_dir / "index.html").exists():
            from flask import send_from_directory

            return send_from_directory(str(static_dir), "index.html")
        # Fall back to legacy Jinja2 template (deprecated)
        import warnings

        warnings.warn(
            "Serving legacy HTML viewer. Build the React frontend: cd aegis-web && npm run build",
            DeprecationWarning,
            stacklevel=1,
        )
        return render_template("_legacy_index.html", viewer_config=json.dumps(cache["config"]))

    @app.route("/assets/<path:filename>")
    def static_assets(filename):
        from flask import send_from_directory

        static_dir = Path(__file__).parent.parent / "static" / "assets"
        return send_from_directory(str(static_dir), filename)

    @app.route("/<path:filename>")
    def static_root_files(filename):
        """Serve root-level static files (fonts, favicons) from static/."""
        from flask import abort, send_from_directory

        static_dir = Path(__file__).parent.parent / "static"
        # Only serve files that actually exist to avoid masking API routes
        if (static_dir / filename).is_file():
            return send_from_directory(str(static_dir), filename)
        return abort(404)

    @app.route("/api/viewer-config")
    def api_viewer_config():
        """Return the full viewer configuration."""
        return jsonify(cache["config"])

    @app.route("/api/body")
    def api_body():
        """Return body mesh as binary (positions + normals, float32).

        Accepts optional ?name= query parameter to select a specific body.
        Defaults to the default body loaded at startup.
        """
        name = request.args.get("name", cache.get("default_body"))
        bodies = cache.get("bodies", {})
        entry = bodies.get(name)
        if entry is None:
            # Fall back to legacy single-body cache for backward compat
            if name == cache.get("default_body") and cache.get("body_binary") is not None:
                data = cache["body_binary"]
                meta = cache["body_meta"]
                resp = Response(data, mimetype="application/octet-stream")
                resp.headers["X-Meta"] = json.dumps(meta)
                return resp
            return jsonify({"error": f"Body '{name}' not found"}), 404

        resp = Response(entry["binary"], mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(entry["meta"])
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

    @app.route("/api/clear-cache", methods=["POST"])
    def api_clear_cache():
        """Clear all cached voxel, scene, and MIMO data."""
        with cache_lock:
            for key in (
                "voxel_positions",
                "voxel_materials",
                "voxel_sizes",
                "voxel_binary",
                "voxel_meta",
                "body_placement",
                "tiles_dir",
                "voxel_json_path",
                "mimo_scene",
                "mimo_summary",
                "mimo_results_binary",
                "mimo_results_stats",
            ):
                cache.pop(key, None)
        try:
            from aegis.viewer.raytracer import _scene_cache, clear_voxel_scene_cache

            clear_voxel_scene_cache()
            _scene_cache.clear()
        except ImportError:
            pass
        app.config.pop("_last_compliance_result", None)
        return jsonify({"ok": True})

    @app.route("/api/config")
    def api_config():
        """Return available configuration options."""
        from aegis.viewer.compute import SKIN_MODELS

        # Read bodies from the preloaded cache (populated at startup)
        bodies_cache = cache.get("bodies", {})
        if bodies_cache:
            bodies = list(bodies_cache.keys())
        else:
            # Fallback: discover from data_dir if bodies cache is empty
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

        # Sionna RT runs on Modal GPU, not locally. Check if Modal proxy is
        # configured (env vars present) OR if sionna is installed locally.
        has_sionna = False
        try:
            from aegis.viewer.modal_proxy import _is_enabled as _modal_enabled

            has_sionna = _modal_enabled()
        except Exception:
            pass
        if not has_sionna:
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
        # Report default body name and its meta from preloaded bodies cache
        default_body_name = cache.get("default_body", "")
        bodies_cache = cache.get("bodies", {})
        default_entry = bodies_cache.get(default_body_name)
        body_meta = default_entry["meta"] if default_entry is not None else cache.get("body_meta")
        bodies.sort()

        return jsonify(
            {
                "bodies": bodies,
                "body_name": default_body_name,
                "skin_models": SKIN_MODELS,
                "levels": levels,
                "has_voxels": has_voxels,
                "has_differt": has_differt,
                "has_sionna": has_sionna,
                "voxel_rt_available": has_voxels and has_differt,
                "has_tiles": n_tiles > 0,
                "n_tiles": n_tiles,
                "scenes": scenes,
                "body_meta": body_meta,
                "voxel_meta": cache.get("voxel_meta"),
                "has_location_loader": has_pipeline and has_api_key,
                "has_api_key": has_api_key,
                "body_placement": cache.get("body_placement"),
            }
        )
