"""Main /api/compute dosimetry route, GPU status, and S_inc validation."""

from __future__ import annotations

import json
import logging
import math
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

_MAX_INLINE_MESH_BYTES = 5 * 1024 * 1024


def _validate_sinc_request(body: dict):
    """Extract and validate parameters for /api/validate/sinc.

    Returns (params_dict, None) on success or (None, error_response) on failure.
    """
    try:
        params = {
            "tx_lat": float(body["tx_lat"]),
            "tx_lon": float(body["tx_lon"]),
            "tx_alt": float(body["tx_alt"]),
            "rx_lat": float(body["rx_lat"]),
            "rx_lon": float(body["rx_lon"]),
            "rx_alt": float(body["rx_alt"]),
            "freq_mhz": float(body["freq_mhz"]),
            "power_w": float(body["power_w"]),
            "gain_dbi": float(body["gain_dbi"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        return None, (jsonify({"error": f"Missing or invalid parameter: {exc}"}), 400)
    return params, None


def _compute_aegis_sinc(p: dict) -> tuple[float, float, float]:
    """Compute the free-space incident power density (W/m^2, dBm) and 3D distance."""
    R = 6_371_000.0
    dlat = np.radians(p["rx_lat"] - p["tx_lat"])
    dlon = np.radians(p["rx_lon"] - p["tx_lon"])
    dist = R * np.sqrt(dlat**2 + (dlon * np.cos(np.radians(p["tx_lat"]))) ** 2)
    dist = max(dist, 0.1)
    dist_3d = np.sqrt(dist**2 + (p["tx_alt"] - p["rx_alt"]) ** 2)
    eirp_w = p["power_w"] * 10 ** (p["gain_dbi"] / 10)
    sinc_wm2 = eirp_w / (4 * np.pi * dist_3d**2)
    sinc_dbm = 10 * np.log10(sinc_wm2 * 1000) if sinc_wm2 > 0 else -200.0
    return float(sinc_wm2), float(sinc_dbm), float(dist_3d)


def _fetch_cloudrf_sinc(api_key: str, p: dict):
    """Fetch CloudRF link budget. Returns (rx_dbm, None) or (None, error_response)."""
    try:
        from aegis.integration.cloudrf import CloudRFClient

        path_result = CloudRFClient(api_key).path(
            tx_lat=p["tx_lat"],
            tx_lon=p["tx_lon"],
            tx_alt=p["tx_alt"],
            rx_lat=p["rx_lat"],
            rx_lon=p["rx_lon"],
            rx_alt=p["rx_alt"],
            freq_mhz=p["freq_mhz"],
            power_w=p["power_w"],
            gain_dbi=p["gain_dbi"],
        )
    except Exception as exc:
        return None, (jsonify({"error": f"CloudRF API error: {exc}"}), 502)
    return float(path_result.get("rxPower", path_result.get("rx_power", -200))), None


def _handle_validate_sinc(cache: dict, cache_lock) -> Response:
    """Implementation for POST /api/validate/sinc."""
    api_key = os.environ.get("CLOUDRF_API_KEY")
    if not api_key:
        return jsonify({"error": "CLOUDRF_API_KEY not configured"}), 501

    body = request.get_json(silent=True) or {}
    p, err = _validate_sinc_request(body)
    if err is not None:
        return err

    sinc_wm2, sinc_dbm, dist_3d = _compute_aegis_sinc(p)

    cloudrf_sinc_dbm, err = _fetch_cloudrf_sinc(api_key, p)
    if err is not None:
        return err

    return jsonify(
        {
            "aegis_sinc_wm2": sinc_wm2,
            "aegis_sinc_dbm": sinc_dbm,
            "cloudrf_sinc_dbm": cloudrf_sinc_dbm,
            "delta_db": float(sinc_dbm - cloudrf_sinc_dbm),
            "distance_m": dist_3d,
        }
    )


def _load_inline_mesh_body(cache: dict, cache_lock):
    """Parse the inline-mesh upload body for /api/compute.

    Returns (body, params, cfg, None) on success or (None, None, None, error_response)
    on failure.
    """
    raw_params = request.headers.get("X-Compute-Params")
    if not raw_params:
        return None, None, None, (jsonify({"error": "X-Compute-Params header required for inline mesh"}), 400)
    try:
        params = json.loads(raw_params)
    except (ValueError, TypeError):
        return None, None, None, (jsonify({"error": "Invalid JSON in X-Compute-Params header"}), 400)
    if not isinstance(params, dict):
        return None, None, None, (jsonify({"error": "X-Compute-Params must be a JSON object"}), 400)
    n_tri = params.get("n_triangles")
    if n_tri is None or not isinstance(n_tri, int):
        return None, None, None, (jsonify({"error": "n_triangles required in X-Compute-Params"}), 400)
    if n_tri <= 0 or n_tri > 500_000:
        return None, None, None, (jsonify({"error": "n_triangles must be between 1 and 500000"}), 400)

    mesh_data = request.get_data()
    if len(mesh_data) > _MAX_INLINE_MESH_BYTES:
        return None, None, None, (jsonify({"error": f"Mesh binary exceeds {_MAX_INLINE_MESH_BYTES} bytes"}), 413)

    n_verts = n_tri * 3
    expected_size = n_verts * 3 * 4 * 2  # positions + normals, float32
    if len(mesh_data) != expected_size:
        return (
            None,
            None,
            None,
            (jsonify({"error": f"Expected {expected_size} bytes, got {len(mesh_data)}"}), 400),
        )

    from aegis.geometry.mesh import BodyMesh

    floats = np.frombuffer(mesh_data, dtype=np.float32)
    positions = floats[: n_verts * 3].reshape(n_tri, 3, 3)
    normals_flat = floats[n_verts * 3 :].reshape(n_verts, 3)
    normals = normals_flat[::3]  # take every 3rd (face normal repeated 3x per vertex)

    try:
        body = BodyMesh.from_arrays(positions, normals, name="inline_posed")
    except ValueError as exc:
        return None, None, None, (jsonify({"error": f"Invalid mesh arrays: {exc}"}), 400)

    with cache_lock:
        cfg = cache["config"]
    return body, params, cfg, None


def _load_cached_body(cache: dict, cache_lock):
    """Parse the JSON body for /api/compute and resolve the cached body mesh.

    Returns (body, params, cfg, None) on success or (None, None, None, error_response)
    on failure.
    """
    params = request.get_json(silent=True)
    if params is None:
        if request.data:
            return None, None, None, (jsonify({"error": "Invalid JSON body"}), 400)
        params = {}
    elif not isinstance(params, dict):
        return None, None, None, (jsonify({"error": "JSON body must be an object"}), 400)

    body_name = params.get("body_name", cache.get("default_body"))
    with cache_lock:
        entry = cache.get("bodies", {}).get(body_name)
        cfg = cache["config"]
    if entry is None:
        return None, None, None, (jsonify({"error": f"Body '{body_name}' not found"}), 404)
    return entry["body"], params, cfg, None


def _resolve_body_and_params(cache: dict, cache_lock):
    """Dispatch based on content-type to load the body mesh + JSON params."""
    if request.content_type == _OCTET_STREAM:
        return _load_inline_mesh_body(cache, cache_lock)
    return _load_cached_body(cache, cache_lock)


def _parse_mode_level_corrections(params: dict, dcfg: dict):
    """Parse mode+corrections (new API) or legacy level from params.

    Returns (level, mode, corrections, None) on success or
    (None, None, None, error_response) on failure.
    """
    mode = params.get("mode")
    if mode is not None:
        if mode not in ("bound", "aggregate", "spatial"):
            return None, None, None, (jsonify({"error": "mode must be one of: bound, aggregate, spatial"}), 400)
        if mode == "spatial":
            corrections = {
                "fresnel": _parse_bool(params.get("fresnel"), True),
                "polarisation": _parse_bool(params.get("polarisation"), False),
                "curvature": _parse_bool(params.get("curvature"), False),
                "diffraction": _parse_bool(params.get("diffraction"), False),
            }
        else:
            corrections = None
        return None, mode, corrections, None
    try:
        level = int(params.get("level", dcfg["default_level"]))
    except (TypeError, ValueError):
        return None, None, None, (jsonify({"error": "level must be an integer"}), 400)
    if level not in range(0, 9):
        return None, None, None, (jsonify({"error": "level must be between 0 and 8"}), 400)
    return level, None, None, None


def _parse_power_dbm(params: dict, dcfg: dict, pwr_cfg: dict):
    """Parse and validate power_dbm. Returns (float, None) or (None, error_response)."""
    try:
        power_dbm = float(params.get("power_dbm", dcfg["default_power_dbm"]))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "power_dbm must be a number"}), 400)
    if not math.isfinite(power_dbm):
        return None, (jsonify({"error": "power_dbm must be a finite number"}), 400)
    effective_max = min(pwr_cfg["max"], _MAX_POWER_DBM)
    if power_dbm < pwr_cfg["min"] or power_dbm > effective_max:
        return None, (jsonify({"error": f"power_dbm must be between {pwr_cfg['min']} and {effective_max} dBm"}), 400)
    return power_dbm, None


def _parse_stochastic_params(params: dict, cfg: dict):
    """Parse stochastic channel params (if requested).

    Returns (stochastic_dict_or_None, None) or (None, error_response) on failure.
    """
    if not params.get("stochastic"):
        return None, None
    stoch_cfg = cfg["dosimetry"].get("stochastic", {})
    try:
        stochastic = {
            "preset": params.get("stochastic_preset", stoch_cfg.get("default_preset", "3GPP_38.901_UMi_LOS")),
            "seed": int(params.get("stochastic_seed", stoch_cfg.get("default_seed", 42))),
            "overrides": params.get("stochastic_overrides", {}),
            "freq_ghz": float(params.get("freq_hz", DEFAULT_FREQ_HZ)) / 1e9,
        }
    except (TypeError, ValueError):
        return None, (jsonify({"error": "Invalid stochastic parameters (seed must be integer)"}), 400)
    return stochastic, None


def _parse_antennas_array(params: dict, default_power_dbm: float):
    """Parse the optional multi-antenna array.

    Returns (list_or_None, None) on success or (None, error_response) on failure.
    """
    raw_antennas = params.get("antennas")
    if raw_antennas is None:
        return None, None
    if not isinstance(raw_antennas, list):
        return None, (jsonify({"error": "antennas must be a list"}), 400)
    antennas: list[dict] = []
    for i, raw_ant in enumerate(raw_antennas):
        if not isinstance(raw_ant, dict):
            return None, (jsonify({"error": f"antennas[{i}] must be an object"}), 400)
        ant_pos, err = _parse_vec3(raw_ant, "position", [5, 0, 1])
        if err:
            return None, err
        try:
            ant_power = float(raw_ant.get("power_dbm", default_power_dbm))
        except (TypeError, ValueError):
            return None, (jsonify({"error": f"antennas[{i}].power_dbm must be a number"}), 400)
        if not math.isfinite(ant_power):
            return None, (jsonify({"error": f"antennas[{i}].power_dbm must be a finite number"}), 400)
        acfg = raw_ant.get("array_config", {})
        if not isinstance(acfg, dict):
            return None, (jsonify({"error": f"antennas[{i}].array_config must be an object"}), 400)
        antennas.append(
            {
                "position": ant_pos.tolist(),
                "power_dbm": ant_power,
                "array_config": acfg,
            }
        )
    return antennas, None


def _collect_compute_params(params: dict, cfg: dict):
    """Parse all request parameters for /api/compute.

    Returns (parsed_dict, None) on success or (None, error_response) on failure.
    """
    dcfg = cfg["dosimetry"]
    pwr_cfg = dcfg["power_input"]

    level, mode, corrections, err = _parse_mode_level_corrections(params, dcfg)
    if err is not None:
        return None, err

    power_dbm, err = _parse_power_dbm(params, dcfg, pwr_cfg)
    if err is not None:
        return None, err

    stochastic, err = _parse_stochastic_params(params, cfg)
    if err is not None:
        return None, err

    tissue, _, err = _parse_freq_and_tissue(params)
    if err:
        return None, err

    antenna_pos, err = _parse_vec3(params, "antenna_pos", [5, 0, 1])
    if err:
        return None, err
    body_offset, err = _parse_vec3(params, "body_offset")
    if err:
        return None, err
    body_rotation_y, err = _parse_rotation_y(params)
    if err:
        return None, err
    quantities, exposure_scenario, err = _parse_quantities_and_scenario(params)
    if err:
        return None, err

    antennas, err = _parse_antennas_array(params, power_dbm)
    if err is not None:
        return None, err

    return {
        "level": level,
        "mode": mode,
        "corrections": corrections,
        "power_dbm": power_dbm,
        "stochastic": stochastic,
        "tissue": tissue,
        "antenna_pos": antenna_pos,
        "body_offset": body_offset,
        "body_rotation_y": body_rotation_y,
        "quantities": quantities,
        "exposure_scenario": exposure_scenario,
        "antennas": antennas,
        "exposure_mode": params.get("exposure_mode", "theoretical"),
    }, None


def _build_compute_response(result, res_body, res_tissue, res_level, res_mode, res_corr, extra, pp):
    """Build the final binary + X-Stats response.

    Returns (response, stats, None) on success or (None, None, error_response) on failure.
    The caller is expected to mutate ``stats["timings"]`` after this returns.
    """
    try:
        buf, arrays_meta = _build_binary_response(result, pp["quantities"])
        stats = _build_stats_response(
            result,
            res_body,
            res_tissue,
            res_level,
            mode=res_mode,
            corrections=res_corr,
            extra=extra,
            scenario=pp["exposure_scenario"],
        )
    except Exception as exc:
        logger.exception("response build failed")
        return None, None, (jsonify({"error": str(exc)}), 500)

    stats["timings"] = extra.get("timings", {})
    stats["arrays"] = arrays_meta

    resp = Response(bytes(buf), mimetype=_OCTET_STREAM)
    resp.headers["X-Stats"] = _json_dumps_safe(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp, stats, None


def _api_compute_impl(cache: dict, cache_lock) -> Response:
    """Compute dosimetry for given antenna position."""
    from aegis.viewer.compute import compute_dosimetry

    body, params, cfg, err = _resolve_body_and_params(cache, cache_lock)
    if err is not None:
        return err

    pp, err = _collect_compute_params(params, cfg)
    if err is not None:
        return err

    import time as _time

    t_route = _time.perf_counter()

    try:
        result, res_body, res_tissue, res_level, res_mode, res_corr, extra = compute_dosimetry(
            body,
            antenna_pos=pp["antenna_pos"],
            body_offset=pp["body_offset"],
            body_rotation_y=pp["body_rotation_y"],
            level=pp["level"],
            mode=pp["mode"],
            corrections=pp["corrections"],
            tissue=pp["tissue"],
            power_dbm=pp["power_dbm"],
            config=cfg,
            stochastic=pp["stochastic"],
            antennas=pp["antennas"],
            exposure_mode=pp["exposure_mode"],
        )
    except Exception as exc:
        logger.exception("compute_dosimetry failed")
        return jsonify({"error": str(exc)}), 500

    t_compute = _time.perf_counter()

    resp, stats, err = _build_compute_response(result, res_body, res_tissue, res_level, res_mode, res_corr, extra, pp)
    if err is not None:
        return err

    t_stats = _time.perf_counter()

    _cache_dosimetry_for_export(cache, result, res_body, stats)

    # Inject route-level timings into the X-Stats header in place
    stats["timings"]["compliance_stats_ms"] = (t_stats - t_compute) * 1e3
    stats["timings"]["route_total_ms"] = (t_stats - t_route) * 1e3
    resp.headers["X-Stats"] = _json_dumps_safe(stats)
    return resp


def _api_gpu_status_impl(cache: dict, cache_lock) -> Response:
    """Return GPU container warmth status."""
    from aegis.viewer.modal_proxy import gpu_status

    return jsonify(gpu_status())
