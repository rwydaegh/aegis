"""Location loading routes: SSE pipeline streaming, cancellation, and geocoding."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import requests as http_requests
from flask import Flask, Response, jsonify, request, session

from aegis.viewer.config import DEFAULTS as _VIEWER_DEFAULTS
from aegis.viewer.routes._types import RouteResponse

logger = logging.getLogger(__name__)

_ErrResp = tuple[Response, int]

_GOOGLE_API_KEY_MISSING = "GOOGLE_API_KEY not set"
_NETWORK_TIMEOUT_S = _VIEWER_DEFAULTS["server"]["network_timeout_s"]


def _parse_load_params() -> tuple[dict[str, Any] | None, _ErrResp | None]:
    """Parse location/radius/voxel_size/force from request args.

    Returns (params_dict, None) on success or (None, error_response) on failure.
    """
    location = request.args.get("location", "").strip()
    try:
        radius = int(request.args.get("radius", 30))
        voxel_size = float(request.args.get("voxel_size", 0.5))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "radius must be integer, voxel_size must be number"}), 400)
    force = request.args.get("force", "false").lower() == "true"
    return (
        {"location": location, "radius": radius, "voxel_size": voxel_size, "force": force},
        None,
    )


def _validate_load_params(params: dict) -> _ErrResp | None:
    """Validate parsed location load params.

    Returns None on success or an error response tuple on failure.
    """
    location = params["location"]
    radius = params["radius"]
    voxel_size = params["voxel_size"]

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
    return None


def _resolve_pipeline_paths(
    cache: dict, location: str, radius: int
) -> tuple[tuple[Any, Any, Any, Any] | None, _ErrResp | None]:
    """Resolve pipeline script path and output directories.

    Returns ((pipeline_js, pipeline_output, voxel_output), None) on success
    or (None, error_response) on failure.
    """
    from aegis.viewer.pipeline import cache_dir_for, find_pipeline

    pipeline_dir = cache.get("pipeline_dir")
    pipeline_js = find_pipeline(pipeline_dir)
    if pipeline_js is None:
        return None, (
            jsonify({"error": "Pipeline not found. Set VOXELEARTH_DIR or use --pipeline-dir"}),
            404,
        )

    base_cache = Path(
        cache.get("cache_dir") or os.environ.get("VOXELEARTH_CACHE_DIR") or str(pipeline_js.parent / "pipeline_cache")
    )
    voxel_output = cache_dir_for(location, radius, base_cache)
    pipeline_output = voxel_output.parent
    return (pipeline_js, pipeline_output, voxel_output, pipeline_dir), None


def _compute_resolution(radius: int, voxel_size: float) -> int:
    """Convert voxel size (meters) to resolution (voxels per dimension).

    The voxelizer divides the longest bounding-box dimension by resolution,
    so resolution = (2 * radius) / voxel_size is a good approximation.
    Cap at 2000 to prevent resource exhaustion from extreme combinations.
    """
    return min(2000, max(10, round((2 * radius) / voxel_size)))


def _stream_pipeline_run(location, radius, api_key, pipeline_output, resolution, pipeline_dir, sid):
    """Yield SSE progress events from a pipeline subprocess run.

    Yields either progress events or a single error event (terminal).
    """
    from aegis.viewer.pipeline import run_pipeline

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
            if line.startswith("ERROR:"):
                yield f"event: error\ndata: {line}\n\n"
                return
            yield f"event: progress\ndata: {line}\n\n"
    except Exception as e:
        logger.exception("Pipeline execution failed")
        err_type = type(e).__name__
        yield f"event: error\ndata: ERROR: Pipeline failed ({err_type}). Check server logs.\n\n"


def _refresh_tiles_dir(cache: dict, cache_lock, voxel_output: Path):
    """Recompute tiles_dir on cache, returning the resolved path or None."""
    tiles_candidate = voxel_output.parent / "tiles"
    with cache_lock:
        cache["tiles_dir"] = None
        if tiles_candidate.is_dir() and any(tiles_candidate.glob("*.glb")):
            cache["tiles_dir"] = tiles_candidate
        return cache.get("tiles_dir")


def _stream_voxel_load(cache: dict, cache_lock, voxel_output: Path):
    """Yield SSE progress events for loading voxels + fixing/counting GLB tiles."""
    from aegis.viewer.pipeline import fix_glb_tiles_dir
    from aegis.viewer.raytracer import clear_voxel_scene_cache
    from aegis.viewer.server import _load_and_cache_voxels_dir

    yield "event: progress\ndata: Loading voxels into viewer...\n\n"
    br = cache.get("bbox_radius", 15.0)
    _load_and_cache_voxels_dir(str(voxel_output), br)

    clear_voxel_scene_cache()
    tiles_dir = _refresh_tiles_dir(cache, cache_lock, voxel_output)
    if tiles_dir is not None:
        n_fixed = fix_glb_tiles_dir(tiles_dir)
        if n_fixed:
            yield f"event: progress\ndata: Fixed blob URIs in {n_fixed} GLB file(s)\n\n"
        n_tiles = len(list(tiles_dir.glob("*.glb")))
        yield f"event: progress\ndata: Found {n_tiles} GLB tiles\n\n"

    meta = cache.get("voxel_meta", {})
    yield f"event: done\ndata: {json.dumps(meta)}\n\n"


def _api_location_load_impl(cache: dict, cache_lock) -> RouteResponse:
    """Stream pipeline progress via SSE, then load voxels."""
    params, err = _parse_load_params()
    if err is not None:
        return err
    assert params is not None  # noqa: S101 - helper contract
    validate_err = _validate_load_params(params)
    if validate_err is not None:
        return validate_err

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return jsonify({"error": _GOOGLE_API_KEY_MISSING}), 400

    paths, err = _resolve_pipeline_paths(cache, params["location"], params["radius"])
    if err is not None:
        return err
    assert paths is not None  # noqa: S101 - helper contract
    _pipeline_js, pipeline_output, voxel_output, pipeline_dir = paths

    resolution = _compute_resolution(params["radius"], params["voxel_size"])
    sid = session.get("session_id", "default")
    location = params["location"]
    radius = params["radius"]
    force = params["force"]

    def generate():
        cached = voxel_output.exists() and any(voxel_output.glob("*.json"))
        if cached and not force:
            yield "event: progress\ndata: Using cached data\n\n"
        else:
            had_error = False
            for event in _stream_pipeline_run(
                location, radius, api_key, pipeline_output, resolution, pipeline_dir, sid
            ):
                yield event
                if event.startswith("event: error"):
                    had_error = True
            if had_error:
                return

        try:
            yield from _stream_voxel_load(cache, cache_lock, voxel_output)
        except Exception as e:
            logger.exception("Voxel loading failed in SSE stream")
            err_type = type(e).__name__
            yield f"event: error\ndata: Voxel load failed ({err_type}). Check server logs.\n\n"
            yield "event: done\ndata: {}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _validate_geocode_query(q: str) -> _ErrResp | None:
    """Validate the geocode query string. Returns None or an error response."""
    if not q:
        return jsonify({"error": "Missing q parameter"}), 400
    if len(q) > 500:
        return jsonify({"error": "Query too long (max 500 characters)"}), 400
    return None


def _fetch_geocode(q: str, api_key: str) -> tuple[dict[str, Any] | None, _ErrResp | None]:
    """Call Google Geocoding API. Returns (data, None) or (None, error_response)."""
    try:
        resp = http_requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": q, "key": api_key},
            timeout=_NETWORK_TIMEOUT_S,
        )
        resp.raise_for_status()
        return resp.json(), None
    except Exception as exc:
        logger.exception("Geocoding request failed")
        return None, (jsonify({"error": f"Geocoding failed: {exc}"}), 502)


def _extract_geocode_result(data: dict, q: str) -> tuple[tuple[float, float, str] | None, _ErrResp | None]:
    """Extract (lat, lng, formatted) from geocoding response.

    Returns ((lat, lng, formatted), None) on success or (None, error_response) on failure.
    """
    results = data.get("results", [])
    if not results:
        return None, (jsonify({"error": f"No results for '{q}'"}), 404)
    try:
        loc = results[0]["geometry"]["location"]
        lat, lng = loc["lat"], loc["lng"]
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("Malformed geocode response for %r: %s", q, exc)
        return None, (jsonify({"error": "Geocoding returned an unexpected response format"}), 502)
    formatted = results[0].get("formatted_address", q)
    return (lat, lng, formatted), None


def _api_geocode_impl(cache: dict, cache_lock) -> RouteResponse:
    """Resolve a text location to lat/lon using Google Geocoding API."""
    q = request.args.get("q", "").strip()
    err = _validate_geocode_query(q)
    if err is not None:
        return err

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return jsonify({"error": _GOOGLE_API_KEY_MISSING}), 400

    data, err = _fetch_geocode(q, api_key)
    if err is not None:
        return err
    assert data is not None  # noqa: S101 - helper contract

    extracted, err = _extract_geocode_result(data, q)
    if err is not None:
        return err
    assert extracted is not None  # noqa: S101 - helper contract
    lat, lng, formatted = extracted
    return jsonify({"lat": lat, "lon": lng, "formatted": formatted})


def _api_location_cancel_impl(cache: dict, cache_lock) -> RouteResponse:
    """Kill running pipeline subprocess for the current session."""
    from aegis.viewer.pipeline import cancel_pipeline

    sid = session.get("session_id", "default")
    killed = cancel_pipeline(session_id=sid)
    return jsonify({"cancelled": killed})


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach location-loading routes to *app*."""

    @app.route("/api/location/load")
    def api_location_load():
        return _api_location_load_impl(cache, cache_lock)

    @app.route("/api/geocode")
    def api_geocode():
        return _api_geocode_impl(cache, cache_lock)

    @app.route("/api/location/cancel", methods=["POST"])
    def api_location_cancel():
        return _api_location_cancel_impl(cache, cache_lock)
