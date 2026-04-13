"""Data-serving routes: body mesh, voxels, tiles, config, and static pages."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_file

from aegis.viewer.server import scoped_cache_get


def _handle_index(cache):
    """Implementation for /."""
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


def _handle_export_config(cache, cache_lock):
    """Implementation for /api/export-config."""
    with cache_lock:
        base = copy.deepcopy(cache["config"])
    interactive = request.get_json(silent=True) or {}

    # Map interactive state (camelCase) to config paths
    if "freqGhz" in interactive:
        base["dosimetry"]["freq_hz"] = interactive["freqGhz"] * 1e9
    if "powerDbm" in interactive:
        base["dosimetry"]["default_power_dbm"] = interactive["powerDbm"]
    if "bodyName" in interactive:
        base["body"]["default_name"] = interactive["bodyName"]
    if "antennaPos" in interactive and interactive["antennaPos"]:
        base["antenna"]["default_position"] = interactive["antennaPos"]
    if "skinModel" in interactive:
        base["dosimetry"]["skin_model"] = interactive["skinModel"]
    if "bodyOffset" in interactive:
        base["body"]["default_offset"] = interactive["bodyOffset"]
    if "bodyRotationY" in interactive:
        base["body"]["default_rotation_y"] = interactive["bodyRotationY"]
    if "wireframe" in interactive:
        base["body"]["wireframe"] = interactive["wireframe"]

    # Fidelity level from mode + toggles
    if "mode" in interactive:
        mode = interactive["mode"]
        if mode == "bound":
            base["dosimetry"]["default_level"] = 0
        elif mode == "aggregate":
            base["dosimetry"]["default_level"] = 1
        else:
            level = 2
            if interactive.get("fresnel"):
                level = 3
            if interactive.get("polarisation"):
                level = 4
            if interactive.get("curvature"):
                level = 5
            if interactive.get("diffraction"):
                level = 6
            base["dosimetry"]["default_level"] = level

    # RT config
    if "rtSource" in interactive:
        base["raytracer"]["default_source"] = interactive["rtSource"]
    if "rtMaxOrder" in interactive:
        base["dosimetry"]["default_max_order"] = interactive["rtMaxOrder"]
    if "rtConfig" in interactive:
        base["raytracer"].update(interactive["rtConfig"])

    # Stochastic channel
    if "stochasticPreset" in interactive:
        base["dosimetry"]["stochastic"]["default_preset"] = interactive["stochasticPreset"]
    if "stochasticSeed" in interactive:
        base["dosimetry"]["stochastic"]["default_seed"] = interactive["stochasticSeed"]

    # Display
    if "exposureScenario" in interactive:
        base["dosimetry"]["exposure_scenario"] = interactive["exposureScenario"]
    if "legendScale" in interactive:
        base["dosimetry"]["display_mode"] = interactive["legendScale"]
    if "dynamicRangeDb" in interactive:
        base["dosimetry"]["dynamic_range_db"] = interactive["dynamicRangeDb"]

    return jsonify(base)


def _handle_body(cache):
    """Implementation for /api/body."""
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
        available = sorted(bodies.keys()) if bodies else []
        return jsonify({"error": f"Body '{name}' not found", "available": available}), 404

    resp = Response(entry["binary"], mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(entry["meta"])
    return resp


def _handle_voxels(cache):
    """Implementation for /api/voxels."""
    if cache.get("voxel_binary") is None:
        return jsonify({"error": "No voxel data loaded"}), 404

    data = cache["voxel_binary"]
    meta = cache["voxel_meta"]

    resp = Response(data, mimetype="application/octet-stream")
    resp.headers["X-Meta"] = json.dumps(meta)
    return resp


def _handle_clear_cache(app, cache, cache_lock):
    """Implementation for /api/clear-cache."""
    from aegis.viewer.server import scoped_cache_clear_session

    # Clear shared (non-session-scoped) voxel/tile data
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
        ):
            cache.pop(key, None)
        # Clear all session-scoped cache entries for this user
        scoped_cache_clear_session(cache)
    try:
        from aegis.viewer.raytracer import _scene_cache, clear_voxel_scene_cache

        clear_voxel_scene_cache()
        _scene_cache.clear()
    except ImportError:
        pass
    return jsonify({"ok": True})


def _handle_config(cache):
    """Implementation for /api/config."""
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
        import differt  # noqa: F401

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
    has_env_mesh = scoped_cache_get(cache, "env_mesh") is not None
    tiles_dir = cache.get("tiles_dir")
    n_tiles = cache.get("n_tiles", 0)
    if n_tiles == 0 and tiles_dir:
        n_tiles = len(list(Path(tiles_dir).glob("*.glb")))
        cache["n_tiles"] = n_tiles
    # Report default body name and its meta from preloaded bodies cache
    default_body_name = cache.get("default_body", "")
    bodies_cache = cache.get("bodies", {})
    default_entry = bodies_cache.get(default_body_name)
    body_meta = default_entry["meta"] if default_entry is not None else cache.get("body_meta")
    bodies.sort()

    # Discover GLB (animated) phantoms from phantom_dir
    # Resolve relative to data_dir so CWD doesn't matter
    data_dir_path = Path(cache.get("data_dir", "data"))
    phantom_dir_cfg = cfg.get("body", {}).get("phantom_dir", "")
    if phantom_dir_cfg and Path(phantom_dir_cfg).is_absolute():
        phantom_dir = Path(phantom_dir_cfg)
    else:
        phantom_dir = data_dir_path / "phantoms"
    gltf_bodies = sorted(p.stem for p in phantom_dir.glob("*.glb") if p.is_file()) if phantom_dir.is_dir() else []

    # Merge GLB names into the bodies list so they appear in the dropdown
    all_bodies = sorted(set(bodies) | set(gltf_bodies))

    return jsonify(
        {
            "bodies": all_bodies,
            "gltf_bodies": gltf_bodies,
            "body_name": default_body_name,
            "skin_models": SKIN_MODELS,
            "levels": levels,
            "has_voxels": has_voxels,
            "has_env_mesh": has_env_mesh,
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
            "google_api_key": os.environ.get("GOOGLE_API_KEY", ""),
            "google_map_id": os.environ.get("GOOGLE_MAP_ID", ""),
            "cesium_ion_token": os.environ.get("CESIUM_ION_TOKEN", ""),
            "body_placement": cache.get("body_placement"),
            "body_device_offsets": cache.get("body_device_offsets", {}),
        }
    )


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach data-serving routes to *app*."""

    @app.route("/")
    def index():
        return _handle_index(cache)

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

    @app.route("/api/export-config", methods=["POST"])
    def api_export_config():
        """Return full viewer config with interactive state overlaid."""
        return _handle_export_config(cache, cache_lock)

    @app.route("/api/body")
    def api_body():
        """Return body mesh as binary (positions + normals, float32).

        Accepts optional ?name= query parameter to select a specific body.
        Defaults to the default body loaded at startup.
        """
        return _handle_body(cache)

    @app.route("/api/voxels")
    def api_voxels():
        """Return voxel data as binary (positions float32 + colors uint8 + materials uint8)."""
        return _handle_voxels(cache)

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

    @app.route("/api/phantom/<name>.glb")
    def serve_phantom_glb(name):
        """Serve a GLB phantom file."""
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            abort(400, "Invalid phantom name")
        data_dir_path = Path(cache.get("data_dir", "data"))
        phantom_dir_cfg = cache["config"]["body"].get("phantom_dir", "")
        if phantom_dir_cfg and Path(phantom_dir_cfg).is_absolute():
            phantom_dir = Path(phantom_dir_cfg)
        else:
            phantom_dir = data_dir_path / "phantoms"
        path = (phantom_dir / f"{name}.glb").resolve()
        if not path.is_relative_to(phantom_dir.resolve()):
            abort(403)
        if not path.is_file():
            abort(404)
        return send_file(path, mimetype="model/gltf-binary", conditional=True, max_age=3600)

    @app.route("/api/clear-cache", methods=["POST"])
    def api_clear_cache():
        """Clear all cached voxel, scene, and MIMO data."""
        return _handle_clear_cache(app, cache, cache_lock)

    @app.route("/api/config")
    def api_config():
        """Return available configuration options."""
        return _handle_config(cache)
