"""Sionna RT routes (scene-file based and environment-mesh based)."""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
from flask import Response, jsonify, request

from aegis.defaults import DEFAULT_POWER_DBM
from aegis.viewer.routes._types import RouteResponse
from aegis.viewer.server import scoped_cache_get

from ._parsing import (
    _ERR_INVALID_JSON,
    _ERR_INVALID_SCENE,
    _parse_freq_and_tissue,
    _parse_mode_or_level,
    _parse_quantities_and_scenario,
    _parse_rotation_y,
    _parse_vec3,
)
from ._responses import (
    _MAX_POWER_DBM,
    _cache_dosimetry_for_export,
    _make_rt_response,
    _stats_label,
    _zero_paths_response,
)
from ._rt_config import _parse_rt_config

logger = logging.getLogger(__name__)

_ErrResp = tuple[Response, int]


def _validate_scene_path(scene_path: str) -> bool:
    """Proxy to package-level `_validate_scene_path` so tests can mock it."""
    from aegis.viewer.routes import compute as _pkg

    return _pkg._validate_scene_path(scene_path)


def _run_dosimetry(tissue, body, paths, engine_kw, **kwargs) -> tuple[Any, _ErrResp | None]:
    """Proxy to package-level `_run_dosimetry` so tests can mock it."""
    from aegis.viewer.routes import compute as _pkg

    return _pkg._run_dosimetry(tissue, body, paths, engine_kw, **kwargs)


def _parse_power_dbm(params: dict) -> tuple[float | None, _ErrResp | None]:
    """Parse and validate power_dbm. Returns (float, None) or (None, error_response)."""
    try:
        power_dbm = float(params.get("power_dbm", DEFAULT_POWER_DBM))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "power_dbm must be a number"}), 400)
    if not math.isfinite(power_dbm):
        return None, (jsonify({"error": "power_dbm must be a finite number"}), 400)
    if power_dbm < 0 or power_dbm > _MAX_POWER_DBM:
        return None, (jsonify({"error": f"power_dbm must be between 0 and {_MAX_POWER_DBM} dBm"}), 400)
    return power_dbm, None


def _sionna_rt_config(rt_cfg: dict) -> dict:
    """Build the rt_config dict sent to Sionna Modal functions."""
    return {
        "los": rt_cfg["los"],
        "specular_reflection": rt_cfg["specular_reflection"],
        "diffuse_reflection": rt_cfg["diffuse_reflection"],
        "refraction": rt_cfg["refraction"],
        "diffraction": rt_cfg["diffraction"],
        "edge_diffraction": rt_cfg["edge_diffraction"],
        "diffraction_lit_region": rt_cfg["diffraction_lit_region"],
        "samples_per_src": rt_cfg["rays_per_source"],
        "max_num_paths_per_src": rt_cfg["max_paths_per_source"],
        "synthetic_array": rt_cfg["synthetic_array"],
        "seed": rt_cfg["seed"],
    }


def _resolve_body_from_cache(cache: dict, cache_lock, params: dict) -> tuple[Any, _ErrResp | None]:
    """Resolve cached body mesh for a scene-based request."""
    body_name = params.get("body_name", cache.get("default_body"))
    if body_name is not None and not isinstance(body_name, str):
        return None, (jsonify({"error": "body_name must be a string"}), 400)
    with cache_lock:
        entry = cache.get("bodies", {}).get(body_name)
    if entry is None:
        return None, (jsonify({"error": f"Body '{body_name}' not found"}), 404)
    return entry["body"], None


def _parse_common_sionna_params(params: dict, cache: dict) -> tuple[dict[str, Any] | None, _ErrResp | None]:
    """Parse shared sionna route parameters (antenna pos, offsets, engine, power, tissue, ...)."""
    antenna_pos, err = _parse_vec3(params, "antenna_pos", [5, 0, 1])
    if err:
        return None, err
    body_offset, err = _parse_vec3(params, "body_offset")
    if err:
        return None, err
    body_rotation_y, err = _parse_rotation_y(params)
    if err:
        return None, err
    engine_kw, err = _parse_mode_or_level(params)
    if err:
        return None, err
    power_dbm, err = _parse_power_dbm(params)
    if err is not None:
        return None, err
    rt_cfg_parsed = _parse_rt_config(params, cache)
    tissue, _, err = _parse_freq_and_tissue(params)
    if err:
        return None, err
    quantities, exposure_scenario, err = _parse_quantities_and_scenario(params)
    if err:
        return None, err

    return {
        "antenna_pos": antenna_pos,
        "body_offset": body_offset,
        "body_rotation_y": body_rotation_y,
        "engine_kw": engine_kw,
        "power_dbm": power_dbm,
        "rt_cfg": rt_cfg_parsed,
        "tissue": tissue,
        "quantities": quantities,
        "exposure_scenario": exposure_scenario,
    }, None


def _finalize_rt_response(
    cache, transformed_body, body, paths, path_viz, gpu_backend, rt_ms, was_cold, backend_label, pp, timings
) -> RouteResponse:
    """Run dosimetry, build binary X-Stats response, and cache for export.

    ``timings`` is a dict with keys: ``t_route``, ``t_rt``.
    Returns the Flask Response.
    """
    import time as _time

    level_val, _, _ = _stats_label(pp["engine_kw"])
    if paths.n_paths == 0:
        return _zero_paths_response(body, pp["tissue"], level_val or 0, cache=cache)

    ecbf_warnings: list[str] = []
    result, err = _run_dosimetry(
        pp["tissue"], transformed_body, paths, pp["engine_kw"], ecbf_warnings_out=ecbf_warnings
    )
    if err:
        return err
    assert result is not None  # noqa: S101 - helper contract
    t_compute = _time.perf_counter()

    body_center_arr = timings.get("body_center")
    if body_center_arr is None:
        body_center_arr = transformed_body.centroids.mean(axis=0)
    dist = float(np.linalg.norm(pp["antenna_pos"] - body_center_arr))
    extra = {
        "S_inc": float(np.sum(paths.power)),
        "distance_m": dist,
        "n_rt_paths": paths.n_paths,
        "path_viz": path_viz,
        "backend": backend_label,
        "cold_start": was_cold,
    }
    if gpu_backend is not None:
        extra["gpu_backend"] = gpu_backend
    if ecbf_warnings:
        extra["ecbf_warnings"] = ecbf_warnings

    t_stats = _time.perf_counter()
    timing_pairs = [
        ("rt_ms", rt_ms if rt_ms is not None else (timings["t_rt"] - timings["t_route"]) * 1e3),
        ("kernel_ms", (t_compute - timings["t_rt"]) * 1e3),
        ("compliance_stats_ms", (t_stats - t_compute) * 1e3),
        ("route_total_ms", (t_stats - timings["t_route"]) * 1e3),
    ]
    resp, stats, err = _make_rt_response(
        result,
        transformed_body,
        pp["tissue"],
        pp["engine_kw"],
        pp["quantities"],
        pp["exposure_scenario"],
        extra,
        timing_pairs,
    )
    if err:
        return err
    assert resp is not None  # noqa: S101 - helper contract
    assert stats is not None  # noqa: S101 - helper contract
    _cache_dosimetry_for_export(cache, result, transformed_body, stats, paths=paths, tissue=pp["tissue"])
    return resp


def _call_modal_sionna_scene(
    scene_path: str, antenna_pos, body_center, pp, rt_cfg_dict
) -> tuple[dict[str, Any] | None, _ErrResp | None]:
    """Run Sionna RT on Modal using a scene-file source.

    Returns (modal_result, None) or (None, error_response) on failure.
    """
    from pathlib import Path as _Path

    from aegis.viewer.modal_proxy import trace_sionna_bundled as _modal_trace_sionna

    scene_name = _Path(scene_path).parent.name
    modal_result = _modal_trace_sionna(
        scene_name=scene_name,
        tx_pos=antenna_pos.tolist(),
        rx_pos=body_center.tolist(),
        max_bounces=pp["rt_cfg"]["max_depth"],
        freq_hz=pp["tissue"].freq_hz,
        tx_power_dbm=pp["power_dbm"],
        rt_config=rt_cfg_dict,
    )
    if modal_result is None:
        return None, (jsonify({"error": "Sionna RT requires GPU. Modal unavailable."}), 501)
    return modal_result, None


def _unpack_modal_result(modal_result: dict):
    """Convert a Modal trace result to (paths, path_viz, gpu_backend, rt_ms)."""
    from aegis.paths import PropagationPaths

    paths = PropagationPaths.from_dict(modal_result["paths"])
    path_viz = modal_result["path_viz"]
    gpu_backend = modal_result.get("gpu_backend")
    rt_ms = modal_result.get("timings", {}).get("trace_ms")
    return paths, path_viz, gpu_backend, rt_ms


def _api_compute_sionna_rt_impl(cache: dict, cache_lock) -> RouteResponse:
    """Compute dosimetry using Sionna RT ray-traced paths (via Modal GPU)."""
    from aegis.viewer.compute import _transform_body_for_viewer

    params = request.get_json(silent=True)
    if not isinstance(params, dict):
        return jsonify({"error": _ERR_INVALID_JSON}), 400

    body, err = _resolve_body_from_cache(cache, cache_lock, params)
    if err is not None:
        return err
    assert body is not None  # noqa: S101 - helper contract

    scene_path = params.get("scene_path")
    if not scene_path:
        return jsonify({"error": "Missing 'scene_path'"}), 400
    if not _validate_scene_path(scene_path):
        return jsonify({"error": _ERR_INVALID_SCENE}), 400

    pp, err = _parse_common_sionna_params(params, cache)
    if err is not None:
        return err
    assert pp is not None  # noqa: S101 - helper contract

    # RT receiver: use configured default center (z=1m) shifted by body offset
    default_bc = np.array(cache["config"]["raytracer"]["default_body_center"])
    body_center = default_bc + pp["body_offset"]

    transformed_body = _transform_body_for_viewer(body, pp["body_offset"], pp["body_rotation_y"])

    import time as _time

    t_route = _time.perf_counter()

    from aegis.viewer.modal_proxy import gpu_status as _gpu_status

    _was_cold = not _gpu_status().get("warm", False)

    rt_cfg_dict = _sionna_rt_config(pp["rt_cfg"])

    modal_result, err = _call_modal_sionna_scene(scene_path, pp["antenna_pos"], body_center, pp, rt_cfg_dict)
    if err is not None:
        return err
    assert modal_result is not None  # noqa: S101 - helper contract

    paths, path_viz, gpu_backend, rt_ms = _unpack_modal_result(modal_result)

    t_rt = _time.perf_counter()

    return _finalize_rt_response(
        cache,
        transformed_body,
        body,
        paths,
        path_viz,
        gpu_backend,
        rt_ms,
        _was_cold,
        "sionna",
        pp,
        {"t_route": t_route, "t_rt": t_rt, "body_center": body_center},
    )


def _load_env_request(cache: dict, cache_lock, params: dict) -> tuple[tuple[Any, Any, Any] | None, _ErrResp | None]:
    """Fetch body mesh + environment mesh from the cache.

    Returns ((body, env_mesh, cfg), None) or (None, error_response) on failure.
    """
    body_name = params.get("body_name", cache.get("default_body"))
    if body_name is not None and not isinstance(body_name, str):
        return None, (jsonify({"error": "body_name must be a string"}), 400)
    with cache_lock:
        entry = cache.get("bodies", {}).get(body_name)
        env_mesh = scoped_cache_get(cache, "env_mesh")
        cfg = cache["config"]
    if entry is None:
        return None, (jsonify({"error": f"Body '{body_name}' not found"}), 404)
    if env_mesh is None:
        return None, (jsonify({"error": "No environment mesh available"}), 400)
    return (entry["body"], env_mesh, cfg), None


def _build_env_mesh_scene(
    env_mesh, max_order: int, max_rt_triangles: int
) -> tuple[tuple[Any, Any, Any] | None, _ErrResp | None]:
    """Convert environment mesh to Sionna-ready scene data with triangle cap check.

    Returns ((hull_verts, hull_tris, per_face_mats), None) on success or
    (None, error_response) on failure.
    """
    try:
        from aegis.environment.export import to_sionna_mesh_data

        hull_verts, hull_tris, per_face_mats = to_sionna_mesh_data(env_mesh)

        actual_triangles = len(hull_tris)
        if actual_triangles > max_rt_triangles and max_order > 0:
            return None, (
                jsonify(
                    {
                        "error": f"Scene too large for reflections ({actual_triangles:,} triangles, "
                        f"limit {max_rt_triangles:,}). Use LOS only (order 0) or reduce scene size."
                    }
                ),
                400,
            )
        return (hull_verts, hull_tris, per_face_mats), None
    except Exception as e:
        return None, (jsonify({"error": f"Environment mesh build failed: {e}"}), 500)


def _call_modal_sionna_env(
    env_mesh, scene_data: dict, antenna_pos, body_center, max_order: int, pp: dict, rt_cfg_dict: dict
) -> tuple[dict[str, Any] | None, _ErrResp | None]:
    """Run Sionna RT on Modal with an environment-mesh scene.

    Returns (modal_result, None) on success or (None, error_response) on failure.
    """
    import hashlib

    from aegis.viewer.modal_proxy import trace_sionna_voxel as _modal_trace_voxel

    env_hash = hashlib.md5(np.asarray(env_mesh.vertices).tobytes()).hexdigest()[:12]
    scene_key = f"env_{env_hash}"

    try:
        modal_result = _modal_trace_voxel(
            scene_key=scene_key,
            scene_data=scene_data,
            tx_pos=antenna_pos.tolist(),
            rx_pos=body_center.tolist(),
            max_bounces=max_order,
            freq_hz=pp["tissue"].freq_hz,
            tx_power_dbm=pp["power_dbm"],
            rt_config=rt_cfg_dict,
        )
    except NotImplementedError:
        return None, (jsonify({"error": "Environment mesh ray tracing with Sionna is not yet implemented."}), 501)

    if modal_result is None:
        return None, (jsonify({"error": "GPU unavailable for environment mesh ray tracing"}), 501)
    return modal_result, None


def _api_compute_sionna_env_rt_impl(cache: dict, cache_lock) -> RouteResponse:
    """Compute dosimetry using Sionna RT on the environment mesh (via Modal GPU)."""
    from aegis.viewer.compute import _transform_body_for_viewer

    params = request.get_json(silent=True)
    if not isinstance(params, dict):
        return jsonify({"error": _ERR_INVALID_JSON}), 400

    loaded, err = _load_env_request(cache, cache_lock, params)
    if err is not None:
        return err
    assert loaded is not None  # noqa: S101 - helper contract
    body, env_mesh, cfg = loaded

    pp, err = _parse_common_sionna_params(params, cache)
    if err is not None:
        return err
    assert pp is not None  # noqa: S101 - helper contract

    transformed_body = _transform_body_for_viewer(body, pp["body_offset"], pp["body_rotation_y"])
    body_center = transformed_body.centroids.mean(axis=0)

    import time as _time

    t_route = _time.perf_counter()

    max_order = pp["rt_cfg"]["max_depth"]
    max_rt_triangles = cfg["raytracer"]["max_rt_triangles"]

    scene_parts, err = _build_env_mesh_scene(env_mesh, max_order, max_rt_triangles)
    if err is not None:
        return err
    assert scene_parts is not None  # noqa: S101 - helper contract
    hull_verts, hull_tris, per_face_mats = scene_parts

    from aegis.viewer.modal_proxy import gpu_status as _gpu_status

    _was_cold = not _gpu_status().get("warm", False)

    scene_data = {
        "vertices": hull_verts.tolist(),
        "triangles": hull_tris.tolist(),
        "materials": per_face_mats,
    }

    rt_cfg_dict = _sionna_rt_config(pp["rt_cfg"])

    modal_result, err = _call_modal_sionna_env(
        env_mesh, scene_data, pp["antenna_pos"], body_center, max_order, pp, rt_cfg_dict
    )
    if err is not None:
        return err
    assert modal_result is not None  # noqa: S101 - helper contract

    paths, path_viz, gpu_backend, rt_ms = _unpack_modal_result(modal_result)

    t_rt = _time.perf_counter()

    return _finalize_rt_response(
        cache,
        transformed_body,
        body,
        paths,
        path_viz,
        gpu_backend,
        rt_ms,
        _was_cold,
        "sionna-env",
        pp,
        {"t_route": t_route, "t_rt": t_rt, "body_center": body_center},
    )
