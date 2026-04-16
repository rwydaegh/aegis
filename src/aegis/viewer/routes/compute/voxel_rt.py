"""Sionna RT on voxel environment route."""

from __future__ import annotations

import logging

import numpy as np
from flask import Response, jsonify, request

from aegis.defaults import DEFAULT_POWER_DBM

from ._parsing import (
    _ERR_INVALID_JSON,
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


def _run_dosimetry(tissue, body, paths, engine_kw):
    """Proxy to package-level `_run_dosimetry` so tests can mock it."""
    from aegis.viewer.routes import compute as _pkg

    return _pkg._run_dosimetry(tissue, body, paths, engine_kw)


def _api_compute_voxel_rt_impl(cache: dict, cache_lock) -> Response:
    """Compute dosimetry using Sionna RT on the voxel environment geometry (via Modal GPU)."""
    from aegis.viewer.compute import _transform_body_for_viewer

    params = request.get_json(silent=True)
    if not isinstance(params, dict):
        return jsonify({"error": _ERR_INVALID_JSON}), 400

    body_name = params.get("body_name", cache.get("default_body"))
    with cache_lock:
        entry = cache.get("bodies", {}).get(body_name)
        voxel_positions = cache.get("voxel_positions")
        voxel_sizes = cache.get("voxel_sizes")
        voxel_materials = cache.get("voxel_materials")
        cfg = cache["config"]
    if entry is None:
        return jsonify({"error": f"Body '{body_name}' not found"}), 404
    body = entry["body"]

    if voxel_positions is None or len(voxel_positions) == 0:
        return jsonify({"error": "No voxel data available"}), 400

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

    # Prepare voxel mesh data for Modal
    max_rt_triangles = cfg["raytracer"]["max_rt_triangles"]
    try:
        from aegis.viewer.scene_data import extract_exterior, prepare_for_raytracing

        z_up_pos, grid_coords, vs = prepare_for_raytracing(voxel_positions, voxel_sizes)
        ext_mask = extract_exterior(grid_coords)
        ext_pos = z_up_pos[ext_mask]

        ext_materials = None
        if voxel_materials is not None:
            ext_materials = [voxel_materials[i] for i in np.nonzero(ext_mask)[0]]

        # Pre-triangulate using greedy mesher (sends ~8x fewer triangles)
        from aegis.viewer.raytracer import get_or_build_voxel_scene

        ext_grid = grid_coords[ext_mask]
        material_colors = cfg.get("voxels", {}).get("material_colors")
        voxel_scene = get_or_build_voxel_scene(
            ext_pos,
            ext_grid,
            voxel_size=vs,
            materials=ext_materials,
            material_colors=material_colors,
        )
        hull_verts = np.array(voxel_scene.mesh.vertices)
        hull_tris = np.array(voxel_scene.mesh.triangles)

        actual_triangles = len(hull_tris)
        if actual_triangles > max_rt_triangles and max_order > 0:
            return jsonify(
                {
                    "error": f"Scene too large for reflections ({actual_triangles:,} triangles, "
                    f"limit {max_rt_triangles:,}). Use LOS only (order 0) or reduce scene size."
                }
            ), 400

        # Build per-face material names for Sionna BSDF assignment
        face_mats_idx = np.array(voxel_scene.mesh.face_materials)
        mat_names_tuple = voxel_scene.mesh.material_names
        per_face_mats = [mat_names_tuple[int(i)] for i in face_mats_idx]
    except Exception as e:
        return jsonify({"error": f"Voxel mesh build failed: {e}"}), 500

    # Call Modal GPU for Sionna RT on voxel geometry
    import hashlib

    from aegis.viewer.modal_proxy import gpu_status as _gpu_status
    from aegis.viewer.modal_proxy import trace_sionna_voxel as _modal_trace_voxel

    _was_cold = not _gpu_status().get("warm", False)

    voxel_hash = hashlib.md5(np.asarray(voxel_positions).tobytes()).hexdigest()[:12]
    scene_key = f"voxel_{voxel_hash}"

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
        return jsonify(
            {"error": "Voxel ray tracing with Sionna is not yet implemented. Mesh-to-scene conversion is pending."}
        ), 501

    if modal_result is None:
        return jsonify({"error": "GPU unavailable for voxel ray tracing"}), 501

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

    extra["backend"] = "sionna-voxel"
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
