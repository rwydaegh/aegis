"""DiffeRT ray-traced dosimetry route."""

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
    _ERR_NO_DIFFERT,
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


def _resolve_rt_body(cache: dict, cache_lock, params: dict) -> tuple[Any, _ErrResp | None]:
    """Resolve the cached body mesh.

    Returns (body, None) on success or (None, error_response) on failure.
    """
    body_name = params.get("body_name", cache.get("default_body"))
    if body_name is not None and not isinstance(body_name, str):
        return None, (jsonify({"error": "body_name must be a string"}), 400)
    with cache_lock:
        entry = cache.get("bodies", {}).get(body_name)
    if entry is None:
        return None, (jsonify({"error": f"Body '{body_name}' not found"}), 404)
    return entry["body"], None


def _resolve_rt_source(cache: dict, cache_lock, scene_path: str | None) -> tuple[str | None, _ErrResp | None]:
    """Decide which geometry source to use for ray tracing.

    Returns (mode, None) where mode is one of "scene", "voxel", "env",
    or (None, error_response) on failure.
    """
    if scene_path:
        return "scene", None
    with cache_lock:
        has_voxels = cache.get("voxel_positions") is not None and len(cache.get("voxel_positions", [])) > 0
        has_env = scoped_cache_get(cache, "env_mesh") is not None
    if has_voxels:
        return "voxel", None
    if has_env:
        return "env", None
    return None, (jsonify({"error": "No scene, voxels, or environment loaded for ray tracing"}), 400)


def _parse_power_dbm(params: dict) -> tuple[float | None, _ErrResp | None]:
    """Parse and validate power_dbm for RT routes."""
    try:
        power_dbm = float(params.get("power_dbm", DEFAULT_POWER_DBM))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "power_dbm must be a number"}), 400)
    if not math.isfinite(power_dbm):
        return None, (jsonify({"error": "power_dbm must be a finite number"}), 400)
    if power_dbm < 0 or power_dbm > _MAX_POWER_DBM:
        return None, (jsonify({"error": f"power_dbm must be between 0 and {_MAX_POWER_DBM} dBm"}), 400)
    return power_dbm, None


def _collect_rt_params(cache: dict, params: dict) -> tuple[dict[str, Any] | None, _ErrResp | None]:
    """Parse all shared ray-trace route parameters.

    Returns (parsed_dict, None) or (None, error_response).
    """
    engine_kw, err = _parse_mode_or_level(params)
    if err:
        return None, err
    power_dbm, err = _parse_power_dbm(params)
    if err is not None:
        return None, err
    rt_cfg_parsed = _parse_rt_config(params, cache)

    body_offset, err = _parse_vec3(params, "body_offset")
    if err:
        return None, err
    body_rotation_y, err = _parse_rotation_y(params)
    if err:
        return None, err
    tissue, _, err = _parse_freq_and_tissue(params)
    if err:
        return None, err
    quantities, exposure_scenario, err = _parse_quantities_and_scenario(params)
    if err:
        return None, err

    return {
        "engine_kw": engine_kw,
        "power_dbm": power_dbm,
        "rt_cfg": rt_cfg_parsed,
        "body_offset": body_offset,
        "body_rotation_y": body_rotation_y,
        "tissue": tissue,
        "quantities": quantities,
        "exposure_scenario": exposure_scenario,
    }, None


def _try_modal_differt(scene_path: str, antenna_pos, body_center, tissue, power_dbm, rt_cfg):
    """Attempt ray-tracing on Modal GPU for a scene-file source.

    Returns (modal_result_or_None, modal_error_or_None). When both are None,
    Modal is disabled; the caller should fall back to local DiffeRT.
    """
    try:
        from pathlib import Path as _Path

        from aegis.viewer.modal_proxy import _is_enabled as _modal_enabled
        from aegis.viewer.modal_proxy import trace_differt as _modal_trace_differt

        scene_dir = _Path(scene_path).parent
        scene_xml = _Path(scene_path).read_text()
        scene_files = {}
        for f in scene_dir.rglob("*"):
            if f.is_file() and f.name != _Path(scene_path).name:
                scene_files[str(f.relative_to(scene_dir))] = f.read_bytes()
        modal_result = _modal_trace_differt(
            scene_xml=scene_xml,
            scene_files=scene_files,
            tx_pos=antenna_pos.tolist(),
            rx_pos=body_center.tolist(),
            max_order=rt_cfg["max_depth"],
            freq_hz=tissue.freq_hz,
            tx_power_dbm=power_dbm,
            reflection_loss_per_order=rt_cfg["reflection_loss_per_order"],
            method=rt_cfg["method"],
            num_rays=rt_cfg["rays_per_source"],
            chunk_size=rt_cfg["chunk_size"],
        )
        if modal_result is None and _modal_enabled():
            return None, "Modal DiffeRT returned no result"
        return modal_result, None
    except Exception as e:
        logger.error("Modal DiffeRT proxy attempt failed: %s", e, exc_info=True)
        from aegis.viewer.modal_proxy import _is_enabled as _modal_enabled

        if _modal_enabled():
            return None, str(e)
        return None, None


def _build_voxel_scene(cache: dict, cache_lock):
    """Build a voxel-hull DiffeRT scene from cache."""
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


def _trace_local_differt(
    source_mode, cache, cache_lock, scene_path, rt_kwargs
) -> tuple[tuple[Any, Any] | None, _ErrResp | None]:
    """Run local DiffeRT against a scene file, voxel hull or environment mesh.

    Returns ((paths, path_viz), None) on success or (None, error_response) on failure.
    """
    from aegis.viewer.raytracer import compute_paths_differt

    try:
        if source_mode == "voxel":
            voxel_scene = _build_voxel_scene(cache, cache_lock)
            return compute_paths_differt(**rt_kwargs, scene=voxel_scene), None
        if source_mode == "env":
            from aegis.environment.export import to_differt_scene

            with cache_lock:
                env_mesh = scoped_cache_get(cache, "env_mesh")
            if env_mesh is None:
                return None, (jsonify({"error": "No environment mesh loaded"}), 400)
            env_scene = to_differt_scene(env_mesh)
            return compute_paths_differt(**rt_kwargs, scene=env_scene), None
        return compute_paths_differt(scene_path, **rt_kwargs), None
    except Exception as e:
        return None, (jsonify({"error": f"Ray tracing failed: {e}"}), 500)


def _trace_paths(
    source_mode, cache, cache_lock, scene_path, antenna_pos, body_center, tissue, power_dbm, rt_cfg
) -> tuple[Any, Any, str | None, float | None, _ErrResp | None]:
    """Run ray tracing via Modal or local fallback.

    Returns (paths, path_viz, gpu_backend, rt_ms, None) on success or
    (None, None, None, None, error_response) on failure.
    """
    modal_result = None
    modal_error = None
    if source_mode == "scene":
        modal_result, modal_error = _try_modal_differt(scene_path, antenna_pos, body_center, tissue, power_dbm, rt_cfg)

    if modal_result is not None:
        from aegis.paths import PropagationPaths

        paths = PropagationPaths.from_dict(modal_result["paths"])
        path_viz = modal_result["path_viz"]
        gpu_backend = modal_result.get("gpu_backend")
        rt_ms = modal_result.get("timings", {}).get("trace_ms")
        return paths, path_viz, gpu_backend, rt_ms, None

    if modal_error:
        return None, None, None, None, (jsonify({"error": f"DiffeRT on Modal failed: {modal_error}"}), 503)

    rt_kwargs = dict(
        tx_pos=antenna_pos,
        rx_pos=body_center,
        max_order=rt_cfg["max_depth"],
        freq_hz=tissue.freq_hz,
        tx_power_dbm=power_dbm,
        reflection_loss_per_order=rt_cfg["reflection_loss_per_order"],
        method=rt_cfg["method"],
        num_rays=rt_cfg["rays_per_source"],
        chunk_size=rt_cfg["chunk_size"],
    )
    traced, err = _trace_local_differt(source_mode, cache, cache_lock, scene_path, rt_kwargs)
    if err is not None:
        return None, None, None, None, err
    assert traced is not None  # noqa: S101 - helper contract
    paths, path_viz = traced
    return paths, path_viz, None, None, None


def _api_compute_rt_impl(cache: dict, cache_lock) -> RouteResponse:
    """Compute dosimetry using DiffeRT ray-traced paths."""
    try:
        from aegis.viewer.raytracer import compute_paths_differt as _  # noqa: F401
    except ImportError:
        return jsonify({"error": _ERR_NO_DIFFERT}), 501

    from aegis.viewer.compute import _transform_body_for_viewer

    params = request.get_json(silent=True)
    if not isinstance(params, dict):
        return jsonify({"error": _ERR_INVALID_JSON}), 400

    body, err = _resolve_rt_body(cache, cache_lock, params)
    if err is not None:
        return err
    assert body is not None  # noqa: S101 - helper contract

    antenna_pos, err = _parse_vec3(params, "antenna_pos", [5, 0, 1])
    if err:
        return err
    assert antenna_pos is not None  # noqa: S101 - helper contract

    scene_path = params.get("scene_path") or None
    if scene_path and not _validate_scene_path(scene_path):
        return jsonify({"error": _ERR_INVALID_SCENE}), 400

    source_mode, err = _resolve_rt_source(cache, cache_lock, scene_path)
    if err is not None:
        return err
    assert source_mode is not None  # noqa: S101 - helper contract

    pp, err = _collect_rt_params(cache, params)
    if err is not None:
        return err
    assert pp is not None  # noqa: S101 - helper contract

    # RT receiver: use configured default center (z=1m) shifted by body offset
    # (body centroid mean is ~z=-0.38, below floors of most Sionna scenes)
    default_bc = np.array(cache["config"]["raytracer"]["default_body_center"])
    body_center = default_bc + pp["body_offset"]

    transformed_body = _transform_body_for_viewer(body, pp["body_offset"], pp["body_rotation_y"])

    import time as _time

    t_route = _time.perf_counter()

    from aegis.viewer.modal_proxy import gpu_status as _gpu_status

    _was_cold = not _gpu_status().get("warm", False)

    paths, path_viz, gpu_backend, rt_ms, err = _trace_paths(
        source_mode,
        cache,
        cache_lock,
        scene_path,
        antenna_pos,
        body_center,
        pp["tissue"],
        pp["power_dbm"],
        pp["rt_cfg"],
    )
    if err is not None:
        return err
    assert paths is not None  # noqa: S101 - helper contract

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
