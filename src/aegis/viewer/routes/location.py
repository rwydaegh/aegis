"""Location loading routes: SSE pipeline streaming, cancellation, and geocoding."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests as http_requests
from flask import Flask, Response, jsonify, request, session

logger = logging.getLogger(__name__)


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach location-loading routes to *app*."""

    @app.route("/api/location/load")
    def api_location_load():
        """Stream pipeline progress via SSE, then load voxels."""
        from aegis.viewer.pipeline import (
            cache_dir_for,
            find_pipeline,
            run_pipeline,
        )

        location = request.args.get("location", "").strip()
        try:
            radius = int(request.args.get("radius", 30))
            voxel_size = float(request.args.get("voxel_size", 0.5))
        except (TypeError, ValueError):
            return jsonify({"error": "radius must be integer, voxel_size must be number"}), 400
        force = request.args.get("force", "false").lower() == "true"

        if not location:
            return jsonify({"error": "Missing location parameter"}), 400
        if len(location) > 500:
            return jsonify({"error": "Location string too long (max 500 characters)"}), 400

        if radius <= 0 or radius > 500:
            return jsonify({"error": "radius must be between 1 and 500 meters"}), 400
        if voxel_size <= 0 or voxel_size > 10:
            return jsonify({"error": "voxel_size must be between 0 (exclusive) and 10 meters"}), 400
        if voxel_size < 0.1:
            return jsonify({"error": "voxel_size below 0.1m would produce too many voxels"}), 400

        # Convert voxel size (meters) to resolution (voxels per dimension).
        # The voxelizer divides the longest bounding-box dimension by resolution,
        # so resolution = (2 * radius) / voxel_size is a good approximation.
        # Cap at 2000 to prevent resource exhaustion from extreme combinations.
        resolution = min(2000, max(10, round((2 * radius) / voxel_size)))

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return jsonify({"error": "GOOGLE_API_KEY not set"}), 400

        pipeline_dir = cache.get("pipeline_dir")
        pipeline_js = find_pipeline(pipeline_dir)
        if pipeline_js is None:
            return jsonify({"error": "Pipeline not found. Set VOXELEARTH_DIR or use --pipeline-dir"}), 404

        # Determine cache/output directory
        base_cache = Path(
            cache.get("cache_dir")
            or os.environ.get("VOXELEARTH_CACHE_DIR")
            or str(pipeline_js.parent / "pipeline_cache")
        )
        voxel_output = cache_dir_for(location, radius, base_cache)
        pipeline_output = voxel_output.parent

        sid = session.get("session_id", "default")

        def generate():
            # Check cache
            cached = voxel_output.exists() and any(voxel_output.glob("*.json"))
            if cached and not force:
                yield "event: progress\ndata: Using cached data\n\n"
            else:
                # Run pipeline
                try:
                    for line in run_pipeline(
                        location,
                        radius,
                        api_key,
                        pipeline_output,
                        resolution=resolution,
                        pipeline_dir=pipeline_dir,
                        session_id=sid,
                    ):
                        # Filter noisy THREE.js warnings from Node.js pipeline
                        if "Couldn't load texture blob:" in line:
                            continue
                        yield f"event: progress\ndata: {line}\n\n"
                        if line.startswith("ERROR:"):
                            yield f"event: error\ndata: {line}\n\n"
                            return
                except Exception as e:
                    logger.exception("Pipeline execution failed")
                    err_type = type(e).__name__
                    yield f"event: error\ndata: ERROR: Pipeline failed ({err_type}). Check server logs.\n\n"
                    return

            # Load voxels from output directory
            try:
                from aegis.viewer.raytracer import clear_voxel_scene_cache
                from aegis.viewer.server import _load_and_cache_voxels_dir

                yield "event: progress\ndata: Loading voxels into viewer...\n\n"
                br = cache.get("bbox_radius", 15.0)
                _load_and_cache_voxels_dir(str(voxel_output), br)

                # Refresh tiles_dir (tiles may now exist after pipeline run)
                clear_voxel_scene_cache()
                tiles_candidate = voxel_output.parent / "tiles"
                with cache_lock:
                    cache["tiles_dir"] = None
                    if tiles_candidate.is_dir() and any(tiles_candidate.glob("*.glb")):
                        cache["tiles_dir"] = tiles_candidate
                    tiles_dir = cache.get("tiles_dir")
                if tiles_dir is not None:
                    # Fix invalid blob:nodedata: URIs in GLB textures
                    from aegis.viewer.pipeline import fix_glb_tiles_dir

                    n_fixed = fix_glb_tiles_dir(tiles_dir)
                    if n_fixed:
                        yield f"event: progress\ndata: Fixed blob URIs in {n_fixed} GLB file(s)\n\n"
                    n_tiles = len(list(tiles_dir.glob("*.glb")))
                    yield f"event: progress\ndata: Found {n_tiles} GLB tiles\n\n"

                meta = cache.get("voxel_meta", {})
                yield f"event: done\ndata: {json.dumps(meta)}\n\n"
            except Exception as e:
                logger.exception("Voxel loading failed in SSE stream")
                err_type = type(e).__name__
                yield f"event: error\ndata: Voxel load failed ({err_type}). Check server logs.\n\n"

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.route("/api/geocode")
    def api_geocode():
        """Resolve a text location to lat/lon using Google Geocoding API."""
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify({"error": "Missing q parameter"}), 400
        if len(q) > 500:
            return jsonify({"error": "Query too long (max 500 characters)"}), 400

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return jsonify({"error": "GOOGLE_API_KEY not set"}), 400

        try:
            resp = http_requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": q, "key": api_key},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.exception("Geocoding request failed")
            return jsonify({"error": f"Geocoding failed: {exc}"}), 502

        results = data.get("results", [])
        if not results:
            return jsonify({"error": f"No results for '{q}'"}), 404

        try:
            loc = results[0]["geometry"]["location"]
            lat, lng = loc["lat"], loc["lng"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Malformed geocode response for %r: %s", q, exc)
            return jsonify({"error": "Geocoding returned an unexpected response format"}), 502

        return jsonify(
            {
                "lat": lat,
                "lon": lng,
                "formatted": results[0].get("formatted_address", q),
            }
        )

    @app.route("/api/location/cancel", methods=["POST"])
    def api_location_cancel():
        """Kill running pipeline subprocess for the current session."""
        from aegis.viewer.pipeline import cancel_pipeline

        sid = session.get("session_id", "default")
        killed = cancel_pipeline(session_id=sid)
        return jsonify({"cancelled": killed})
