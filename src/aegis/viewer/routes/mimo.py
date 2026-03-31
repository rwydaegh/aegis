"""MIMO API routes: compute, per-user result, and summary."""

from __future__ import annotations

import logging

import numpy as np
from flask import Flask, Response, jsonify, request

from aegis.constants import C_0
from aegis.defaults import DEFAULT_FREQ_HZ
from aegis.mimo.array import AntennaArray
from aegis.mimo.compute import compute_mimo_scene_with_bodies
from aegis.mimo.scene import MIMOScene
from aegis.mimo.user import UserConfig, UserState
from aegis.viewer.routes.compute import _json_dumps_safe

logger = logging.getLogger(__name__)

_OCTET_STREAM = "application/octet-stream"


def _build_scene(params: dict, cache: dict) -> tuple[MIMOScene | None, Response | None]:
    """Build a MIMOScene from request params. Returns (scene, None) or (None, error_response)."""
    array_cfg = params.get("array")
    if not array_cfg:
        return None, (jsonify({"error": "Missing 'array' in request"}), 400)

    users_cfg = params.get("users")
    if not users_cfg:
        return None, (jsonify({"error": "Missing or empty 'users' in request"}), 400)

    user_ids = [u.get("id") for u in users_cfg if "id" in u]
    if len(user_ids) != len(set(user_ids)):
        dupes = [uid for uid in set(user_ids) if user_ids.count(uid) > 1]
        return None, (jsonify({"error": f"Duplicate user IDs: {dupes}"}), 400)

    freq_hz = float(params.get("freq_hz", DEFAULT_FREQ_HZ))
    power_dbm = float(params.get("power_dbm", 30.0))
    total_power = 10 ** ((power_dbm - 30) / 10)

    wavelength = C_0 / freq_hz
    d_h = float(array_cfg.get("d_h_wavelengths", 0.5)) * wavelength
    d_v = float(array_cfg.get("d_v_wavelengths", 0.5)) * wavelength

    try:
        array = AntennaArray.upa(
            n_h=int(array_cfg["n_h"]),
            n_v=int(array_cfg["n_v"]),
            d_h=d_h,
            d_v=d_v,
            center=np.array(array_cfg["position"], dtype=np.float64),
            broadside=np.array(array_cfg["broadside"], dtype=np.float64),
            element_pattern=str(array_cfg.get("element_pattern", "patch")),
        )
    except (KeyError, ValueError) as exc:
        return None, (jsonify({"error": f"Invalid array config: {exc}"}), 400)

    bodies_cache = cache.get("bodies", {})
    users = []
    for u in users_cfg:
        phantom = u.get("phantom", cache.get("default_body", "thelonious"))
        if phantom not in bodies_cache:
            return None, (jsonify({"error": f"Unknown phantom: {phantom!r}"}), 404)

        # device_offset is relative to user body; convert to absolute world position
        user_pos = np.array(u.get("position", [0.0, 0.0, 0.0]), dtype=np.float64)
        default_offset = cache.get("body_device_offsets", {}).get(phantom, [0.0, 0.30, 1.4])
        device_offset = u.get("device_offset", u.get("device_position", default_offset))
        device_position = user_pos + np.array(device_offset, dtype=np.float64)
        device_orientation = u.get("device_orientation", [0.0, 0.0, 1.0])

        try:
            cfg = UserConfig(
                user_id=u["id"],
                phantom_name=phantom,
                position=np.array(u.get("position", [0.0, 0.0, 0.0]), dtype=np.float64),
                device_position=np.array(device_position, dtype=np.float64),
                device_orientation=np.array(device_orientation, dtype=np.float64),
                orientation=float(u.get("orientation", 0.0)),
            )
        except (KeyError, ValueError) as exc:
            return None, (jsonify({"error": f"Invalid user config: {exc}"}), 400)

        users.append(UserState(config=cfg))

    scene = MIMOScene(
        array=array,
        users=users,
        freq_hz=freq_hz,
        total_power=total_power,
    )
    return scene, None


def _user_stats(user: UserState, scene: MIMOScene) -> dict:
    """Build per-user stats dict from a computed UserState."""
    result = user.result
    stats: dict = {
        "user_id": user.config.user_id,
        "phantom": user.config.phantom_name,
    }
    if result is not None:
        p_abs = float(result.p_abs)
        stats["p_abs"] = p_abs
        stats["p_abs_mw"] = p_abs * 1e3
        stats["peak_sab"] = float(result.peak_sab)
        if hasattr(result, "sab_averaged") and result.sab_averaged is not None:
            stats["peak_sab_averaged"] = float(np.max(result.sab_averaged))
    return stats


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach MIMO routes to app."""

    @app.route("/api/mimo/compute", methods=["POST"])
    def api_mimo_compute():
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

        # Cache scene and per-user results
        with cache_lock:
            cache["mimo_scene"] = scene
            cache["mimo_summary"] = summary

            results_binary: dict[str, bytes] = {}
            results_stats: dict[str, dict] = {}
            for user in scene.users:
                uid = user.config.user_id
                if user._sab_raw is not None:
                    results_binary[uid] = user._sab_raw.astype(np.float32).tobytes()
                stats = _user_stats(user, scene)
                results_stats[uid] = stats

            cache["mimo_results_binary"] = results_binary
            cache["mimo_results_stats"] = results_stats

        return jsonify(summary)

    @app.route("/api/mimo/result/<user_id>", methods=["GET"])
    def api_mimo_result(user_id: str):
        results_binary = cache.get("mimo_results_binary")
        if not results_binary or user_id not in results_binary:
            return jsonify({"error": f"No result for user {user_id!r}"}), 404

        data_bytes = results_binary[user_id]
        stats = (cache.get("mimo_results_stats") or {}).get(user_id, {})

        resp = Response(data_bytes, mimetype=_OCTET_STREAM)
        resp.headers["X-Stats"] = _json_dumps_safe(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/mimo/summary", methods=["GET"])
    def api_mimo_summary():
        summary = cache.get("mimo_summary")
        scene = cache.get("mimo_scene")
        if summary is None or scene is None:
            return jsonify({"error": "No MIMO results computed yet"}), 404

        config = cache.get("config", {})
        exposure_budget_mw = float(config.get("mimo", {}).get("exposure_budget_mw", 100.0))

        users_out = []
        results_stats = cache.get("mimo_results_stats", {})
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
                "compliant": p_abs_mw < exposure_budget_mw,
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
