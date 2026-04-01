"""Antenna pattern library routes: browse and load MSI patterns."""

from __future__ import annotations

import logging
import math
import os
import threading

from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)

# Lazily initialized pattern index
_pattern_index = None
_pattern_index_lock = threading.Lock()


def _get_index(app: Flask):
    """Return the lazily initialized PatternIndex, scanning on first call."""
    global _pattern_index
    if _pattern_index is not None:
        return _pattern_index
    with _pattern_index_lock:
        if _pattern_index is not None:
            return _pattern_index
        from aegis.basestation.msi import PatternIndex

        idx = PatternIndex()
        pattern_dir = app.config.get(
            "PATTERN_DIR",
            os.path.join("data", "antenna_patterns", "msi_raw"),
        )
        if os.path.isdir(pattern_dir):
            idx.scan_directory(pattern_dir)
            logger.info("Pattern index: scanned %s, found %d entries", pattern_dir, len(idx._entries))
        else:
            logger.warning("Pattern directory not found: %s", pattern_dir)
        _pattern_index = idx
    return _pattern_index


def register(app: Flask, cache: dict, cache_lock: threading.RLock) -> None:
    """Register antenna pattern library API routes."""

    @app.route("/api/patterns/manufacturers")
    def api_patterns_manufacturers():
        """List all manufacturers in the pattern library."""
        idx = _get_index(app)
        return jsonify({"manufacturers": idx.list_manufacturers()})

    @app.route("/api/patterns/models")
    def api_patterns_models():
        """List models for a given manufacturer."""
        manufacturer = request.args.get("manufacturer")
        if not manufacturer:
            return jsonify({"error": "Missing required parameter: manufacturer"}), 400
        idx = _get_index(app)
        models = idx.list_models(manufacturer)
        return jsonify({"manufacturer": manufacturer, "models": models})

    @app.route("/api/patterns/search")
    def api_patterns_search():
        """Search patterns by query, manufacturer, and/or frequency."""
        q = request.args.get("q") or None
        manufacturer = request.args.get("manufacturer") or None
        freq_mhz_str = request.args.get("freq_mhz")
        freq_mhz = None
        if freq_mhz_str is not None:
            try:
                freq_mhz = float(freq_mhz_str)
            except ValueError:
                return jsonify({"error": "freq_mhz must be a number"}), 400

        idx = _get_index(app)
        results = idx.search(query=q, manufacturer=manufacturer, freq_mhz=freq_mhz)
        total = len(results)
        results = results[:100]
        return jsonify(
            {
                "results": [
                    {
                        "manufacturer": e.manufacturer,
                        "model": e.model,
                        "frequency_mhz": None if math.isnan(e.frequency_mhz) else e.frequency_mhz,
                        "id": f"{e.manufacturer}/{e.inner_path}",
                    }
                    for e in results
                ],
                "total": total,
            }
        )

    @app.route("/api/patterns/load", methods=["POST"])
    def api_patterns_load():
        """Load a pattern by id and return its metadata."""
        body = request.get_json(silent=True) or {}
        pattern_id = body.get("id")
        if not pattern_id:
            return jsonify({"error": "Missing required field: id"}), 400

        idx = _get_index(app)
        entry = idx.get_by_id(pattern_id)
        if entry is None:
            return jsonify({"error": f"Pattern not found: {pattern_id!r}"}), 404

        try:
            header, pattern = idx.load(entry)
        except Exception as exc:
            logger.exception("Failed to load pattern %r", pattern_id)
            return jsonify({"error": f"Failed to load pattern: {exc}"}), 500

        return jsonify(
            {
                "name": header.name,
                "frequency_mhz": None if math.isnan(header.frequency_mhz) else header.frequency_mhz,
                "max_gain_dbi": header.gain_dbi,
                "tilt_deg": header.tilt_deg,
                "shape": list(pattern.gain_dbi.shape),
            }
        )
