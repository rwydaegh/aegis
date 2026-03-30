"""Location loading routes: SSE pipeline streaming and cancellation."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

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

        if radius <= 0 or radius > 500:
            return jsonify({"error": "radius must be between 1 and 500 meters"}), 400
        if voxel_size <= 0 or voxel_size > 10:
            return jsonify({"error": "voxel_size must be between 0 (exclusive) and 10 meters"}), 400
        if voxel_size < 0.1:
            return jsonify({"error": "voxel_size below 0.1m would produce too many voxels"}), 400

        # Convert voxel size (meters) to resolution (voxels per dimension).
        # The voxelizer divides the longest bounding-box dimension by resolution,
        # so resolution = (2 * radius) / voxel_size is a good approximation.
        resolution = max(10, round((2 * radius) / voxel_size))

        if not location:
            return jsonify({"error": "Missing location parameter"}), 400

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return jsonify({"error": "GOOGLE_API_KEY not set"}), 400

        pipeline_dir = cache.get("pipeline_dir")
        if find_pipeline(pipeline_dir) is None:
            return jsonify({"error": "Pipeline not found. Set VOXELEARTH_DIR or use --pipeline-dir"}), 404

        # Determine cache/output directory
        pipeline_js = find_pipeline(pipeline_dir)
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
                for line in run_pipeline(
                    location,
                    radius,
                    api_key,
                    pipeline_output,
                    resolution=resolution,
                    pipeline_dir=pipeline_dir,
                    session_id=sid,
                ):
                    yield f"event: progress\ndata: {line}\n\n"
                    if line.startswith("ERROR:"):
                        yield f"event: error\ndata: {line}\n\n"
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
                    n_tiles = len(list(tiles_dir.glob("*.glb")))
                    yield f"event: progress\ndata: Found {n_tiles} GLB tiles\n\n"

                meta = cache.get("voxel_meta", {})
                yield f"event: done\ndata: {json.dumps(meta)}\n\n"
            except Exception as e:
                logger.exception("Voxel loading failed in SSE stream")
                yield f"event: error\ndata: Voxel load failed: {e}\n\n"

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.route("/api/location/cancel", methods=["POST"])
    def api_location_cancel():
        """Kill running pipeline subprocess for the current session."""
        from aegis.viewer.pipeline import cancel_pipeline

        sid = session.get("session_id", "default")
        killed = cancel_pipeline(session_id=sid)
        return jsonify({"cancelled": killed})
