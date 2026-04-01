"""Antenna pattern library routes: search, load, and index management."""

from __future__ import annotations

import json
import logging
import os
import threading

import numpy as np
from flask import Flask, Response, jsonify, request

logger = logging.getLogger(__name__)

_OCTET_STREAM = "application/octet-stream"

# Module-level singleton (created on first request)
_library_instance = None
_library_lock = threading.Lock()


def _get_library(cache: dict):
    """Return (or lazily create) the AntennaPatternLibrary singleton."""
    global _library_instance
    if _library_instance is not None:
        return _library_instance

    with _library_lock:
        if _library_instance is not None:
            return _library_instance

        from aegis.basestation.library import AntennaPatternLibrary

        data_dir = cache.get("data_dir", "data")
        cfg = cache.get("config", {})
        key_env = cfg.get("basestations", {}).get("pattern_library", {}).get("cloudrf_api_key_env", "CLOUDRF_API_KEY")
        cloudrf_api_key = os.environ.get(key_env)
        _library_instance = AntennaPatternLibrary(
            data_dir=data_dir,
            cloudrf_api_key=cloudrf_api_key,
        )
        logger.info("AntennaPatternLibrary initialised (data_dir=%s)", data_dir)
    return _library_instance


def _handle_search(cache: dict):
    """Implementation for GET /api/patterns/search."""
    q = request.args.get("q", "")
    manufacturer = request.args.get("manufacturer") or None
    source = request.args.get("source", "all")

    def _float_arg(name):
        v = request.args.get(name)
        if v is None:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    freq_min = _float_arg("freq_min")
    freq_max = _float_arg("freq_max")
    gain_min = _float_arg("gain_min")
    gain_max = _float_arg("gain_max")

    limit_str = request.args.get("limit", "50")
    try:
        limit = int(limit_str)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    if limit < 1 or limit > 1000:
        return jsonify({"error": "limit must be between 1 and 1000"}), 400

    lib = _get_library(cache)
    try:
        results = lib.search(
            query=q,
            manufacturer=manufacturer,
            freq_min_mhz=freq_min,
            freq_max_mhz=freq_max,
            gain_min_dbi=gain_min,
            gain_max_dbi=gain_max,
            source=source,
            limit=limit,
        )
    except Exception as exc:
        logger.exception("Pattern search failed")
        return jsonify({"error": f"Search failed: {exc}"}), 500

    return jsonify(
        {
            "results": [
                {
                    "id": r.id,
                    "source": r.source,
                    "manufacturer": r.manufacturer,
                    "model": r.model,
                    "frequency_mhz": r.frequency_mhz,
                    "gain_dbi": r.gain_dbi,
                    "tilt_deg": r.tilt_deg,
                }
                for r in results
            ]
        }
    )


def _handle_load(cache: dict, source: str, pattern_id: str):
    """Implementation for GET /api/patterns/<source>/<path:pattern_id>."""
    lib = _get_library(cache)
    try:
        pattern = lib.load_pattern(source, pattern_id)
    except KeyError:
        return jsonify({"error": f"Pattern not found: {pattern_id}"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Failed to load pattern %s/%s", source, pattern_id)
        return jsonify({"error": f"Load failed: {exc}"}), 500

    # Flatten (181, 360) -> (65160,) float32
    data = pattern.gain_dbi.astype(np.float32)
    # Replace NaN with -200 (noise floor) for binary transmission
    data = np.nan_to_num(data, nan=-200.0)
    raw_bytes = data.flatten().tobytes()

    meta = {
        "id": pattern_id,
        "source": source,
        "max_gain_dbi": float(pattern.max_gain_dbi),
        "shape": [181, 360],
    }

    resp = Response(raw_bytes, mimetype=_OCTET_STREAM)
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp


def _handle_manufacturers(cache: dict):
    """Implementation for GET /api/patterns/manufacturers."""
    lib = _get_library(cache)
    try:
        results = lib.search(limit=10000)
    except Exception as exc:
        logger.exception("Failed to fetch manufacturers")
        return jsonify({"error": f"Failed: {exc}"}), 500

    manufacturers = sorted({r.manufacturer for r in results})
    return jsonify({"manufacturers": manufacturers})


def _handle_build_index(cache: dict):
    """Implementation for POST /api/patterns/build-index."""
    global _library_instance

    # Reset singleton so next call picks up rebuilt index
    with _library_lock:
        _library_instance = None

    lib = _get_library(cache)
    try:
        count = lib.build_index()
    except Exception as exc:
        logger.exception("Index build failed")
        return jsonify({"error": f"Build failed: {exc}"}), 500

    return jsonify({"count": count})


def register(app: Flask, cache: dict, cache_lock: threading.RLock) -> None:
    """Register antenna pattern API routes."""

    @app.route("/api/patterns/search")
    def api_patterns_search():
        """Search the antenna pattern index."""
        return _handle_search(cache)

    @app.route("/api/patterns/manufacturers")
    def api_patterns_manufacturers():
        """List unique manufacturers in the local index."""
        return _handle_manufacturers(cache)

    @app.route("/api/patterns/build-index", methods=["POST"])
    def api_patterns_build_index():
        """Rebuild the SQLite antenna pattern index from MSI zip archives."""
        return _handle_build_index(cache)

    @app.route("/api/patterns/<source>/<path:pattern_id>")
    def api_patterns_load(source: str, pattern_id: str):
        """Load a full 2D antenna pattern as binary float32."""
        return _handle_load(cache, source, pattern_id)
