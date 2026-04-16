"""Sionna RT routes (scene-file based and environment-mesh based)."""

from __future__ import annotations

import logging

import numpy as np
from flask import Response, jsonify, request

from aegis.defaults import DEFAULT_POWER_DBM
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


def _validate_scene_path(scene_path: str) -> bool:
    """Proxy to package-level `_validate_scene_path` so tests can mock it."""
    from aegis.viewer.routes import compute as _pkg

    return _pkg._validate_scene_path(scene_path)


def _run_dosimetry(tissue, body, paths, engine_kw):
    """Proxy to package-level `_run_dosimetry` so tests can mock it."""
    from aegis.viewer.routes import compute as _pkg

    return _pkg._run_dosimetry(tissue, body, paths, engine_kw)


def _api_compute_sionna_rt_impl(cache: dict, cache_lock) -> Response:
    """Compute dosimetry using Sionna RT ray-traced paths (via Modal GPU)."""
    from aegis.viewer.compute import _transform_body_for_viewer

    params = request.get_json(silent=True)
    if not isinstance(params, dict):
        return jsonify({"error": _ERR_INVALID_JSON}), 400

    body_name = params.get("body_name", cache.get("default_body"))
    with cache_lock:
        entry = cache.get("bodies", {}).get(body_name)
    if entry is None:
        return jsonify({"error": f"Body '{body_name}' not found"}), 404
    body = entry["body"]

    antenna_pos, err = _parse_vec3(params, "antenna_pos", [5, 0, 1])
    if err:
        return err

    scene_path = params.get("scene_path")
    if not scene_path:
        return jsonify({"error": "Missing 'scene_path'"}), 400
    if not _validate_scene_path(scene_path):
        return jsonify({"error": _ERR_INVALID_SCENE}), 400

    engine_kw, err = _parse_mode_or_level(params)
    if err:
        return err
    try:
        power_dbm = float(params.get("power_dbm", DEFAULT_POWER_DBM))
    except (TypeError, ValueError):
        return jsonify({"error": "power_dbm must be a number"}), 400
    if power_dbm < 0 or power_dbm > _MAX_POWER_DBM:
        return jsonify({"error": f"power_dbm must be between 0 and {_MAX_POWER_DBM} dBm"}), 400
    rt_cfg_parsed = _parse_rt_config(params, cache)

    body_offset, err = _parse_vec3(params, "body_offset")
    if err:
        return err
    body_rotation_y, err = _parse_rotation_y(params)
    if err:
        return err
    tissue, _, err = _parse_freq_and_tissue(params)
    if err:
        return err
    quantities, exposure_scenario, err = _parse_quantities_and_scenario(params)
    if err:
        return err

    # RT receiver: use configured default center (z=1m) shifted by body offset
    default_bc = np.array(cache["config"]["raytracer"]["default_body_center"])
    body_center = default_bc + body_offset

    transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)

    import time as _time

    t_route = _time.perf_counter()

    # Call Modal GPU for Sionna RT (no local CPU fallback)
    from aegis.viewer.modal_proxy import gpu_status as _gpu_status

    _was_cold = not _gpu_status().get("warm", False)

    # Extract scene name from path: .../simple_reflector/simple_reflector.xml -> simple_reflector
    from pathlib import Path as _Path

    from aegis.viewer.modal_proxy import trace_sionna_bundled as _modal_trace_sionna

    scene_name = _Path(scene_path).parent.name
    rt_config_dict = {
        "los": rt_cfg_parsed["los"],
        "specular_reflection": rt_cfg_parsed["specular_reflection"],
        "diffuse_reflection": rt_cfg_parsed["diffuse_reflection"],
        "refraction": rt_cfg_parsed["refraction"],
        "diffraction": rt_cfg_parsed["diffraction"],
        "edge_diffraction": rt_cfg_parsed["edge_diffraction"],
        "diffraction_lit_region": rt_cfg_parsed["diffraction_lit_region"],
        "samples_per_src": rt_cfg_parsed["rays_per_source"],
        "max_num_paths_per_src": rt_cfg_parsed["max_paths_per_source"],
        "synthetic_array": rt_cfg_parsed["synthetic_array"],
        "seed": rt_cfg_parsed["seed"],
    }

    modal_result = _modal_trace_sionna(
        scene_name=scene_name,
        tx_pos=antenna_pos.tolist(),
        rx_pos=body_center.tolist(),
        max_bounces=rt_cfg_parsed["max_depth"],
        freq_hz=tissue.freq_hz,
        tx_power_dbm=power_dbm,
        rt_config=rt_config_dict,
    )

    if modal_result is None:
        return jsonify({"error": "Sionna RT requires GPU. Modal unavailable."}), 501

    from aegis.paths import PropagationPaths

    paths = PropagationPaths.from_dict(modal_result["paths"])
    path_viz = modal_result["path_viz"]
    gpu_backend = modal_result.get("gpu_backend")
    rt_ms = modal_result.get("timings", {}).get("trace_ms")

    t_rt = _time.perf_counter()

    level_val, _, _ = _stats_label(engine_kw)
    if paths.n_paths == 0:
        return _zero_paths_response(body, tissue, level_val or 0, cache=cache)

    result, err = _run_dosimetry(tissue, transformed_body, paths, engine_kw)
    if err:
        return err
    t_compute = _time.perf_counter()

    dist = float(np.linalg.norm(antenna_pos - body_center))
    extra = {
        "S_inc": float(np.sum(paths.power)),
        "distance_m": dist,
        "n_rt_paths": paths.n_paths,
        "path_viz": path_viz,
        "backend": "sionna",
        "cold_start": _was_cold,
    }

    if gpu_backend is not None:
        extra["gpu_backend"] = gpu_backend

    t_stats = _time.perf_counter()
    timing_pairs = [
        ("rt_ms", rt_ms if rt_ms is not None else (t_rt - t_route) * 1e3),
        ("kernel_ms", (t_compute - t_rt) * 1e3),
        ("compliance_stats_ms", (t_stats - t_compute) * 1e3),
        ("route_total_ms", (t_stats - t_route) * 1e3),
    ]
    resp, stats, err = _make_rt_response(
        result,
        transformed_body,
        tissue,
        engine_kw,
        quantities,
        exposure_scenario,
        extra,
        timing_pairs,
    )
    if err:
        return err
    _cache_dosimetry_for_export(cache, result, transformed_body, stats, paths=paths)
    return resp


def _api_compute_sionna_env_rt_impl(cache: dict, cache_lock) -> Response:
    """Compute dosimetry using Sionna RT on the environment mesh (via Modal GPU)."""
    from aegis.viewer.compute import _transform_body_for_viewer

    params = request.get_json(silent=True)
    if not isinstance(params, dict):
        return jsonify({"error": _ERR_INVALID_JSON}), 400

    body_name = params.get("body_name", cache.get("default_body"))
    with cache_lock:
        entry = cache.get("bodies", {}).get(body_name)
        env_mesh = scoped_cache_get(cache, "env_mesh")
        cfg = cache["config"]
    if entry is None:
        return jsonify({"error": f"Body '{body_name}' not found"}), 404
    body = entry["body"]

    if env_mesh is None:
        return jsonify({"error": "No environment mesh available"}), 400

    antenna_pos, err = _parse_vec3(params, "antenna_pos", [5, 0, 1])
    if err:
        return err
    body_offset, err = _parse_vec3(params, "body_offset")
    if err:
        return err
    body_rotation_y, err = _parse_rotation_y(params)
    if err:
        return err

    engine_kw, err = _parse_mode_or_level(params)
    if err:
        return err
    try:
        power_dbm = float(params.get("power_dbm", DEFAULT_POWER_DBM))
    except (TypeError, ValueError):
        return jsonify({"error": "power_dbm must be a number"}), 400
    if power_dbm < 0 or power_dbm > _MAX_POWER_DBM:
        return jsonify({"error": f"power_dbm must be between 0 and {_MAX_POWER_DBM} dBm"}), 400
    rt_cfg_parsed = _parse_rt_config(params, cache)
    max_order = rt_cfg_parsed["max_depth"]

    quantities, exposure_scenario, err = _parse_quantities_and_scenario(params)
    if err:
        return err
    tissue, _, err = _parse_freq_and_tissue(params)
    if err:
        return err

    # Transform body consistently (vertices, centroids, normals all rotated + offset)
    transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)
    body_center = transformed_body.centroids.mean(axis=0)

    import time as _time

    t_route = _time.perf_counter()

    # Extract mesh data for Modal
    max_rt_triangles = cfg["raytracer"]["max_rt_triangles"]
    try:
        from aegis.environment.export import to_sionna_mesh_data

        hull_verts, hull_tris, per_face_mats = to_sionna_mesh_data(env_mesh)

        actual_triangles = len(hull_tris)
        if actual_triangles > max_rt_triangles and max_order > 0:
            return jsonify(
                {
                    "error": f"Scene too large for reflections ({actual_triangles:,} triangles, "
                    f"limit {max_rt_triangles:,}). Use LOS only (order 0) or reduce scene size."
                }
            ), 400
    except Exception as e:
        return jsonify({"error": f"Environment mesh build failed: {e}"}), 500

    # Call Modal GPU for Sionna RT on environment mesh geometry
    import hashlib

    from aegis.viewer.modal_proxy import gpu_status as _gpu_status
    from aegis.viewer.modal_proxy import trace_sionna_voxel as _modal_trace_voxel

    _was_cold = not _gpu_status().get("warm", False)

    env_hash = hashlib.md5(np.asarray(env_mesh.vertices).tobytes()).hexdigest()[:12]
    scene_key = f"env_{env_hash}"

    scene_data = {
        "vertices": hull_verts.tolist(),
        "triangles": hull_tris.tolist(),
        "materials": per_face_mats,
    }

    rt_config_dict = {
        "los": rt_cfg_parsed["los"],
        "specular_reflection": rt_cfg_parsed["specular_reflection"],
        "diffuse_reflection": rt_cfg_parsed["diffuse_reflection"],
        "refraction": rt_cfg_parsed["refraction"],
        "diffraction": rt_cfg_parsed["diffraction"],
        "edge_diffraction": rt_cfg_parsed["edge_diffraction"],
        "diffraction_lit_region": rt_cfg_parsed["diffraction_lit_region"],
        "samples_per_src": rt_cfg_parsed["rays_per_source"],
        "max_num_paths_per_src": rt_cfg_parsed["max_paths_per_source"],
        "synthetic_array": rt_cfg_parsed["synthetic_array"],
        "seed": rt_cfg_parsed["seed"],
    }

    try:
        modal_result = _modal_trace_voxel(
            scene_key=scene_key,
            scene_data=scene_data,
            tx_pos=antenna_pos.tolist(),
            rx_pos=body_center.tolist(),
            max_bounces=max_order,
            freq_hz=tissue.freq_hz,
            tx_power_dbm=power_dbm,
            rt_config=rt_config_dict,
        )
    except NotImplementedError:
        return jsonify({"error": "Environment mesh ray tracing with Sionna is not yet implemented."}), 501

    if modal_result is None:
        return jsonify({"error": "GPU unavailable for environment mesh ray tracing"}), 501

    from aegis.paths import PropagationPaths

    paths = PropagationPaths.from_dict(modal_result["paths"])
    path_viz = modal_result["path_viz"]
    gpu_backend = modal_result.get("gpu_backend")
    rt_ms = modal_result.get("timings", {}).get("trace_ms")

    t_rt = _time.perf_counter()

    level_val, _, _ = _stats_label(engine_kw)
    if paths.n_paths == 0:
        return _zero_paths_response(body, tissue, level_val or 0, cache=cache)

    result, err = _run_dosimetry(tissue, transformed_body, paths, engine_kw)
    if err:
        return err
    t_compute = _time.perf_counter()

    dist = float(np.linalg.norm(antenna_pos - body_center))
    extra = {
        "S_inc": float(np.sum(paths.power)),
        "distance_m": dist,
        "n_rt_paths": paths.n_paths,
        "path_viz": path_viz,
    }

    extra["backend"] = "sionna-env"
    extra["cold_start"] = _was_cold
    if gpu_backend is not None:
        extra["gpu_backend"] = gpu_backend

    t_stats = _time.perf_counter()
    timing_pairs = [
        ("rt_ms", rt_ms if rt_ms is not None else (t_rt - t_route) * 1e3),
        ("kernel_ms", (t_compute - t_rt) * 1e3),
        ("compliance_stats_ms", (t_stats - t_compute) * 1e3),
        ("route_total_ms", (t_stats - t_route) * 1e3),
    ]
    resp, stats, err = _make_rt_response(
        result,
        transformed_body,
        tissue,
        engine_kw,
        quantities,
        exposure_scenario,
        extra,
        timing_pairs,
    )
    if err:
        return err
    _cache_dosimetry_for_export(cache, result, transformed_body, stats, paths=paths)
    return resp
