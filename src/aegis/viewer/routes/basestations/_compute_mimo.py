"""POST /api/basestations/compute_mimo handler."""

from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np
from flask import Response, jsonify

from aegis.viewer.routes._helpers import get_json_dict
from aegis.viewer.server import scoped_cache_get

logger = logging.getLogger(__name__)

_OCTET_STREAM = "application/octet-stream"
_ErrResp = tuple[Response, int]


def _validate_index(index, basestations) -> tuple[int | None, _ErrResp | None]:
    if index is None:
        return None, (jsonify({"error": "Missing 'index' in request"}), 400)
    try:
        index = int(index)
    except (TypeError, ValueError):
        return None, (jsonify({"error": "'index' must be an integer"}), 400)
    if index < 0 or index >= len(basestations):
        return None, (jsonify({"error": f"Index {index} out of range [0, {len(basestations)})"}), 400)
    return index, None


def _validate_level(params: dict) -> tuple[int | None, _ErrResp | None]:
    try:
        level = int(params.get("level", 7))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "level must be an integer"}), 400)
    if level not in (7, 8):
        return None, (jsonify({"error": "level must be 7 or 8 for MIMO"}), 400)
    return level, None


def _broadside_from_azimuth_tilt(az_deg: float, tilt_deg: float) -> np.ndarray:
    az_rad = np.deg2rad(az_deg)
    tilt_rad = np.deg2rad(tilt_deg)
    return np.array(
        [
            np.sin(az_rad) * np.cos(tilt_rad),
            np.cos(az_rad) * np.cos(tilt_rad),
            -np.sin(tilt_rad),
        ],
        dtype=np.float64,
    )


def _build_antenna_array(bs, ant_pos, broadside, archetype) -> tuple[Any, int | None, int | None, _ErrResp | None]:
    from aegis.basestation.classify import infer_element_grid
    from aegis.constants import C_0
    from aegis.mimo.array import AntennaArray

    n_h, n_v = infer_element_grid(archetype, bs.gain_dbi)
    spacing = (C_0 / bs.freq_hz) / 2.0
    try:
        array = AntennaArray.upa(
            n_h=n_h,
            n_v=n_v,
            d_h=spacing,
            d_v=spacing,
            center=ant_pos,
            broadside=broadside,
            element_pattern="patch",
        )
    except (ValueError, TypeError) as exc:
        return None, None, None, (jsonify({"error": f"Failed to build antenna array: {exc}"}), 400)
    return array, n_h, n_v, None


def _build_user(
    cache: dict,
    bodies_cache: dict,
    body_offset: np.ndarray,
    body_rotation_y: float,
) -> tuple[Any, str | None, _ErrResp | None]:
    from aegis.mimo.user import UserConfig, UserState

    phantom_name = cache.get("default_body", "thelonious")
    if phantom_name not in bodies_cache:
        if not bodies_cache:
            return None, None, (jsonify({"error": "No phantom loaded"}), 404)
        phantom_name = next(iter(bodies_cache))

    default_offset = cache.get("body_device_offsets", {}).get(phantom_name, [0.0, 0.30, 1.4])
    device_offset = np.array(default_offset, dtype=np.float64)
    cos_o, sin_o = np.cos(body_rotation_y), np.sin(body_rotation_y)
    rotated_offset = np.array(
        [
            cos_o * device_offset[0] - sin_o * device_offset[1],
            sin_o * device_offset[0] + cos_o * device_offset[1],
            device_offset[2],
        ]
    )
    user_cfg = UserConfig(
        user_id="bs_mimo_user",
        phantom_name=phantom_name,
        position=body_offset,
        device_position=body_offset + rotated_offset,
        device_orientation=np.array([0.0, 0.0, 1.0]),
        orientation=float(body_rotation_y),
    )
    return UserState(config=user_cfg), phantom_name, None


def _extract_sab_bytes(user, body):
    sab_data = user._sab_raw
    if sab_data is None:
        n_tri = body.n_triangles
        return np.zeros(n_tri, dtype=np.float32).tobytes(), 0.0, 0.0, n_tri

    sab_f32 = sab_data.astype(np.float32)
    peak_sab = float(np.max(sab_f32))
    p_abs = float(user.result.p_abs) if user.result else 0.0
    return sab_f32.tobytes(), peak_sab, p_abs, len(sab_data)


def _handle_basestations_compute_mimo(cache: dict, cache_lock: threading.RLock):
    """Implementation for POST /api/basestations/compute_mimo."""
    from aegis.basestation.classify import classify_antenna
    from aegis.basestation.coords import wgs84_to_enu
    from aegis.mimo.compute import compute_mimo_scene_with_bodies
    from aegis.mimo.scene import MIMOScene
    from aegis.viewer.routes.compute import _json_dumps_safe, _parse_rotation_y, _parse_vec3

    params, err = get_json_dict()
    if err is not None:
        return err

    with cache_lock:
        basestations = scoped_cache_get(cache, "basestations", []) or []
        origin = scoped_cache_get(cache, "basestations_origin")
        bodies_cache = cache.get("bodies", {})
        body_name = params.get("body_name", cache.get("default_body"))
        entry = bodies_cache.get(body_name)
    body = entry["body"] if entry is not None else None

    index, err = _validate_index(params.get("index"), basestations)
    if err is not None:
        return err
    assert index is not None  # noqa: S101 - helper contract
    bs = basestations[index]

    archetype = classify_antenna(
        gain_dbi=bs.gain_dbi,
        technology=bs.technology,
        freq_mhz=bs.freq_mhz,
        h_bw=bs.horizontal_beamwidth_deg or 0,
        v_bw=bs.vertical_beamwidth_deg or 0,
    )
    if archetype != "mmimo":
        return jsonify({"error": f"Base station {index} is classified as '{archetype}', not 'mmimo'"}), 400

    if body is None:
        return jsonify({"error": "No body mesh loaded"}), 404
    if origin is None:
        return jsonify({"error": "No scene origin set"}), 400

    body_offset, err = _parse_vec3(params, "body_offset", [0, 0, 0])
    if err:
        return err
    assert body_offset is not None  # noqa: S101 - helper contract
    body_rotation_y, err = _parse_rotation_y(params)
    if err:
        return err
    assert body_rotation_y is not None  # noqa: S101 - helper contract

    level, err = _validate_level(params)
    if err is not None:
        return err
    assert level is not None  # noqa: S101 - helper contract
    precoder_type = str(params.get("precoder_type", "mrt"))

    lat0, lon0 = origin
    ant_pos = wgs84_to_enu(bs.latitude, bs.longitude, 0.0, lat0, lon0)
    ant_pos[2] = bs.height_m
    broadside = _broadside_from_azimuth_tilt(bs.azimuth_deg, bs.total_tilt_deg)

    array, n_h, n_v, err = _build_antenna_array(bs, ant_pos, broadside, archetype)
    if err is not None:
        return err
    assert array is not None  # noqa: S101 - helper contract

    total_power = 10 ** ((bs.eirp_dbm - 30) / 10)

    user, _phantom_name, err = _build_user(cache, bodies_cache, body_offset, body_rotation_y)
    if err is not None:
        return err
    assert user is not None  # noqa: S101 - helper contract

    scene = MIMOScene(array=array, users=[user], freq_hz=bs.freq_hz, total_power=total_power)
    bodies = {name: entry["body"] for name, entry in bodies_cache.items()}

    try:
        summary = compute_mimo_scene_with_bodies(
            scene,
            bodies,
            level=level,
            precoder_type=precoder_type,
        )
    except Exception as exc:
        logger.exception("mMIMO compute failed for base station %d", index)
        return jsonify({"error": f"MIMO compute failed: {exc}"}), 500

    sab_bytes, peak_sab, p_abs, n_tri = _extract_sab_bytes(user, body)

    stats = {
        "p_abs": p_abs,
        "p_abs_mw": p_abs * 1e3,
        "peak_sab": peak_sab,
        "n_triangles": n_tri,
        "n_elements": array.n_elements,
        "n_h": n_h,
        "n_v": n_v,
        "archetype": archetype,
        "freq_hz": bs.freq_hz,
        "level": level,
        "precoder_type": precoder_type,
        "total_power_w": total_power,
        "base_station_index": index,
        "arrays": [{"key": "sab", "offset": 0, "length": n_tri}],
        "peaks": {"sab": peak_sab},
        "timings": summary.get("timings", {}),
    }

    resp = Response(sab_bytes, mimetype=_OCTET_STREAM)
    resp.headers["X-Stats"] = _json_dumps_safe(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp
