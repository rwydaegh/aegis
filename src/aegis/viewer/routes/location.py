"""Location loading routes: SSE pipeline streaming and cancellation."""

from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, Response, jsonify, request


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
        radius = int(request.args.get("radius", 30))
        force = request.args.get("force", "false").lower() == "true"

        if not location:
            return jsonify({"error": "Missing location parameter"}), 400

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return jsonify({"error": "GOOGLE_API_KEY not set"}), 400

        if find_pipeline() is None:
            return jsonify({"error": "Pipeline not found"}), 404

        # Determine cache/output directory
        base_cache = Path(
            cache.get("cache_dir")
            or os.environ.get("VOXELEARTH_CACHE_DIR")
            or str(find_pipeline().parent / "pipeline_cache")
        )
        voxel_output = cache_dir_for(location, radius, base_cache)
        pipeline_output = voxel_output.parent

        def generate():
            # Check cache
            cached = voxel_output.exists() and any(voxel_output.glob("*.json"))
            if cached and not force:
                yield "event: progress\ndata: Using cached data\n\n"
            else:
                # Run pipeline
                for line in run_pipeline(location, radius, api_key, pipeline_output):
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
                with cache_lock:
                    cache["tiles_dir"] = None
                    tiles_candidate = voxel_output.parent / "tiles"
                    if tiles_candidate.is_dir() and any(tiles_candidate.glob("*.glb")):
                        cache["tiles_dir"] = tiles_candidate
                if cache.get("tiles_dir") is not None:
                    yield f"event: progress\ndata: Found {len(list(tiles_candidate.glob('*.glb')))} GLB tiles\n\n"

                meta = cache.get("voxel_meta", {})
                yield f"event: done\ndata: {json.dumps(meta)}\n\n"
            except Exception as e:
                yield f"event: error\ndata: Voxel load failed: {e}\n\n"

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.route("/api/location/cancel", methods=["POST"])
    def api_location_cancel():
        """Kill running pipeline subprocess."""
        from aegis.viewer.pipeline import cancel_pipeline

        killed = cancel_pipeline()
        return jsonify({"cancelled": killed})
