"""Sionna RT on voxel environment route."""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
from flask import Response, jsonify, request

from aegis.defaults import DEFAULT_POWER_DBM
from aegis.viewer.routes._types import RouteResponse

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

_ErrResp = tuple[Response, int]


def _run_dosimetry(tissue, body, paths, engine_kw, **kwargs) -> tuple[Any, _ErrResp | None]:
    """Proxy to package-level `_run_dosimetry` so tests can mock it."""
    from aegis.viewer.routes import compute as _pkg

    return _pkg._run_dosimetry(tissue, body, paths, engine_kw, **kwargs)


def _load_voxel_request(
    cache: dict, cache_lock, params: dict
) -> tuple[tuple[Any, Any, Any, Any, Any] | None, _ErrResp | None]:
    """Fetch body mesh + voxel data from the cache.

    Returns ((body, voxel_positions, voxel_sizes, voxel_materials, cfg), None) on success
    or (None, error_response) on failure.
    """
    body_name = params.get("body_name", cache.get("default_body"))
    with cache_lock:
        entry = cache.get("bodies", {}).get(body_name)
        voxel_positions = cache.get("voxel_positions")
        voxel_sizes = cache.get("voxel_sizes")
        voxel_materials = cache.get("voxel_materials")
        cfg = cache["config"]
    if entry is None:
        return None, (jsonify({"error": f"Body '{body_name}' not found"}), 404)
    if voxel_positions is None or len(voxel_positions) == 0:
        return None, (jsonify({"error": "No voxel data available"}), 400)
    return (entry["body"], voxel_positions, voxel_sizes, voxel_materials, cfg), None


def _parse_voxel_rt_params(params: dict, cache: dict) -> tuple[dict[str, Any] | None, _ErrResp | None]:
    """Parse shared RT params for the voxel-RT route.

    Returns (parsed_dict, None) or (None, error_response).
    """
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
    try:
        power_dbm = float(params.get("power_dbm", DEFAULT_POWER_DBM))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "power_dbm must be a number"}), 400)
    if not math.isfinite(power_dbm):
        return None, (jsonify({"error": "power_dbm must be a finite number"}), 400)
    if power_dbm < 0 or power_dbm > _MAX_POWER_DBM:
        return None, (jsonify({"error": f"power_dbm must be between 0 and {_MAX_POWER_DBM} dBm"}), 400)
    rt_cfg_parsed = _parse_rt_config(params, cache)

    quantities, exposure_scenario, err = _parse_quantities_and_scenario(params)
    if err:
        return None, err
    tissue, _, err = _parse_freq_and_tissue(params)
    if err:
        return None, err

    return {
        "antenna_pos": antenna_pos,
        "body_offset": body_offset,
        "body_rotation_y": body_rotation_y,
        "engine_kw": engine_kw,
        "power_dbm": power_dbm,
        "rt_cfg": rt_cfg_parsed,
        "quantities": quantities,
        "exposure_scenario": exposure_scenario,
        "tissue": tissue,
    }, None


def _build_voxel_rt_scene(
    voxel_positions, voxel_sizes, voxel_materials, cfg, max_order: int, max_rt_triangles: int
) -> tuple[dict[str, Any] | None, _ErrResp | None]:
    """Build the voxel RT scene hull + per-face material list for Modal Sionna.

    Returns (scene_dict, None) on success or (None, error_response) on failure.
    """
    try:
        from aegis.viewer.scene_data import extract_exterior, prepare_for_raytracing

        z_up_pos, grid_coords, vs = prepare_for_raytracing(voxel_positions, voxel_sizes)
        ext_mask = extract_exterior(grid_coords)
        ext_pos = z_up_pos[ext_mask]

        ext_materials = None
        if voxel_materials is not None:
            ext_materials = [voxel_materials[i] for i in np.nonzero(ext_mask)[0]]

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
            return None, (
                jsonify(
                    {
                        "error": f"Scene too large for reflections ({actual_triangles:,} triangles, "
                        f"limit {max_rt_triangles:,}). Use LOS only (order 0) or reduce scene size."
                    }
                ),
                400,
            )

        face_mats_idx = np.array(voxel_scene.mesh.face_materials)
        mat_names_tuple = voxel_scene.mesh.material_names
        per_face_mats = [mat_names_tuple[int(i)] for i in face_mats_idx]
        return {
            "vertices": hull_verts.tolist(),
            "triangles": hull_tris.tolist(),
            "materials": per_face_mats,
        }, None
    except Exception as e:
        return None, (jsonify({"error": f"Voxel mesh build failed: {e}"}), 500)


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


def _invoke_modal_voxel_trace(
    voxel_positions, scene_data, antenna_pos, body_center, max_order, tissue, power_dbm, rt_cfg_dict
) -> tuple[dict[str, Any] | None, _ErrResp | None]:
    """Call Modal trace_sionna_voxel with an appropriate scene key.

    Returns (modal_result, None) on success or (None, error_response) on failure.
    """
    import hashlib

    from aegis.viewer.modal_proxy import trace_sionna_voxel as _modal_trace_voxel

    voxel_hash = hashlib.md5(np.asarray(voxel_positions).tobytes()).hexdigest()[:12]
    scene_key = f"voxel_{voxel_hash}"

    try:
        modal_result = _modal_trace_voxel(
            scene_key=scene_key,
            scene_data=scene_data,
            tx_pos=antenna_pos.tolist(),
            rx_pos=body_center.tolist(),
            max_bounces=max_order,
            freq_hz=tissue.freq_hz,
            tx_power_dbm=power_dbm,
            rt_config=rt_cfg_dict,
        )
    except NotImplementedError:
        return None, (
            jsonify(
                {"error": "Voxel ray tracing with Sionna is not yet implemented. Mesh-to-scene conversion is pending."}
            ),
            501,
        )
    if modal_result is None:
        return None, (jsonify({"error": "GPU unavailable for voxel ray tracing"}), 501)
    return modal_result, None


def _api_compute_voxel_rt_impl(cache: dict, cache_lock) -> RouteResponse:
    """Compute dosimetry using Sionna RT on the voxel environment geometry (via Modal GPU)."""
    from aegis.viewer.compute import _transform_body_for_viewer

    params = request.get_json(silent=True)
    if not isinstance(params, dict):
        return jsonify({"error": _ERR_INVALID_JSON}), 400

    loaded, err = _load_voxel_request(cache, cache_lock, params)
    if err is not None:
        return err
    assert loaded is not None  # noqa: S101 - helper contract
    body, voxel_positions, voxel_sizes, voxel_materials, cfg = loaded

    pp, err = _parse_voxel_rt_params(params, cache)
    if err is not None:
        return err
    assert pp is not None  # noqa: S101 - helper contract

    transformed_body = _transform_body_for_viewer(body, pp["body_offset"], pp["body_rotation_y"])
    body_center = transformed_body.centroids.mean(axis=0)

    import time as _time

    t_route = _time.perf_counter()

    max_order = pp["rt_cfg"]["max_depth"]
    max_rt_triangles = cfg["raytracer"]["max_rt_triangles"]

    scene_data, err = _build_voxel_rt_scene(
        voxel_positions, voxel_sizes, voxel_materials, cfg, max_order, max_rt_triangles
    )
    if err is not None:
        return err
    assert scene_data is not None  # noqa: S101 - helper contract

    from aegis.viewer.modal_proxy import gpu_status as _gpu_status

    _was_cold = not _gpu_status().get("warm", False)

    rt_cfg_dict = _sionna_rt_config(pp["rt_cfg"])

    modal_result, err = _invoke_modal_voxel_trace(
        voxel_positions,
        scene_data,
        pp["antenna_pos"],
        body_center,
        max_order,
        pp["tissue"],
        pp["power_dbm"],
        rt_cfg_dict,
    )
    if err is not None:
        return err
    assert modal_result is not None  # noqa: S101 - helper contract

    from aegis.paths import PropagationPaths

    paths = PropagationPaths.from_dict(modal_result["paths"])
    path_viz = modal_result["path_viz"]
    gpu_backend = modal_result.get("gpu_backend")
    rt_ms = modal_result.get("timings", {}).get("trace_ms")

    t_rt = _time.perf_counter()

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

    dist = float(np.linalg.norm(pp["antenna_pos"] - body_center))
    extra = {
        "S_inc": float(np.sum(paths.power)),
        "distance_m": dist,
        "n_rt_paths": paths.n_paths,
        "path_viz": path_viz,
        "backend": "sionna-voxel",
        "cold_start": _was_cold,
    }
    if gpu_backend is not None:
        extra["gpu_backend"] = gpu_backend
    if ecbf_warnings:
        extra["ecbf_warnings"] = ecbf_warnings

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
