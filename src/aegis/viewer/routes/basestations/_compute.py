"""POST /api/basestations/compute handler."""

from __future__ import annotations

import logging
import threading

import numpy as np
from flask import Response, jsonify

from aegis.viewer.routes._helpers import get_json_dict
from aegis.viewer.routes._types import RouteResponse
from aegis.viewer.server import scoped_cache_get

logger = logging.getLogger(__name__)

_OCTET_STREAM = "application/octet-stream"
_VALID_MODES = {"bound", "aggregate", "spatial"}


def _parse_body_transform(params: dict, transform_fns: dict):
    body_offset, err = transform_fns["_parse_vec3"](params, "body_offset", [0, 0, 0])
    if err:
        return None, None, err
    body_rotation_y, err = transform_fns["_parse_rotation_y"](params)
    if err:
        return None, None, err
    return body_offset, body_rotation_y, None


def _parse_max_distance(params: dict):
    try:
        max_distance_m = float(params.get("max_distance_m", 2000))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "max_distance_m must be a number"}), 400)
    if max_distance_m <= 0 or max_distance_m > 50_000:
        return None, (jsonify({"error": "max_distance_m must be between 0 and 50000"}), 400)
    return max_distance_m, None


def _filter_by_indices(basestations: list, indices):
    if indices is None:
        return basestations, None
    if not isinstance(indices, list):
        return None, (jsonify({"error": "'indices' must be a list of integers"}), 400)
    try:
        indices = [int(i) for i in indices]
    except (TypeError, ValueError):
        return None, (jsonify({"error": "'indices' must contain only integers"}), 400)
    return [basestations[i] for i in indices if 0 <= i < len(basestations)], None


def _eirp_weighted_freq(selected: list, freq_hz_override) -> float:
    if freq_hz_override is not None:
        return float(freq_hz_override)
    total_eirp_w = sum(10 ** ((bs.eirp_dbm - 30) / 10) for bs in selected)
    if total_eirp_w > 0:
        return float(sum(bs.freq_hz * 10 ** ((bs.eirp_dbm - 30) / 10) for bs in selected) / total_eirp_w)
    return 3.5e9


def _zero_power_response(body, n_basestations: int, json_dumps_safe) -> RouteResponse:
    n_tri = body.n_triangles
    sab_bytes = np.zeros(n_tri, dtype=np.float32).tobytes()
    stats = {
        "p_abs": 0,
        "p_abs_mw": 0,
        "peak_sab": 0,
        "n_illuminated": 0,
        "n_triangles": n_tri,
        "n_basestations": n_basestations,
        "n_paths": 0,
        "arrays": [{"key": "sab", "offset": 0, "length": n_tri}],
        "peaks": {"sab": 0.0},
    }
    resp = Response(sab_bytes, mimetype=_OCTET_STREAM)
    resp.headers["X-Stats"] = json_dumps_safe(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp


def _build_exposure_configs(selected: list):
    from aegis.basestation.classify import classify_basestation

    return [
        classify_basestation(
            gain_dbi=bs.gain_dbi,
            technology=bs.technology,
            freq_mhz=bs.freq_mhz,
            h_bw=bs.horizontal_beamwidth_deg or 0,
            v_bw=bs.vertical_beamwidth_deg or 0,
        )["exposure_config"]
        for bs in selected
    ]


def _handle_basestations_compute(cache: dict, cache_lock: threading.RLock):
    """Implementation for POST /api/basestations/compute."""
    from aegis.basestation.adapter import paths_from_basestations
    from aegis.basestation.power import ExposureMode
    from aegis.engine import DosimetryEngine
    from aegis.viewer.compute import _transform_body_for_viewer, resolve_skin_model
    from aegis.viewer.routes.compute import (
        _build_binary_response,
        _build_stats_response,
        _inject_curvature_H,
        _json_dumps_safe,
        _parse_rotation_y,
        _parse_vec3,
    )

    params, err = get_json_dict()
    if err is not None:
        return err

    with cache_lock:
        basestations = scoped_cache_get(cache, "basestations", [])
        origin = scoped_cache_get(cache, "basestations_origin")
        body_name = params.get("body_name", cache.get("default_body"))
        entry = cache.get("bodies", {}).get(body_name)

    if not basestations:
        return jsonify({"error": "No base stations loaded"}), 400
    if entry is None:
        return jsonify({"error": f"Body '{body_name}' not found"}), 404
    body = entry["body"]
    if origin is None:
        return jsonify({"error": "No scene origin set"}), 400

    selected, err = _filter_by_indices(basestations, params.get("indices"))
    if err is not None:
        return err
    if not selected:
        return jsonify({"error": "No base stations selected"}), 400

    transform_fns = {"_parse_vec3": _parse_vec3, "_parse_rotation_y": _parse_rotation_y}
    body_offset, body_rotation_y, err = _parse_body_transform(params, transform_fns)
    if err is not None:
        return err
    assert body_offset is not None  # noqa: S101 - helper contract
    assert body_rotation_y is not None  # noqa: S101 - helper contract

    transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)
    body_center = np.mean(transformed_body.centroids, axis=0)

    exposure_mode_str = params.get("exposure_mode", "theoretical")
    try:
        exposure_mode = ExposureMode(exposure_mode_str)
    except ValueError:
        return jsonify({"error": f"Invalid exposure_mode: {exposure_mode_str!r}"}), 400

    max_distance_m, err = _parse_max_distance(params)
    if err is not None:
        return err
    assert max_distance_m is not None  # noqa: S101 - helper contract

    paths = paths_from_basestations(
        selected,
        body_center,
        origin,
        max_distance_m=max_distance_m,
        exposure_mode=exposure_mode,
        exposure_configs=_build_exposure_configs(selected),
    )

    if paths.n_paths == 0 or paths.total_power <= 0:
        return _zero_power_response(body, len(selected), _json_dumps_safe)

    freq_hz = _eirp_weighted_freq(selected, params.get("freq_hz"))
    skin_model = params.get("skin_model", "itis")
    tissue = resolve_skin_model(skin_model, freq_hz)

    mode = params.get("mode", "spatial")
    if mode not in _VALID_MODES:
        return jsonify({"error": f"mode must be one of: {', '.join(sorted(_VALID_MODES))}"}), 400
    engine = DosimetryEngine(tissue)
    engine_kw = _inject_curvature_H({"mode": mode, "spatial_averaging": True}, transformed_body)

    try:
        result = engine.compute(transformed_body, paths, **engine_kw)
    except Exception as exc:
        logger.exception("Basestations dosimetry compute failed")
        return jsonify({"error": f"Dosimetry compute failed: {exc}"}), 500

    quantities = params.get("quantities", ["sab", "sab_4cm2"])
    buf, arrays_meta = _build_binary_response(result, quantities)

    stats = _build_stats_response(
        result,
        transformed_body,
        tissue,
        None,
        mode=mode,
        corrections=[],
        extra={
            "n_basestations": len(selected),
            "n_paths": paths.n_paths,
            "freq_hz": freq_hz,
            "total_power_w_m2": float(paths.total_power),
            "arrays": arrays_meta,
        },
    )

    resp = Response(bytes(buf), mimetype=_OCTET_STREAM)
    resp.headers["X-Stats"] = _json_dumps_safe(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp
