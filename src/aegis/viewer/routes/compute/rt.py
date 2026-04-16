"""DiffeRT ray-traced dosimetry route."""

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
    _ERR_NO_DIFFERT,
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


def _api_compute_rt_impl(cache: dict, cache_lock) -> Response:
    """Compute dosimetry using DiffeRT ray-traced paths."""
    try:
        from aegis.viewer.raytracer import compute_paths_differt
    except ImportError:
        return jsonify({"error": _ERR_NO_DIFFERT}), 501

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

    scene_path = params.get("scene_path") or None
    if scene_path and not _validate_scene_path(scene_path):
        return jsonify({"error": _ERR_INVALID_SCENE}), 400

    # Determine RT source: scene file, voxel hull, or environment mesh
    use_voxel_scene = False
    use_env_mesh = False
    if not scene_path:
        with cache_lock:
            has_voxels = cache.get("voxel_positions") is not None and len(cache.get("voxel_positions", [])) > 0
            has_env = scoped_cache_get(cache, "env_mesh") is not None
        if has_voxels:
            use_voxel_scene = True
        elif has_env:
            use_env_mesh = True
        else:
            return jsonify({"error": "No scene, voxels, or environment loaded for ray tracing"}), 400

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
    # (body centroid mean is ~z=-0.38, below floors of most Sionna scenes)
    default_bc = np.array(cache["config"]["raytracer"]["default_body_center"])
    body_center = default_bc + body_offset

    transformed_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)

    import time as _time

    t_route = _time.perf_counter()

    # Try Modal GPU first, fall back to local CPU (only if Modal is not configured)
    from aegis.viewer.modal_proxy import gpu_status as _gpu_status

    _was_cold = not _gpu_status().get("warm", False)
    gpu_backend = None
    modal_result = None
    modal_error = None

    if not use_voxel_scene and not use_env_mesh:
        try:
            from pathlib import Path as _Path

            from aegis.viewer.modal_proxy import _is_enabled as _modal_enabled
            from aegis.viewer.modal_proxy import trace_differt as _modal_trace_differt

            scene_dir = _Path(scene_path).parent
            scene_xml = _Path(scene_path).read_text()
            # Bundle mesh files so Modal has them
            scene_files = {}
            for f in scene_dir.rglob("*"):
                if f.is_file() and f.name != _Path(scene_path).name:
                    scene_files[str(f.relative_to(scene_dir))] = f.read_bytes()
            modal_result = _modal_trace_differt(
                scene_xml=scene_xml,
                scene_files=scene_files,
                tx_pos=antenna_pos.tolist(),
                rx_pos=body_center.tolist(),
                max_order=rt_cfg_parsed["max_depth"],
                freq_hz=tissue.freq_hz,
                tx_power_dbm=power_dbm,
                reflection_loss_per_order=rt_cfg_parsed["reflection_loss_per_order"],
                method=rt_cfg_parsed["method"],
                num_rays=rt_cfg_parsed["rays_per_source"],
                chunk_size=rt_cfg_parsed["chunk_size"],
            )
            if modal_result is None and _modal_enabled():
                modal_error = "Modal DiffeRT returned no result"
        except Exception as e:
            logger.error("Modal DiffeRT proxy attempt failed: %s", e, exc_info=True)
            from aegis.viewer.modal_proxy import _is_enabled as _modal_enabled

            if _modal_enabled():
                modal_error = str(e)

    if modal_result is not None:
        from aegis.paths import PropagationPaths

        paths = PropagationPaths.from_dict(modal_result["paths"])
        path_viz = modal_result["path_viz"]
        gpu_backend = modal_result.get("gpu_backend")
        rt_ms = modal_result.get("timings", {}).get("trace_ms")
    elif modal_error:
        # Modal is configured but failed - don't fall back to local CPU (OOM risk)
        return jsonify({"error": f"DiffeRT on Modal failed: {modal_error}"}), 503
    else:
        # Local DiffeRT: scene file, voxel hull, or environment mesh
        try:
            rt_kwargs = dict(
                tx_pos=antenna_pos,
                rx_pos=body_center,
                max_order=rt_cfg_parsed["max_depth"],
                freq_hz=tissue.freq_hz,
                tx_power_dbm=power_dbm,
                reflection_loss_per_order=rt_cfg_parsed["reflection_loss_per_order"],
                method=rt_cfg_parsed["method"],
                num_rays=rt_cfg_parsed["rays_per_source"],
                chunk_size=rt_cfg_parsed["chunk_size"],
            )
            if use_voxel_scene:
                from aegis.viewer.raytracer import get_or_build_voxel_scene
                from aegis.viewer.scene_data import extract_exterior, prepare_for_raytracing

                with cache_lock:
                    vp = cache["voxel_positions"]
                    vs = cache.get("voxel_sizes")
                    vm = cache.get("voxel_materials")
                    cfg = cache.get("config", {})

                z_up_pos, gc, dominant_size = prepare_for_raytracing(vp, vs)
                ext_mask = extract_exterior(gc)
                ext_pos = z_up_pos[ext_mask]
                ext_grid = gc[ext_mask]
                ext_mats = [vm[i] for i in np.nonzero(ext_mask)[0]] if vm is not None else None
                material_colors = cfg.get("voxels", {}).get("material_colors")

                voxel_scene = get_or_build_voxel_scene(
                    ext_pos,
                    ext_grid,
                    voxel_size=dominant_size,
                    materials=ext_mats,
                    material_colors=material_colors,
                )
                paths, path_viz = compute_paths_differt(**rt_kwargs, scene=voxel_scene)
            elif use_env_mesh:
                from aegis.environment.export import to_differt_scene

                with cache_lock:
                    env_mesh = scoped_cache_get(cache, "env_mesh")
                env_scene = to_differt_scene(env_mesh)
                paths, path_viz = compute_paths_differt(**rt_kwargs, scene=env_scene)
            else:
                paths, path_viz = compute_paths_differt(scene_path, **rt_kwargs)
        except Exception as e:
            return jsonify({"error": f"Ray tracing failed: {e}"}), 500
        rt_ms = None

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
