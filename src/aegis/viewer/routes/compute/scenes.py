"""Scene listing, scene load, and voxel hull mesh routes."""

from __future__ import annotations

import json

import numpy as np
from flask import Response, jsonify, request

from aegis.viewer.routes._types import RouteResponse

from ._parsing import _ERR_INVALID_SCENE
from ._responses import _ERR_NO_DIFFERT, _OCTET_STREAM


def _validate_scene_path(scene_path: str) -> bool:
    """Proxy to package-level `_validate_scene_path` so tests can mock it."""
    from aegis.viewer.routes import compute as _pkg

    return _pkg._validate_scene_path(scene_path)


def _api_scenes_impl(cache: dict, cache_lock) -> RouteResponse:
    """List available Sionna XML scenes for DiffeRT ray tracing."""
    try:
        from aegis.viewer.raytracer import list_available_scenes

        return jsonify(list_available_scenes())
    except ImportError:
        return jsonify({"error": _ERR_NO_DIFFERT}), 501


def _api_scene_load_impl(cache: dict, cache_lock) -> RouteResponse:
    """Load a Sionna scene and return its geometry for Three.js."""
    try:
        from aegis.viewer.raytracer import load_scene, scene_geometry_to_binary
    except ImportError:
        return jsonify({"error": _ERR_NO_DIFFERT}), 501

    params = request.get_json(silent=True)
    if not isinstance(params, dict):
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    scene_path = params.get("path")
    if not scene_path:
        return jsonify({"error": "Missing 'path' parameter"}), 400
    if not _validate_scene_path(scene_path):
        return jsonify({"error": _ERR_INVALID_SCENE}), 400

    try:
        scene_data = load_scene(scene_path)
        data, meta = scene_geometry_to_binary(scene_data)
        resp = Response(data, mimetype=_OCTET_STREAM)
        resp.headers["X-Meta"] = json.dumps(meta)
        resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _api_voxels_hull_mesh_impl(cache: dict, cache_lock) -> RouteResponse:
    """Exterior voxel hull as triangle soup (same geometry as voxel DiffeRT)."""
    try:
        from aegis.viewer.raytracer import get_or_build_voxel_scene, scene_geometry_to_binary
    except ImportError:
        return jsonify({"error": _ERR_NO_DIFFERT}), 501

    with cache_lock:
        voxel_positions = cache.get("voxel_positions")
        voxel_sizes = cache.get("voxel_sizes")
        voxel_materials = cache.get("voxel_materials")
        cfg = cache.get("config", {})
    if voxel_positions is None or len(voxel_positions) == 0:
        return jsonify({"error": "No voxel data"}), 400
    if voxel_sizes is None:
        return jsonify({"error": "No voxel_sizes in cache"}), 400

    from aegis.viewer.scene_data import extract_exterior, prepare_for_raytracing

    z_up_pos, grid_coords, vs = prepare_for_raytracing(voxel_positions, voxel_sizes)
    ext_mask = extract_exterior(grid_coords)
    ext_grid = grid_coords[ext_mask]
    ext_pos = z_up_pos[ext_mask]

    ext_materials = None
    if voxel_materials is not None:
        ext_materials = [voxel_materials[i] for i in np.nonzero(ext_mask)[0]]
    material_colors = cfg.get("voxels", {}).get("material_colors")

    try:
        scene = get_or_build_voxel_scene(
            ext_pos,
            ext_grid,
            voxel_size=vs,
            materials=ext_materials,
            material_colors=material_colors,
        )
        mesh = scene.mesh
        vertices = np.array(mesh.vertices)
        triangles = np.array(mesh.triangles)
        mnames = list(mesh.material_names) if mesh.material_names else []
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    scene_data = {
        "vertices": vertices,
        "triangles": triangles,
        "face_colors": np.array(mesh.face_colors),
        "n_vertices": int(len(vertices)),
        "n_triangles": int(len(triangles)),
        "material_names": mnames,
    }
    data, meta = scene_geometry_to_binary(scene_data)
    resp = Response(data, mimetype=_OCTET_STREAM)
    resp.headers["X-Meta"] = json.dumps(meta)
    resp.headers["Access-Control-Expose-Headers"] = "X-Meta"
    return resp
