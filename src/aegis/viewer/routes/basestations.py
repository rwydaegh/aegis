"""Base station routes: load, list, and compute dosimetry from cell towers."""

from __future__ import annotations

import json
import logging
import threading

import numpy as np
from flask import Flask, Response, jsonify, request

logger = logging.getLogger(__name__)

_OCTET_STREAM = "application/octet-stream"


def register(app: Flask, cache: dict, cache_lock: threading.RLock) -> None:
    """Register base station API routes."""

    @app.route("/api/basestations/load", methods=["POST"])
    def api_basestations_load():
        """Load base stations from basestationLib for a given area."""
        try:
            from aegis.basestation.adapter import load_basestations
        except ImportError as exc:
            return jsonify({"error": str(exc)}), 500

        params = request.get_json(silent=True) or {}
        country = params.get("country", "Belgium")
        region = params.get("region", "brussels")

        # Build bbox from lat/lon/radius or use explicit bbox
        bbox = params.get("bbox")
        if bbox is None and "lat" in params and "lon" in params:
            lat = float(params["lat"])
            lon = float(params["lon"])
            radius_m = float(params.get("radius_m", 500))
            dlat = radius_m / 111_320.0
            dlon = radius_m / (111_320.0 * np.cos(np.radians(lat)))
            bbox = [lon - dlon, lon + dlon, lat - dlat, lat + dlat]

        try:
            basestations = load_basestations(
                country=country,
                region=region,
                bbox=bbox,
                operator=params.get("operator"),
                technology=params.get("technology"),
                max_workers=int(params.get("max_workers", 4)),
            )
        except Exception as exc:
            logger.exception("Failed to load basestations")
            return jsonify({"error": f"Loading failed: {exc}"}), 500

        # Store in cache
        with cache_lock:
            cache["basestations"] = basestations
            if bbox and len(bbox) == 4:
                cache["basestations_origin"] = (
                    (bbox[2] + bbox[3]) / 2,
                    (bbox[0] + bbox[1]) / 2,
                )
            elif "lat" in params:
                cache["basestations_origin"] = (
                    float(params["lat"]),
                    float(params["lon"]),
                )

        return jsonify(
            {
                "count": len(basestations),
                "basestations": [_bs_summary(bs) for bs in basestations],
            }
        )

    @app.route("/api/basestations/list")
    def api_basestations_list():
        """List currently loaded base stations."""
        with cache_lock:
            basestations = cache.get("basestations", [])

        return jsonify(
            {
                "count": len(basestations),
                "basestations": [_bs_summary(bs) for bs in basestations],
            }
        )

    @app.route("/api/basestations/compute", methods=["POST"])
    def api_basestations_compute():
        """Compute dosimetry from loaded base stations.

        Returns binary sab array with X-Stats JSON header (same format
        as /api/dosimetry).
        """
        from aegis.basestation.adapter import paths_from_basestations
        from aegis.engine import DosimetryEngine
        from aegis.viewer.compute import resolve_skin_model
        from aegis.viewer.routes.compute import (
            _build_binary_response,
            _build_stats_response,
            _inject_curvature_H,
            _parse_vec3,
        )

        with cache_lock:
            basestations = cache.get("basestations", [])
            origin = cache.get("basestations_origin")
            body = cache.get("body")

        if not basestations:
            return jsonify({"error": "No base stations loaded"}), 400
        if body is None:
            return jsonify({"error": "No body mesh loaded"}), 400
        if origin is None:
            return jsonify({"error": "No scene origin set"}), 400

        params = request.get_json(silent=True) or {}

        # Filter by indices
        indices = params.get("indices")
        selected = basestations
        if indices is not None:
            selected = [basestations[i] for i in indices if 0 <= i < len(basestations)]
        if not selected:
            return jsonify({"error": "No base stations selected"}), 400

        # Body offset
        body_offset, err = _parse_vec3(params, "body_offset", [0, 0, 0])
        if err:
            return err

        body_center = np.mean(body.centroids, axis=0) + body_offset

        # Compute paths
        paths = paths_from_basestations(
            selected,
            body_center,
            origin,
            max_distance_m=float(params.get("max_distance_m", 2000)),
        )

        if paths.n_paths == 0 or paths.total_power <= 0:
            # Return zero result
            n_tri = body.n_triangles
            sab_bytes = np.zeros(n_tri, dtype=np.float32).tobytes()
            stats = {
                "p_abs": 0,
                "p_abs_mw": 0,
                "peak_sab": 0,
                "n_illuminated": 0,
                "n_triangles": n_tri,
                "n_basestations": len(selected),
                "n_paths": 0,
                "arrays": [{"key": "sab", "offset": 0, "length": n_tri}],
                "peaks": {"sab": 0.0},
            }
            resp = Response(sab_bytes, mimetype=_OCTET_STREAM)
            resp.headers["X-Stats"] = json.dumps(stats)
            resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
            return resp

        # EIRP-weighted average frequency for tissue model
        freq_hz = params.get("freq_hz")
        if freq_hz is None:
            total_eirp_w = sum(10 ** ((bs.eirp_dbm - 30) / 10) for bs in selected)
            if total_eirp_w > 0:
                freq_hz = sum(bs.freq_hz * 10 ** ((bs.eirp_dbm - 30) / 10) for bs in selected) / total_eirp_w
            else:
                freq_hz = 3.5e9
        freq_hz = float(freq_hz)

        skin_model = params.get("skin_model", "itis")
        tissue = resolve_skin_model(skin_model, freq_hz)

        # Dosimetry engine
        engine = DosimetryEngine(tissue)
        mode = params.get("mode", "spatial")
        engine_kw = {"mode": mode, "spatial_averaging": True}
        engine_kw = _inject_curvature_H(engine_kw, body)

        result = engine.compute(body, paths, **engine_kw)

        # Build response using existing format
        quantities = params.get("quantities", ["sab", "sab_4cm2"])
        buf, arrays_meta = _build_binary_response(result, quantities)

        level, mode_str, corrections = None, mode, []
        stats = _build_stats_response(
            result,
            body,
            tissue,
            level,
            mode=mode_str,
            corrections=corrections,
            extra={
                "n_basestations": len(selected),
                "n_paths": paths.n_paths,
                "freq_hz": freq_hz,
                "total_power_w_m2": float(paths.total_power),
                "arrays": arrays_meta,
            },
        )

        resp = Response(bytes(buf), mimetype=_OCTET_STREAM)
        resp.headers["X-Stats"] = json.dumps(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp


def _bs_summary(bs) -> dict:
    """Serialize a BaseStation to a JSON-safe dict."""
    return {
        "site_code": bs.site_code,
        "antenna_label": bs.antenna_label,
        "operator": bs.operator,
        "technology": bs.technology,
        "latitude": bs.latitude,
        "longitude": bs.longitude,
        "height_m": bs.height_m,
        "eirp_dbm": bs.eirp_dbm,
        "gain_dbi": bs.gain_dbi,
        "freq_mhz": bs.freq_mhz,
        "azimuth_deg": bs.azimuth_deg,
        "total_tilt_deg": bs.total_tilt_deg,
        "has_pattern": bs.pattern is not None,
        "horizontal_beamwidth_deg": bs.horizontal_beamwidth_deg,
        "vertical_beamwidth_deg": bs.vertical_beamwidth_deg,
    }
