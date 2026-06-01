"""Optimization SSE endpoint.

Streams optimization iterations as server-sent events.
POST /api/optimize - start optimization (returns text/event-stream)
POST /api/optimize/cancel - cancel running optimization
"""

from __future__ import annotations

import base64
import json
import logging
import math
import threading
import uuid
from typing import Any

import numpy as np
from flask import Flask, Response, jsonify, session

from aegis.optim.loop import run_optimization
from aegis.viewer.routes._helpers import get_json_dict
from aegis.viewer.routes._types import RouteResponse
from aegis.viewer.server import scoped_cache_get

logger = logging.getLogger(__name__)

_cancel_events: dict[str, threading.Event] = {}
_cancel_lock = threading.Lock()


def _get_session_id() -> str:
    """Return a stable session ID for the current request.

    Uses Flask session if available, otherwise generates a UUID and stores it
    so subsequent requests from the same client can cancel a running optimization.
    """
    sid = session.get("session_id")
    if sid is None:
        sid = uuid.uuid4().hex
        session["session_id"] = sid
    return sid


def _json_safe(obj: Any) -> Any:
    """Make obj JSON-serializable (handle numpy types)."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def _encode_sab(sab: np.ndarray) -> str:
    """Encode float32 SAB array as base64."""
    return base64.b64encode(np.asarray(sab, dtype=np.float32).tobytes()).decode()


def _safe_int(val, default: int) -> int:
    """Convert to int, returning *default* on failure."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_float(val, default: float) -> float:
    """Convert to float, returning *default* on failure."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _require_finite_float(
    params: dict,
    key: str,
    default: float,
    *,
    positive: bool = False,
) -> float:
    raw = params.get(key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{key} must be finite")
    if positive and value <= 0:
        raise ValueError(f"{key} must be positive")
    return value


def _require_finite_vec3(params: dict, key: str, default: list[float]) -> np.ndarray:
    raw = params.get(key, default)
    try:
        values = [float(v) for v in raw]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a list of 3 numbers") from exc
    if len(values) != 3:
        raise ValueError(f"{key} must have exactly 3 elements")
    if not all(math.isfinite(v) for v in values):
        raise ValueError(f"{key} values must be finite")
    return np.array(values, dtype=np.float64)


def _parse_rt_config(params: dict, cache: dict) -> dict[str, Any]:
    """Extract RT config for placement evaluation."""
    rt = params.get("rt_config", {})
    if not isinstance(rt, dict):
        rt = {}

    rt_defaults = cache["config"]["raytracer"]["defaults"]
    d_max = rt_defaults["max_depth"]
    r_def = rt_defaults["rays_per_source"]
    r_min = rt_defaults["rays_per_source_min"]
    r_max = rt_defaults["rays_per_source_max"]
    c_def = rt_defaults["chunk_size"]
    c_max = rt_defaults["chunk_size_max"]

    max_depth = _safe_int(rt.get("max_depth", params.get("max_order", d_max)), d_max)
    max_depth = max(rt_defaults["max_depth_min"], min(max_depth, rt_defaults["max_depth_max"]))

    rays_per_source = _safe_int(rt.get("rays_per_source", r_def), r_def)
    rays_per_source = max(r_min, min(rays_per_source, r_max))

    chunk_size = rt.get("chunk_size")
    if chunk_size is not None:
        chunk_size = max(1, min(_safe_int(chunk_size, c_def), c_max))

    return {
        "max_depth": max_depth,
        "method": rt.get("method", "exhaustive"),
        "rays_per_source": rays_per_source,
        "chunk_size": chunk_size,
        "reflection_loss_per_order": rt.get(
            "reflection_loss_per_order",
            cache["config"]["raytracer"]["reflection_loss_per_order"],
        ),
    }


def _api_optimize_impl(app: Flask, cache: dict, cache_lock) -> RouteResponse:
    params, err = get_json_dict()
    if err is not None:
        return err
    mode = params.get("mode")
    if not mode:
        return jsonify({"error": "mode is required"}), 400

    try:
        config = _build_config(params, app, cache, cache_lock)
    except (ValueError, KeyError) as e:
        return jsonify({"error": str(e)}), 400

    sid = _get_session_id()
    cancel = threading.Event()
    with _cancel_lock:
        if sid in _cancel_events:
            _cancel_events[sid].set()
        _cancel_events[sid] = cancel

    def generate():
        try:
            for result in run_optimization(config, cancel_event=cancel):
                event = _json_safe(result)
                if "sab" in event:
                    event["sab_b64"] = _encode_sab(result["sab"])
                    del event["sab"]
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.exception("Optimization error")
            yield f"data: {json.dumps({'error': True, 'message': str(e)})}\n\n"
        finally:
            with _cancel_lock:
                _cancel_events.pop(sid, None)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _api_optimize_cancel_impl(cache: dict, cache_lock) -> RouteResponse:
    sid = _get_session_id()
    with _cancel_lock:
        ev = _cancel_events.get(sid)
        if ev:
            ev.set()
            return jsonify({"cancelled": True})
    return jsonify({"cancelled": False})


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach optimization routes to app."""

    @app.route("/api/optimize", methods=["POST"])
    def api_optimize():
        return _api_optimize_impl(app, cache, cache_lock)

    @app.route("/api/optimize/cancel", methods=["POST"])
    def api_optimize_cancel():
        return _api_optimize_cancel_impl(cache, cache_lock)


_VALID_MODES = {"mimo_peak", "tilt_power", "placement"}


def _resolve_mimo_g_tilde(params: dict, cache: dict, cache_lock) -> np.ndarray:
    """Resolve the MIMO body channel matrix G_tilde from params or cache."""
    if "G_tilde_real" in params:
        G_real = np.array(params["G_tilde_real"])
        G_imag = np.array(params["G_tilde_imag"])
        return G_real + 1j * G_imag

    with cache_lock:
        scene = scoped_cache_get(cache, "mimo_scene")
    if scene is None:
        raise ValueError("MIMO scene is not ready yet. Wait for the compute to finish and try again.")
    # G_tilde lives on each UserState, not on the scene itself.
    # Use the focused user's G_tilde (or first user with one).
    user_id = params.get("user_id")
    for u in scene.users:
        if user_id and u.config.user_id != user_id:
            continue
        if u.G_tilde is not None:
            return u.G_tilde
    raise ValueError("MIMO body channel is not ready yet. Wait for the compute to finish and try again.")


def _resolve_mimo_x_init(params: dict, G_tilde: np.ndarray) -> np.ndarray:
    """Resolve the initial precoder vector from params or default to first steering vector."""
    x_real = np.array(params.get("x_init_real", []))
    x_imag = np.array(params.get("x_init_imag", []))
    if x_real.size > 0:
        return x_real + 1j * x_imag
    x_init = G_tilde[0, 0, :]
    norm = np.linalg.norm(x_init)
    if norm > 0:
        x_init = x_init / norm
    return x_init


def _build_mimo_peak_config(config: dict, params: dict, cache: dict, cache_lock) -> None:
    """Populate config for mimo_peak mode."""
    config["G_tilde"] = _resolve_mimo_g_tilde(params, cache, cache_lock)
    config["x_init"] = _resolve_mimo_x_init(params, config["G_tilde"])
    config["p_max"] = _require_finite_float(params, "p_max", 1.0, positive=True)
    config["signal_threshold"] = _require_finite_float(params, "signal_threshold", 0.0)


def _build_tilt_power_config(config: dict, params: dict, cache: dict) -> None:
    """Populate config for tilt_power mode."""
    last_result = scoped_cache_get(cache, "_last_dosimetry_result")
    last_body = scoped_cache_get(cache, "_last_dosimetry_body")
    last_paths = scoped_cache_get(cache, "_last_rt_paths")
    if last_result is None or last_body is None:
        raise ValueError("No dosimetry result cached. Run /api/compute first.")
    if last_paths is None:
        raise ValueError("No RT paths cached. Run an RT compute (/api/compute/rt) first.")
    config["paths"] = last_paths
    config["normals"] = np.array(last_body.normals)
    config["antenna_direction"] = _require_finite_vec3(params, "antenna_direction", [0, 0, -1])
    config["tilt_init_deg"] = _require_finite_float(params, "tilt_init_deg", 0.0)
    config["power_init_dbm"] = _require_finite_float(params, "power_init_dbm", 60.0)
    config["icnirp_limit"] = _require_finite_float(params, "icnirp_limit", 20.0, positive=True)

    last_stats = scoped_cache_get(cache, "_last_dosimetry_stats", {}) or {}
    t0_default = last_stats.get("T0", 1.0)
    try:
        t0_default = float(t0_default)
        if not math.isfinite(t0_default) or t0_default <= 0:
            t0_default = 1.0
    except (TypeError, ValueError):
        t0_default = 1.0
    config["T0"] = _require_finite_float(params, "T0", t0_default, positive=True)


def _build_placement_config(config: dict, params: dict, app: Flask, cache: dict, cache_lock) -> None:
    """Populate config for placement mode."""
    config["center"] = _require_finite_vec3(params, "center", [5, 0, 3])

    grid_size = _safe_int(params.get("grid_size", 5), 5)
    grid_size = max(1, min(grid_size, 50))
    config["grid_size"] = grid_size

    grid_spacing = _safe_float(params.get("grid_spacing", 2.0), 2.0)
    grid_spacing = max(0.1, min(grid_spacing, 500.0))
    config["grid_spacing"] = grid_spacing

    # Ensure max_iters covers the full grid so placement never truncates
    total_candidates = grid_size * grid_size
    if config["max_iters"] < total_candidates:
        config["max_iters"] = total_candidates

    config["constraint_axis"] = params.get("constraint_axis")
    config["constraint_value"] = params.get("constraint_value")
    config["evaluate_fn"] = _build_placement_evaluate_fn(
        params,
        app,
        cache,
        cache_lock,
    )


def _build_config(params: dict, app: Flask, cache: dict, cache_lock) -> dict:
    """Parse request params into optimizer config dict."""
    mode = params["mode"]
    if mode not in _VALID_MODES:
        raise ValueError(f"mode must be one of {sorted(_VALID_MODES)}")

    max_iters = _safe_int(params.get("max_iters", 50), 50)
    max_iters = max(1, min(max_iters, 10_000))
    config: dict[str, Any] = {"mode": mode, "max_iters": max_iters}

    if mode == "mimo_peak":
        _build_mimo_peak_config(config, params, cache, cache_lock)
    elif mode == "tilt_power":
        _build_tilt_power_config(config, params, cache)
    elif mode == "placement":
        _build_placement_config(config, params, app, cache, cache_lock)
    else:
        raise ValueError(f"Unknown mode: {mode!r}")

    return config


def _resolve_placement_body(params: dict, cache: dict, cache_lock):
    """Fetch the body entry referenced by params, raising if missing."""
    body_name = params.get("body_name", cache.get("default_body"))
    if body_name is not None and not isinstance(body_name, str):
        raise ValueError("body_name must be a string")
    with cache_lock:
        entry = cache.get("bodies", {}).get(body_name)
    if entry is None:
        raise ValueError(f"Body '{body_name}' not found. Load a body first.")
    return entry["body"]


def _parse_placement_engine_params(params: dict):
    """Parse tissue + engine kwargs for placement evaluation."""
    from aegis.viewer.routes.compute import _parse_freq_and_tissue, _parse_mode_or_level

    tissue, _, err = _parse_freq_and_tissue(params)
    if err:
        raise ValueError("Invalid tissue/frequency parameters")
    # Only forward keys that the caller actually supplied so _parse_mode_or_level
    # can fall back to its default level when neither mode nor level is set.
    # Passing ``None`` for level bypasses the .get(key, default) fallback and
    # trips the ``int(None)`` TypeError path.
    engine_params: dict = {}
    if params.get("dosimetry_mode") is not None:
        engine_params["mode"] = params["dosimetry_mode"]
    if params.get("level") is not None:
        engine_params["level"] = params["level"]
    for flag in ("fresnel", "polarisation", "curvature", "diffraction"):
        if params.get(flag) is not None:
            engine_params[flag] = params[flag]

    engine_kw, err = _parse_mode_or_level(engine_params)
    if err:
        raise ValueError("Invalid mode/level parameters")
    assert engine_kw is not None  # noqa: S101 - helper contract
    return tissue, engine_kw


def _build_voxel_rt_scene(cache: dict, cache_lock):
    """Build an RT scene from cached voxel data."""
    from aegis.viewer.raytracer import get_or_build_voxel_scene
    from aegis.viewer.scene_data import extract_exterior, prepare_for_raytracing

    with cache_lock:
        vp = cache["voxel_positions"]
        vs = cache.get("voxel_sizes")
        vm = cache.get("voxel_materials")
        cfg = cache.get("config", {})

    if vs is None:
        raise ValueError("voxel_sizes missing from cache; cannot build voxel scene")
    z_up_pos, gc, dominant_size = prepare_for_raytracing(vp, vs)
    ext_mask = extract_exterior(gc)
    ext_pos = z_up_pos[ext_mask]
    ext_grid = gc[ext_mask]
    ext_mats = [vm[i] for i in np.nonzero(ext_mask)[0]] if vm is not None else None
    material_colors = cfg.get("voxels", {}).get("material_colors")
    return get_or_build_voxel_scene(
        ext_pos,
        ext_grid,
        voxel_size=dominant_size,
        materials=ext_mats,
        material_colors=material_colors,
    )


def _resolve_placement_rt_scene(params: dict, cache: dict, cache_lock):
    """Resolve an RT scene for placement once, returning (rt_scene, scene_path).

    rt_scene is None when the caller should fall back to a user-supplied
    scene_path or to free-space propagation.
    """
    from aegis.viewer.routes.compute import _validate_scene_path

    scene_path = params.get("scene_path") or None
    if scene_path and not _validate_scene_path(scene_path):
        raise ValueError("Invalid scene path. Use /api/scenes to list available scenes.")

    if scene_path:
        return None, scene_path

    with cache_lock:
        has_voxels = cache.get("voxel_positions") is not None and len(cache.get("voxel_positions", [])) > 0
        has_env = scoped_cache_get(cache, "env_mesh") is not None

    if has_voxels:
        return _build_voxel_rt_scene(cache, cache_lock), None
    if has_env:
        from aegis.environment.export import to_differt_scene

        with cache_lock:
            env_mesh = scoped_cache_get(cache, "env_mesh")
        if env_mesh is None:
            return None, None
        return to_differt_scene(env_mesh), None
    return None, None


def _build_placement_evaluate_fn(
    params: dict,
    app: Flask,
    cache: dict,
    cache_lock,
):
    """Build evaluate_fn closure for placement grid search.

    Each call runs RT + dosimetry for a candidate antenna position and returns
    {"peak_sab": float, "sab": array, "stats": dict}.
    """
    from aegis.viewer.compute import _transform_body_for_viewer
    from aegis.viewer.routes.compute import (
        _build_stats_response,
        _run_dosimetry,
        _stats_label,
    )

    body = _resolve_placement_body(params, cache, cache_lock)
    tissue, engine_kw = _parse_placement_engine_params(params)

    if params.get("body_offset") is None:
        body_offset = np.array([0.0, 0.0, 0.0], dtype=np.float64)
    else:
        body_offset = _require_finite_vec3(params, "body_offset", [0, 0, 0])
    body_rotation_y = _require_finite_float(params, "body_rotation_y", 0.0)
    transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)

    default_bc = np.array(cache["config"]["raytracer"]["default_body_center"], dtype=np.float64)
    body_center = default_bc + body_offset

    power_dbm = _require_finite_float(params, "power_dbm", 43.0)
    pole_height = float(cache["config"]["antenna"].get("pole_height", 2.0))

    rt_cfg = _parse_rt_config(params, cache)
    max_order = rt_cfg["max_depth"]
    num_rays = rt_cfg["rays_per_source"]
    method = rt_cfg["method"]
    reflection_loss = rt_cfg["reflection_loss_per_order"]
    chunk_size = rt_cfg["chunk_size"]

    # Resolve RT scene once (not per eval)
    rt_scene, scene_path = _resolve_placement_rt_scene(params, cache, cache_lock)

    def evaluate_fn(pos: np.ndarray) -> dict:
        from aegis.viewer.raytracer import (
            compute_paths_differt,
            isotropic_incident_power_density,
        )

        tx_pos = np.asarray(pos, dtype=np.float64).reshape(3).copy()
        tx_pos[2] += pole_height
        if rt_scene is not None:
            paths, path_viz = compute_paths_differt(
                tx_pos=tx_pos,
                rx_pos=body_center,
                max_order=max_order,
                freq_hz=tissue.freq_hz,
                tx_power_dbm=power_dbm,
                reflection_loss_per_order=reflection_loss,
                method=method,
                num_rays=num_rays,
                chunk_size=chunk_size,
                scene=rt_scene,
            )
        elif scene_path:
            paths, path_viz = compute_paths_differt(
                scene_path,
                tx_pos=tx_pos,
                rx_pos=body_center,
                max_order=max_order,
                freq_hz=tissue.freq_hz,
                tx_power_dbm=power_dbm,
                reflection_loss_per_order=reflection_loss,
                method=method,
                num_rays=num_rays,
                chunk_size=chunk_size,
            )
        else:
            from aegis.paths import PropagationPaths

            direction = body_center - tx_pos
            dist = float(np.linalg.norm(direction))
            k_hat = direction / dist if dist > 1e-12 else np.array([0.0, 0.0, -1.0], dtype=np.float64)
            tx_power_w = 10 ** ((power_dbm - 30) / 10)
            paths = PropagationPaths.from_powers(
                k_hat=k_hat.reshape(1, 3),
                power=np.array([isotropic_incident_power_density(tx_power_w, dist)], dtype=np.float64),
            )
            path_viz = [{"vertices": [tx_pos.tolist(), body_center.tolist()], "order": 0, "length": dist}]

        ecbf_warnings: list[str] = []
        result, run_err = _run_dosimetry(tissue, transformed_body, paths, engine_kw, ecbf_warnings_out=ecbf_warnings)
        if run_err:
            raise RuntimeError(f"Dosimetry failed at pos {pos}")

        dist = float(np.linalg.norm(tx_pos - body_center))
        extra: dict[str, Any] = {
            "S_inc": float(np.sum(paths.power)),
            "distance_m": dist,
            "n_rt_paths": paths.n_paths,
            "path_viz": path_viz,
        }
        if ecbf_warnings:
            extra["ecbf_warnings"] = ecbf_warnings
        level_val, mode_val, corr_val = _stats_label(engine_kw)
        stats = _build_stats_response(
            result,
            body,
            tissue,
            level_val or 0,
            extra=extra,
            mode=mode_val,
            corrections=corr_val,
        )
        return {
            "peak_sab": float(result.peak_sab),
            "sab": result.sab,
            "stats": stats,
        }

    return evaluate_fn
