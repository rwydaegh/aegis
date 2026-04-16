"""Main /api/compute dosimetry route, GPU status, and S_inc validation."""

from __future__ import annotations

import json
import logging
import os

import numpy as np
from flask import Response, jsonify, request

from aegis.defaults import DEFAULT_FREQ_HZ

from ._parsing import (
    _parse_bool,
    _parse_freq_and_tissue,
    _parse_quantities_and_scenario,
    _parse_rotation_y,
    _parse_vec3,
)
from ._responses import (
    _MAX_POWER_DBM,
    _OCTET_STREAM,
    _build_binary_response,
    _build_stats_response,
    _cache_dosimetry_for_export,
    _json_dumps_safe,
)

logger = logging.getLogger(__name__)


def _handle_validate_sinc(cache: dict, cache_lock) -> Response:
    """Implementation for POST /api/validate/sinc."""
    api_key = os.environ.get("CLOUDRF_API_KEY")
    if not api_key:
        return jsonify({"error": "CLOUDRF_API_KEY not configured"}), 501

    body = request.get_json(silent=True) or {}
    try:
        tx_lat = float(body["tx_lat"])
        tx_lon = float(body["tx_lon"])
        tx_alt = float(body["tx_alt"])
        rx_lat = float(body["rx_lat"])
        rx_lon = float(body["rx_lon"])
        rx_alt = float(body["rx_alt"])
        freq_mhz = float(body["freq_mhz"])
        power_w = float(body["power_w"])
        gain_dbi = float(body["gain_dbi"])
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"error": f"Missing or invalid parameter: {exc}"}), 400

    R = 6_371_000.0
    dlat = np.radians(rx_lat - tx_lat)
    dlon = np.radians(rx_lon - tx_lon)
    dist = R * np.sqrt(dlat**2 + (dlon * np.cos(np.radians(tx_lat))) ** 2)
    dist = max(dist, 0.1)
    dist_3d = np.sqrt(dist**2 + (tx_alt - rx_alt) ** 2)
    eirp_w = power_w * 10 ** (gain_dbi / 10)
    sinc_wm2 = eirp_w / (4 * np.pi * dist_3d**2)
    sinc_dbm = 10 * np.log10(sinc_wm2 * 1000) if sinc_wm2 > 0 else -200.0

    try:
        from aegis.integration.cloudrf import CloudRFClient

        path_result = CloudRFClient(api_key).path(
            tx_lat=tx_lat,
            tx_lon=tx_lon,
            tx_alt=tx_alt,
            rx_lat=rx_lat,
            rx_lon=rx_lon,
            rx_alt=rx_alt,
            freq_mhz=freq_mhz,
            power_w=power_w,
            gain_dbi=gain_dbi,
        )
    except Exception as exc:
        return jsonify({"error": f"CloudRF API error: {exc}"}), 502

    cloudrf_sinc_dbm = float(path_result.get("rxPower", path_result.get("rx_power", -200)))
    delta_db = float(sinc_dbm - cloudrf_sinc_dbm)

    return jsonify(
        {
            "aegis_sinc_wm2": float(sinc_wm2),
            "aegis_sinc_dbm": float(sinc_dbm),
            "cloudrf_sinc_dbm": cloudrf_sinc_dbm,
            "delta_db": delta_db,
            "distance_m": float(dist_3d),
        }
    )


def _api_compute_impl(cache: dict, cache_lock) -> Response:
    """Compute dosimetry for given antenna position."""
    from aegis.viewer.compute import compute_dosimetry

    if request.content_type == _OCTET_STREAM:
        raw_params = request.headers.get("X-Compute-Params")
        if not raw_params:
            return jsonify({"error": "X-Compute-Params header required for inline mesh"}), 400
        try:
            params = json.loads(raw_params)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid JSON in X-Compute-Params header"}), 400
        if not isinstance(params, dict):
            return jsonify({"error": "X-Compute-Params must be a JSON object"}), 400
        n_tri = params.get("n_triangles")
        if n_tri is None or not isinstance(n_tri, int):
            return jsonify({"error": "n_triangles required in X-Compute-Params"}), 400
        if n_tri <= 0 or n_tri > 500_000:
            return jsonify({"error": "n_triangles must be between 1 and 500000"}), 400

        mesh_data = request.get_data()
        max_size = 5 * 1024 * 1024
        if len(mesh_data) > max_size:
            return jsonify({"error": f"Mesh binary exceeds {max_size} bytes"}), 413

        n_verts = n_tri * 3
        expected_size = n_verts * 3 * 4 * 2  # positions + normals, float32
        if len(mesh_data) != expected_size:
            return jsonify({"error": f"Expected {expected_size} bytes, got {len(mesh_data)}"}), 400

        from aegis.geometry.mesh import BodyMesh

        floats = np.frombuffer(mesh_data, dtype=np.float32)
        positions = floats[: n_verts * 3].reshape(n_tri, 3, 3)
        normals_flat = floats[n_verts * 3 :].reshape(n_verts, 3)
        normals = normals_flat[::3]  # take every 3rd (face normal repeated 3x per vertex)

        try:
            body = BodyMesh.from_arrays(positions, normals, name="inline_posed")
        except ValueError as exc:
            return jsonify({"error": f"Invalid mesh arrays: {exc}"}), 400

        with cache_lock:
            cfg = cache["config"]
    else:
        params = request.get_json(silent=True)
        if params is None:
            if request.data:
                return jsonify({"error": "Invalid JSON body"}), 400
            params = {}
        elif not isinstance(params, dict):
            return jsonify({"error": "JSON body must be an object"}), 400

        body_name = params.get("body_name", cache.get("default_body"))
        with cache_lock:
            entry = cache.get("bodies", {}).get(body_name)
            cfg = cache["config"]
        if entry is None:
            return jsonify({"error": f"Body '{body_name}' not found"}), 404
        body = entry["body"]

    dcfg = cfg["dosimetry"]
    pwr_cfg = dcfg["power_input"]

    # Accept mode + correction flags (new API) or level (legacy)
    mode = params.get("mode")
    if mode is not None:
        if mode not in ("bound", "aggregate", "spatial"):
            return jsonify({"error": "mode must be one of: bound, aggregate, spatial"}), 400
        if mode == "spatial":
            corrections = {
                "fresnel": _parse_bool(params.get("fresnel"), True),
                "polarisation": _parse_bool(params.get("polarisation"), False),
                "curvature": _parse_bool(params.get("curvature"), False),
                "diffraction": _parse_bool(params.get("diffraction"), False),
            }
        else:
            corrections = None
        level = None
    else:
        try:
            level = int(params.get("level", dcfg["default_level"]))
        except (TypeError, ValueError):
            return jsonify({"error": "level must be an integer"}), 400
        if level not in range(0, 9):
            return jsonify({"error": "level must be between 0 and 8"}), 400
        mode = None
        corrections = None

    try:
        power_dbm = float(params.get("power_dbm", dcfg["default_power_dbm"]))
    except (TypeError, ValueError):
        return jsonify({"error": "power_dbm must be a number"}), 400
    effective_max = min(pwr_cfg["max"], _MAX_POWER_DBM)
    if power_dbm < pwr_cfg["min"] or power_dbm > effective_max:
        return jsonify({"error": f"power_dbm must be between {pwr_cfg['min']} and {effective_max} dBm"}), 400

    # Stochastic channel params
    stochastic = None
    if params.get("stochastic"):
        stoch_cfg = cfg["dosimetry"].get("stochastic", {})
        try:
            stochastic = {
                "preset": params.get("stochastic_preset", stoch_cfg.get("default_preset", "3GPP_38.901_UMi_LOS")),
                "seed": int(params.get("stochastic_seed", stoch_cfg.get("default_seed", 42))),
                "overrides": params.get("stochastic_overrides", {}),
                "freq_ghz": float(params.get("freq_hz", DEFAULT_FREQ_HZ)) / 1e9,
            }
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid stochastic parameters (seed must be integer)"}), 400

    tissue, _, err = _parse_freq_and_tissue(params)
    if err:
        return err

    antenna_pos, err = _parse_vec3(params, "antenna_pos", [5, 0, 1])
    if err:
        return err
    body_offset, err = _parse_vec3(params, "body_offset")
    if err:
        return err
    body_rotation_y, err = _parse_rotation_y(params)
    if err:
        return err
    quantities, exposure_scenario, err = _parse_quantities_and_scenario(params)
    if err:
        return err

    exposure_mode = params.get("exposure_mode", "theoretical")

    # Parse multi-antenna array (new API)
    antennas = None
    raw_antennas = params.get("antennas")
    if raw_antennas is not None:
        if not isinstance(raw_antennas, list):
            return jsonify({"error": "antennas must be a list"}), 400
        antennas = []
        for i, raw_ant in enumerate(raw_antennas):
            if not isinstance(raw_ant, dict):
                return jsonify({"error": f"antennas[{i}] must be an object"}), 400
            ant_pos, err = _parse_vec3(raw_ant, "position", [5, 0, 1])
            if err:
                return err
            ant_power = float(raw_ant.get("power_dbm", power_dbm))
            acfg = raw_ant.get("array_config", {})
            antennas.append(
                {
                    "position": ant_pos.tolist(),
                    "power_dbm": ant_power,
                    "array_config": acfg,
                }
            )

    import time as _time

    t_route = _time.perf_counter()

    try:
        result, res_body, res_tissue, res_level, res_mode, res_corr, extra = compute_dosimetry(
            body,
            antenna_pos=antenna_pos,
            body_offset=body_offset,
            body_rotation_y=body_rotation_y,
            level=level,
            mode=mode,
            corrections=corrections,
            tissue=tissue,
            power_dbm=power_dbm,
            config=cfg,
            stochastic=stochastic,
            antennas=antennas,
            exposure_mode=exposure_mode,
        )
    except Exception as exc:
        logger.exception("compute_dosimetry failed")
        return jsonify({"error": str(exc)}), 500

    t_compute = _time.perf_counter()

    try:
        # Build multi-array binary response and stats header
        buf, arrays_meta = _build_binary_response(result, quantities)
        stats = _build_stats_response(
            result,
            res_body,
            res_tissue,
            res_level,
            mode=res_mode,
            corrections=res_corr,
            extra=extra,
            scenario=exposure_scenario,
        )
    except Exception as exc:
        logger.exception("response build failed")
        return jsonify({"error": str(exc)}), 500

    t_stats = _time.perf_counter()

    # Cache result and body for export and compliance summary
    _cache_dosimetry_for_export(cache, result, res_body, stats)

    # Inject route-level timings
    timings = extra.get("timings", {})
    timings["compliance_stats_ms"] = (t_stats - t_compute) * 1e3
    timings["route_total_ms"] = (t_stats - t_route) * 1e3
    stats["timings"] = timings
    stats["arrays"] = arrays_meta

    resp = Response(bytes(buf), mimetype=_OCTET_STREAM)
    resp.headers["X-Stats"] = _json_dumps_safe(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp


def _api_gpu_status_impl(cache: dict, cache_lock) -> Response:
    """Return GPU container warmth status."""
    from aegis.viewer.modal_proxy import gpu_status

    return jsonify(gpu_status())
