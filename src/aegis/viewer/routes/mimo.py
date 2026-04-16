"""MIMO API routes: compute, per-user result, and summary."""

from __future__ import annotations

import logging

import numpy as np
from flask import Flask, Response, jsonify, request

from aegis.compliance import ExposureScenario, evaluate_compliance
from aegis.constants import C_0
from aegis.defaults import DEFAULT_FREQ_HZ
from aegis.mimo.array import AntennaArray
from aegis.mimo.compute import compute_mimo_scene_with_bodies
from aegis.mimo.scene import MIMOScene
from aegis.mimo.user import UserConfig, UserState
from aegis.viewer.routes.compute import _json_dumps_safe
from aegis.viewer.server import scoped_cache_get, scoped_cache_set

logger = logging.getLogger(__name__)

_OCTET_STREAM = "application/octet-stream"
_ERR_VEC3_LEN = "must have 3 elements"


def _parse_vec3(raw, label: str):
    """Parse a 3-element numeric array.

    Returns (np.ndarray, None) on success or (None, error_response) on failure.
    """
    try:
        arr = np.array(raw, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        return None, (jsonify({"error": f"Invalid {label}: {exc}"}), 400)
    if arr.shape != (3,):
        return None, (jsonify({"error": f"{label} {_ERR_VEC3_LEN}, got {arr.shape}"}), 400)
    return arr, None


def _validate_users_cfg(users_cfg):
    """Validate the users list config.

    Returns None on success or an error response tuple on failure.
    """
    if not users_cfg:
        return jsonify({"error": "Missing or empty 'users' in request"}), 400
    if not isinstance(users_cfg, list):
        return jsonify({"error": "'users' must be an array"}), 400
    user_ids = [u.get("id") for u in users_cfg if "id" in u]
    if len(user_ids) != len(set(user_ids)):
        dupes = [uid for uid in set(user_ids) if user_ids.count(uid) > 1]
        return jsonify({"error": f"Duplicate user IDs: {dupes}"}), 400
    return None


def _parse_scene_scalars(params: dict):
    """Parse freq_hz, power_dbm and compute derived wavelength/total_power.

    Returns ({freq_hz, wavelength, total_power}, None) on success
    or (None, error_response) on failure.
    """
    try:
        freq_hz = float(params.get("freq_hz", DEFAULT_FREQ_HZ))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "freq_hz must be a number"}), 400)
    if freq_hz <= 0:
        return None, (jsonify({"error": "freq_hz must be positive"}), 400)
    if freq_hz > 300e9:
        return None, (jsonify({"error": "freq_hz exceeds 300 GHz maximum"}), 400)
    try:
        power_dbm = float(params.get("power_dbm", 30.0))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "power_dbm must be a number"}), 400)
    return (
        {
            "freq_hz": freq_hz,
            "wavelength": C_0 / freq_hz,
            "total_power": 10 ** ((power_dbm - 30) / 10),
        },
        None,
    )


def _build_antenna_array(array_cfg: dict, wavelength: float):
    """Build the AntennaArray from request config.

    Returns (array, None) on success or (None, error_response) on failure.
    """
    try:
        n_h = int(array_cfg["n_h"])
        n_v = int(array_cfg["n_v"])
    except (KeyError, TypeError, ValueError) as exc:
        return None, (jsonify({"error": f"Invalid array dimensions: {exc}"}), 400)
    if n_h < 1 or n_v < 1:
        return None, (jsonify({"error": "Array dimensions n_h and n_v must be >= 1"}), 400)
    if n_h * n_v > 1024:
        return None, (
            jsonify({"error": f"Array too large: {n_h}x{n_v} = {n_h * n_v} elements (max 1024)"}),
            400,
        )

    try:
        d_h_wl = float(array_cfg.get("d_h_wavelengths", 0.5))
        d_v_wl = float(array_cfg.get("d_v_wavelengths", 0.5))
    except (TypeError, ValueError) as exc:
        return None, (jsonify({"error": f"Invalid element spacing: {exc}"}), 400)
    if d_h_wl <= 0 or d_v_wl <= 0:
        return None, (jsonify({"error": "Element spacing must be positive"}), 400)

    try:
        raw_position = array_cfg["position"]
        raw_broadside = array_cfg["broadside"]
    except KeyError as exc:
        return None, (jsonify({"error": f"Invalid array position/broadside: {exc}"}), 400)
    position, err = _parse_vec3(raw_position, "array position")
    if err is not None:
        return None, err
    broadside, err = _parse_vec3(raw_broadside, "array broadside")
    if err is not None:
        return None, err

    try:
        array = AntennaArray.upa(
            n_h=n_h,
            n_v=n_v,
            d_h=d_h_wl * wavelength,
            d_v=d_v_wl * wavelength,
            center=position,
            broadside=broadside,
            element_pattern=str(array_cfg.get("element_pattern", "patch")),
        )
    except (KeyError, ValueError) as exc:
        return None, (jsonify({"error": f"Invalid array config: {exc}"}), 400)
    return array, None


def _build_user_state(u: dict, cache: dict):
    """Build a single UserState from a user config dict.

    Returns (UserState, None) on success or (None, error_response) on failure.
    """
    bodies_cache = cache.get("bodies", {})
    phantom = u.get("phantom", cache.get("default_body", "thelonious"))
    if phantom not in bodies_cache:
        return None, (jsonify({"error": f"Unknown phantom: {phantom!r}"}), 404)

    uid_label = u.get("id", "?")
    user_pos, err = _parse_vec3(u.get("position", [0.0, 0.0, 0.0]), f"user position for '{uid_label}'")
    if err is not None:
        return None, err

    default_offset = cache.get("body_device_offsets", {}).get(phantom, [0.0, 0.30, 1.4])
    raw_offset = u.get("device_offset") or u.get("device_position") or default_offset
    device_offset, err = _parse_vec3(raw_offset, f"device offset for '{uid_label}'")
    if err is not None:
        return None, err

    orientation = float(u.get("orientation", 0.0))
    cos_o, sin_o = np.cos(orientation), np.sin(orientation)
    rotated_offset = np.array(
        [
            cos_o * device_offset[0] - sin_o * device_offset[1],
            sin_o * device_offset[0] + cos_o * device_offset[1],
            device_offset[2],
        ]
    )
    device_position = user_pos + rotated_offset

    device_orientation, err = _parse_vec3(u.get("device_orientation", [0.0, 0.0, 1.0]), "device orientation")
    if err is not None:
        return None, err

    try:
        cfg = UserConfig(
            user_id=u["id"],
            phantom_name=phantom,
            position=user_pos,
            device_position=np.asarray(device_position, dtype=np.float64),
            device_orientation=device_orientation,
            orientation=orientation,
        )
    except (KeyError, ValueError) as exc:
        return None, (jsonify({"error": f"Invalid user config: {exc}"}), 400)

    return UserState(config=cfg), None


def _build_scene(params: dict, cache: dict) -> tuple[MIMOScene | None, Response | None]:
    """Build a MIMOScene from request params. Returns (scene, None) or (None, error_response)."""
    array_cfg = params.get("array")
    if not array_cfg:
        return None, (jsonify({"error": "Missing 'array' in request"}), 400)

    users_cfg = params.get("users")
    err = _validate_users_cfg(users_cfg)
    if err is not None:
        return None, err

    scalars, err = _parse_scene_scalars(params)
    if err is not None:
        return None, err

    array, err = _build_antenna_array(array_cfg, scalars["wavelength"])
    if err is not None:
        return None, err

    users = []
    for u in users_cfg:
        user_state, err = _build_user_state(u, cache)
        if err is not None:
            return None, err
        users.append(user_state)

    scene = MIMOScene(
        array=array,
        users=users,
        freq_hz=scalars["freq_hz"],
        total_power=scalars["total_power"],
    )
    return scene, None


def _sab_distribution(sab_arr: np.ndarray, body) -> dict:
    """Compute exposure distribution statistics from a sab array."""
    n_illum = int(np.sum(sab_arr > 0))
    sab_nonzero = sab_arr[sab_arr > 0]
    illuminated_area_cm2 = None
    if body is not None and hasattr(body, "areas") and body.areas is not None:
        illuminated_area_cm2 = float(np.sum(body.areas[sab_arr > 0]) * 1e4)
    return {
        "mean": float(np.mean(sab_arr)),
        "median": float(np.median(sab_arr)),
        "p95": float(np.percentile(sab_arr, 95)),
        "p99": float(np.percentile(sab_arr, 99)),
        "illuminated_fraction": n_illum / sab_arr.size,
        "illuminated_area_cm2": illuminated_area_cm2,
        "illuminated_mean": float(np.mean(sab_nonzero)) if sab_nonzero.size > 0 else 0.0,
        "illuminated_p50": float(np.median(sab_nonzero)) if sab_nonzero.size > 0 else 0.0,
    }


def _evaluate_user_compliance(result, body, freq_hz: float):
    """Evaluate ICNIRP compliance for a user, returning (compliance, scenario) or (None, scenario)."""
    scenario = ExposureScenario.GENERAL_PUBLIC
    ckw = result.compliance_kwargs(body=body)
    try:
        compliance = evaluate_compliance(scenario=scenario, freq_hz=freq_hz, **ckw)
    except (ValueError, TypeError):
        compliance = None
    return compliance, scenario


def _compliance_summary(compliance, scenario, freq_hz: float):
    """Serialize a compliance result into a JSON-friendly dict, or return None."""
    if compliance is None:
        return None
    margin_db = compliance.margin_db if compliance.margin_db != float("inf") else None
    return {
        "overall_pass": compliance.overall_pass,
        "margin_db": margin_db,
        "scenario": scenario.value,
        "freq_hz": freq_hz,
        "checks": [
            {
                "label": c.label,
                "value": round(c.value, 4),
                "limit": round(c.limit, 4),
                "unit": c.unit,
                "pass": c.compliant,
                "ratio": round(c.ratio, 4),
            }
            for c in compliance.all_checks
        ],
    }


def _user_stats(user: UserState, scene: MIMOScene) -> dict:
    """Build per-user stats dict from a computed UserState."""
    result = user.result
    body = user.body
    stats: dict = {
        "user_id": user.config.user_id,
        "phantom": user.config.phantom_name,
    }
    if result is None:
        return stats

    sab_arr = result.sab
    p_abs = float(result.p_abs)
    stats["p_abs"] = p_abs
    stats["p_abs_mw"] = p_abs * 1e3
    stats["peak_sab"] = float(result.peak_sab)
    stats["n_illuminated"] = int(np.sum(sab_arr > 0))
    stats["n_triangles"] = int(sab_arr.size)
    if body is not None:
        stats["n_triangles"] = body.n_triangles
    if hasattr(result, "sab_averaged") and result.sab_averaged is not None:
        stats["peak_sab_averaged"] = float(np.max(result.sab_averaged))

    if sab_arr.size > 0:
        stats["distribution"] = _sab_distribution(sab_arr, body)

    compliance, scenario = _evaluate_user_compliance(result, body, scene.freq_hz)
    stats["compliance"] = _compliance_summary(compliance, scenario, scene.freq_hz)
    stats["compliant"] = compliance.overall_pass if compliance is not None else None
    return stats


def _api_mimo_compute_impl(cache: dict, cache_lock) -> Response:
    params = request.get_json(silent=True) or {}

    scene, err = _build_scene(params, cache)
    if err is not None:
        return err

    # Resolve body meshes (only base bodies needed; compute translates them)
    bodies = {name: entry["body"] for name, entry in cache.get("bodies", {}).items()}

    try:
        level = int(params.get("level", 7))
    except (TypeError, ValueError):
        return jsonify({"error": "level must be an integer"}), 400
    if level not in (7, 8):
        return jsonify({"error": "level must be 7 or 8 for MIMO"}), 400
    precoder_type = str(params.get("precoder_type", "mrt"))
    try:
        summary = compute_mimo_scene_with_bodies(
            scene,
            bodies,
            level=level,
            precoder_type=precoder_type,
        )
    except Exception as exc:
        logger.exception("MIMO compute failed")
        return jsonify({"error": str(exc)}), 500

    # Cache scene and per-user results (session-scoped)
    with cache_lock:
        scoped_cache_set(cache, "mimo_scene", scene)
        scoped_cache_set(cache, "mimo_summary", summary)

        results_binary: dict[str, bytes] = {}
        results_stats: dict[str, dict] = {}
        for user in scene.users:
            uid = user.config.user_id
            if user._sab_raw is not None:
                results_binary[uid] = user._sab_raw.astype(np.float32).tobytes()
            stats = _user_stats(user, scene)
            results_stats[uid] = stats

        scoped_cache_set(cache, "mimo_results_binary", results_binary)
        scoped_cache_set(cache, "mimo_results_stats", results_stats)

    return jsonify(summary)


def _api_mimo_result_impl(user_id: str, cache: dict, cache_lock) -> Response:
    results_binary = scoped_cache_get(cache, "mimo_results_binary")
    if not results_binary or user_id not in results_binary:
        return jsonify({"error": f"No result for user {user_id!r}"}), 404

    data_bytes = results_binary[user_id]
    stats = (scoped_cache_get(cache, "mimo_results_stats") or {}).get(user_id, {})

    resp = Response(data_bytes, mimetype=_OCTET_STREAM)
    resp.headers["X-Stats"] = _json_dumps_safe(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp


def _api_mimo_summary_impl(cache: dict, cache_lock) -> Response:
    summary = scoped_cache_get(cache, "mimo_summary")
    scene = scoped_cache_get(cache, "mimo_scene")
    if summary is None or scene is None:
        return jsonify({"error": "No MIMO results computed yet"}), 404

    config = cache.get("config", {})
    exposure_budget_mw = float(config.get("mimo", {}).get("exposure_budget_mw", 100.0))

    users_out = []
    results_stats = scoped_cache_get(cache, "mimo_results_stats", {})
    for user in scene.users:
        uid = user.config.user_id
        stats = results_stats.get(uid, {})
        p_abs_mw = stats.get("p_abs_mw", 0.0)
        entry = {
            "id": uid,
            "phantom": user.config.phantom_name,
            "position": user.config.position.tolist(),
            "p_abs_mw": p_abs_mw,
            "peak_sab": stats.get("peak_sab", 0.0),
            "compliant": (stats["compliant"] if stats.get("compliant") is not None else p_abs_mw < exposure_budget_mw),
        }
        users_out.append(entry)

    out: dict = {
        "users": users_out,
        "precoder": summary.get("precoder_type", "mrt"),
        "timings": summary.get("timings", {}),
    }
    if summary.get("warning"):
        out["warning"] = summary["warning"]
    return jsonify(out)


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach MIMO routes to app."""

    @app.route("/api/mimo/compute", methods=["POST"])
    def api_mimo_compute():
        return _api_mimo_compute_impl(cache, cache_lock)

    @app.route("/api/mimo/result/<user_id>", methods=["GET"])
    def api_mimo_result(user_id: str):
        return _api_mimo_result_impl(user_id, cache, cache_lock)

    @app.route("/api/mimo/summary", methods=["GET"])
    def api_mimo_summary():
        return _api_mimo_summary_impl(cache, cache_lock)
