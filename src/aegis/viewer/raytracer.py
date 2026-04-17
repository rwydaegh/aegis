"""DiffeRT ray tracing integration for the interactive viewer.

Loads Sionna XML scenes, computes propagation paths from antenna to body,
and converts them to AEGIS PropagationPaths.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
from aegis.paths import PropagationPaths

logger = logging.getLogger(__name__)

_DEFAULT_FSPL_DISTANCE_CLAMP_M = 0.01


def isotropic_incident_power_density(
    tx_power_w: float,
    path_length_m: float,
    *,
    min_distance_m: float = _DEFAULT_FSPL_DISTANCE_CLAMP_M,
) -> float:
    """Spherical spreading: S = P_tx / (4 pi d^2) [W/m^2] for an isotropic radiator."""
    d = max(float(path_length_m), float(min_distance_m))
    return tx_power_w / (4.0 * np.pi * d * d)


def _check_differt() -> None:
    try:
        import differt  # noqa: F401
    except ImportError as exc:
        raise ImportError("DiffeRT is required for ray tracing. Install with: pip install aegis[rt]") from exc


# Cache loaded scenes (expensive to parse)
_scene_cache: dict = {}


_voxel_scene_cache: dict = {}
_voxel_scene_cache_lock = threading.Lock()


def clear_voxel_scene_cache() -> None:
    """Invalidate cached DiffeRT scenes built from voxels (call after reloading voxel data)."""
    with _voxel_scene_cache_lock:
        _voxel_scene_cache.clear()


def list_available_scenes(scenes_dir: str | Path | None = None) -> list[dict]:
    """List available Sionna XML scenes.

    Returns list of dicts with keys: name, path.
    Checks: SIONNA_SCENES_DIR env var, sionna package, then bundled data/scenes/.
    """
    if scenes_dir is None:
        # Try sources in priority order: env var, sionna package, bundled data/scenes/
        candidates: list[Path] = []
        env_dir = os.environ.get("SIONNA_SCENES_DIR")
        if env_dir:
            candidates.append(Path(env_dir))
        try:
            import importlib.util

            spec = importlib.util.find_spec("sionna.rt")
            if spec and spec.origin:
                candidates.append(Path(spec.origin).parent / "scenes")
        except Exception:
            pass
        candidates.append(Path(__file__).resolve().parents[3] / "data" / "scenes")
        candidates.append(Path.cwd() / "data" / "scenes")

        for candidate in candidates:
            if candidate.is_dir():
                scenes_dir = candidate
                break
        else:
            return []

    scenes_dir = Path(scenes_dir)
    if not scenes_dir.exists():
        return []

    results = []
    for xml_file in sorted(scenes_dir.rglob("*.xml")):
        if "checkpoint" in str(xml_file):
            continue
        name = xml_file.parent.name
        results.append(
            {
                "name": name,
                "path": str(xml_file),
            }
        )

    return results


def load_scene(scene_path: str | Path) -> dict:
    """Load a Sionna XML scene with DiffeRT.

    Returns dict with scene object and geometry for Three.js rendering.
    """
    _check_differt()

    scene_path = str(scene_path)
    if scene_path in _scene_cache:
        return _scene_cache[scene_path]

    from differt.scene import TriangleScene

    scene = TriangleScene.load_xml(scene_path)
    mesh = scene.mesh

    vertices = np.array(mesh.vertices)
    triangles = np.array(mesh.triangles)
    face_colors = np.array(mesh.face_colors) if mesh.face_colors is not None else None

    result = {
        "scene": scene,
        "vertices": vertices,
        "triangles": triangles,
        "face_colors": face_colors,
        "n_vertices": len(vertices),
        "n_triangles": len(triangles),
        "material_names": list(mesh.material_names) if mesh.material_names else [],
    }

    _scene_cache[scene_path] = result
    return result


_ZERO3 = np.zeros(3)


def compute_paths_differt(
    scene_path: str | Path | None = None,
    tx_pos: np.ndarray = _ZERO3,
    rx_pos: np.ndarray = _ZERO3,
    max_order: int = 1,
    freq_hz: float = DEFAULT_FREQ_HZ,
    tx_power_dbm: float = DEFAULT_POWER_DBM,
    reflection_loss_per_order: float = 0.5,
    method: str = "exhaustive",
    num_rays: int = 1_000_000,
    chunk_size: int | None = None,
    *,
    scene: Any | None = None,
    # NOTE: Uses from_powers() with scalar power only. Polarisation direction
    # is irrelevant here because the viewer runs incoherent levels (0-6) where
    # only |psi|^2 matters. For coherent levels (7-8) with proper TE/TM
    # tracking, use aegis.integration.differt.paths_from_differt_scene().
) -> tuple[PropagationPaths, list[dict]]:
    """Run DiffeRT ray tracing and return AEGIS PropagationPaths.

    Parameters
    ----------
    scene_path : path to Sionna XML scene (mutually exclusive with scene)
    tx_pos : (3,) transmitter position [m]
    rx_pos : (3,) receiver (body center) position [m]
    max_order : max number of reflections (0=LOS only, 1=+single reflection, etc.)
    freq_hz : frequency [Hz]
    tx_power_dbm : transmit power [dBm]
    scene : pre-built DiffeRT TriangleScene (alternative to scene_path)

    Returns
    -------
    (paths, path_viz_data) where path_viz_data is a list of dicts
    with 'vertices' key for Three.js line rendering.
    """
    _check_differt()

    import equinox as eqx
    import jax.numpy as jnp

    if scene is not None:
        scene_obj = scene
    elif scene_path is not None:
        scene_data = load_scene(scene_path)
        scene_obj = scene_data["scene"]
    else:
        raise ValueError("Either scene_path or scene must be provided")

    tx = jnp.array([tx_pos.tolist()])
    rx = jnp.array([rx_pos.tolist()])

    scene_obj = eqx.tree_at(lambda s: s.transmitters, scene_obj, tx)
    scene_obj = eqx.tree_at(lambda s: s.receivers, scene_obj, rx)

    # Collect paths from all orders
    all_k_hat = []
    all_power = []
    path_viz = []

    tx_power_w = 10 ** ((tx_power_dbm - 30) / 10)

    # chunk_size only applies to exhaustive/hybrid; ignored for SBR
    use_chunk_size = chunk_size if method in ("exhaustive", "hybrid") else None

    for order in range(max_order + 1):
        try:
            paths_result = scene_obj.compute_paths(
                order=order,
                method=method,
                num_rays=num_rays,
                chunk_size=use_chunk_size,
            )
        except Exception as e:
            logger.warning("Bounce order %d failed, skipping: %s", order, e)
            continue

        # When chunk_size is set, compute_paths returns an iterator of Paths
        paths_iter = paths_result if use_chunk_size else [paths_result]

        for paths in paths_iter:
            verts = np.array(paths.vertices)
            mask = np.array(paths.mask)

            # Flatten batch dimensions
            flat_v = verts.reshape(-1, verts.shape[-2], verts.shape[-1])
            flat_m = mask.flatten()

            for i in range(len(flat_v)):
                if i >= len(flat_m) or not flat_m[i]:
                    continue

                path_verts = flat_v[i]  # (order+2, 3)

                # Skip degenerate paths
                segments = np.diff(path_verts, axis=0)
                seg_lengths = np.linalg.norm(segments, axis=1)
                total_length = float(np.sum(seg_lengths))
                if total_length < 1e-6:
                    continue

                # k_hat: direction of last segment (arrival at RX)
                last_seg = segments[-1]
                k_hat = last_seg / np.linalg.norm(last_seg)
                all_k_hat.append(k_hat)

                # Match paths_from_differt: S_inc = P_tx / (4 pi d^2) for isotropic spreading
                reflection_loss = reflection_loss_per_order**order
                S_inc = isotropic_incident_power_density(tx_power_w, total_length) * reflection_loss
                all_power.append(S_inc)

                # Visualization data
                path_viz.append(
                    {
                        "vertices": path_verts.tolist(),
                        "order": order,
                        "length": total_length,
                    }
                )

    if not all_k_hat:
        # No paths found, return empty
        return PropagationPaths.from_powers(k_hat=np.zeros((0, 3)), power=np.zeros(0)), []

    k_hat = np.array(all_k_hat)
    power = np.array(all_power)

    paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

    return paths, path_viz


# Mapping from face direction index to (u_axis, v_axis, fixed_axis) indices
# and the sign of the fixed-axis offset (+hs or -hs).
_FACE_UV_MAP = [
    (1, 2, 0, +1),  # +X: u=y, v=z, fixed=x at +hs
    (1, 2, 0, -1),  # -X: u=y, v=z, fixed=x at -hs
    (0, 2, 1, +1),  # +Y: u=x, v=z, fixed=y at +hs
    (0, 2, 1, -1),  # -Y: u=x, v=z, fixed=y at -hs
    (0, 1, 2, +1),  # +Z: u=x, v=y, fixed=z at +hs
    (0, 1, 2, -1),  # -Z: u=x, v=y, fixed=z at -hs
]

# Winding templates: 4 corners in (u, v) space producing outward-facing normals.
_FACE_WINDING = [
    [(0, 0), (1, 0), (1, 1), (0, 1)],  # +X
    [(0, 1), (1, 1), (1, 0), (0, 0)],  # -X
    [(0, 0), (0, 1), (1, 1), (1, 0)],  # +Y
    [(1, 0), (1, 1), (0, 1), (0, 0)],  # -Y
    [(0, 0), (1, 0), (1, 1), (0, 1)],  # +Z
    [(0, 1), (1, 1), (1, 0), (0, 0)],  # -Z
]


def _best_rectangle_for_seed(
    mat_grid: np.ndarray,
    visited: np.ndarray,
    u: int,
    v: int,
    cur_mat: int,
) -> tuple[int, int]:
    """Return the largest-area (w, h) rectangle of matching unvisited cells starting at (u, v).

    Sweeps both u-first widening and v-first heightening; picks whichever is larger.
    """
    u_span, v_span = mat_grid.shape

    max_u = 1
    while u + max_u < u_span and mat_grid[u + max_u, v] == cur_mat and not visited[u + max_u, v]:
        max_u += 1

    max_v = 1
    while v + max_v < v_span and mat_grid[u, v + max_v] == cur_mat and not visited[u, v + max_v]:
        max_v += 1

    best_w, best_h, best_area = 1, 1, 1

    cur_h = max_v
    for cw in range(1, max_u + 1):
        col_h = 0
        while v + col_h < v_span and mat_grid[u + cw - 1, v + col_h] == cur_mat and not visited[u + cw - 1, v + col_h]:
            col_h += 1
        cur_h = min(cur_h, col_h)
        if cur_h == 0:
            break
        area = cw * cur_h
        if area > best_area:
            best_area, best_w, best_h = area, cw, cur_h

    cur_w = max_u
    for ch in range(1, max_v + 1):
        row_w = 0
        while u + row_w < u_span and mat_grid[u + row_w, v + ch - 1] == cur_mat and not visited[u + row_w, v + ch - 1]:
            row_w += 1
        cur_w = min(cur_w, row_w)
        if cur_w == 0:
            break
        area = cur_w * ch
        if area > best_area:
            best_area, best_w, best_h = area, cur_w, ch

    return best_w, best_h


def _emit_greedy_quad(
    u: int,
    v: int,
    w: int,
    h: int,
    fv: int,
    u_min: int,
    v_min: int,
    origin: np.ndarray,
    voxel_size: float,
    hs: float,
    u_ax: int,
    v_ax: int,
    f_ax: int,
    f_sign: int,
    winding: list[tuple[int, int]],
) -> np.ndarray:
    """Build the (4, 3) float32 quad for a greedy rectangle."""
    gu0, gv0 = u + u_min, v + v_min
    u_lo = origin[u_ax] + gu0 * voxel_size - hs
    u_hi = origin[u_ax] + (gu0 + w) * voxel_size - hs
    v_lo = origin[v_ax] + gv0 * voxel_size - hs
    v_hi = origin[v_ax] + (gv0 + h) * voxel_size - hs
    f_val = origin[f_ax] + fv * voxel_size + f_sign * hs

    u_vals = [u_lo, u_hi]
    v_vals = [v_lo, v_hi]
    quad = np.zeros((4, 3), dtype=np.float32)
    for ci, (ui, vi) in enumerate(winding):
        quad[ci, u_ax] = u_vals[ui]
        quad[ci, v_ax] = v_vals[vi]
        quad[ci, f_ax] = f_val
    return quad


def _mesh_slice(
    slice_gc: np.ndarray,
    slice_mat: np.ndarray,
    fv: int,
    origin: np.ndarray,
    voxel_size: float,
    hs: float,
    u_ax: int,
    v_ax: int,
    f_ax: int,
    f_sign: int,
    winding: list[tuple[int, int]],
    out_verts: list[np.ndarray],
    out_mats: list[int],
) -> None:
    """Greedy-merge one (u, v) slice at fixed axis value fv."""
    u_coords = slice_gc[:, u_ax].astype(np.intp)
    v_coords = slice_gc[:, v_ax].astype(np.intp)
    u_min, u_max = int(u_coords.min()), int(u_coords.max())
    v_min, v_max = int(v_coords.min()), int(v_coords.max())
    u_span = u_max - u_min + 1
    v_span = v_max - v_min + 1

    mat_grid = np.full((u_span, v_span), -1, dtype=np.int32)
    mat_grid[u_coords - u_min, v_coords - v_min] = slice_mat
    visited = np.zeros((u_span, v_span), dtype=bool)

    for u in range(u_span):
        for v in range(v_span):
            cur_mat = int(mat_grid[u, v])
            if cur_mat < 0 or visited[u, v]:
                continue
            w, h = _best_rectangle_for_seed(mat_grid, visited, u, v, cur_mat)
            visited[u : u + w, v : v + h] = True
            out_verts.append(
                _emit_greedy_quad(
                    u,
                    v,
                    w,
                    h,
                    fv,
                    u_min,
                    v_min,
                    origin,
                    voxel_size,
                    hs,
                    u_ax,
                    v_ax,
                    f_ax,
                    f_sign,
                    winding,
                )
            )
            out_mats.append(cur_mat)


def _mesh_direction(
    d: int,
    gc_shifted: np.ndarray,
    ix: np.ndarray,
    iy: np.ndarray,
    iz: np.ndarray,
    occ: np.ndarray,
    mat_grid_3d: np.ndarray,
    origin: np.ndarray,
    voxel_size: float,
    hs: float,
    face_dirs: np.ndarray,
    out_verts: list[np.ndarray],
    out_mats: list[int],
) -> None:
    """Greedy-mesh all exposed faces pointing in direction d (0..5)."""
    dx, dy, dz = int(face_dirs[d, 0]), int(face_dirs[d, 1]), int(face_dirs[d, 2])
    exposed_mask = ~occ[ix + dx, iy + dy, iz + dz]
    exposed_idx = np.where(exposed_mask)[0]
    if len(exposed_idx) == 0:
        return

    u_ax, v_ax, f_ax, f_sign = _FACE_UV_MAP[d]
    winding = _FACE_WINDING[d]

    exposed_gc = gc_shifted[exposed_idx]
    exposed_mat = mat_grid_3d[ix[exposed_idx], iy[exposed_idx], iz[exposed_idx]]
    fixed_vals = exposed_gc[:, f_ax]

    for fv in np.unique(fixed_vals):
        slice_mask = fixed_vals == fv
        _mesh_slice(
            exposed_gc[slice_mask],
            exposed_mat[slice_mask],
            int(fv),
            origin,
            voxel_size,
            hs,
            u_ax,
            v_ax,
            f_ax,
            f_sign,
            winding,
            out_verts,
            out_mats,
        )


def _greedy_mesh_faces(
    grid_coords: np.ndarray,
    positions: np.ndarray,
    voxel_size: float,
    material_ids: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Emit greedy-merged quad vertices using a maximal-area rectangle heuristic.

    For each seed cell, finds the largest-area rectangle by sweeping widths
    and heights and tracking the best area. Produces squarer, larger quads
    than a pure u-first greedy sweep. Only merges adjacent faces that share
    the same material.

    Returns (vertices, quad_material_ids) where vertices is (M, 3) float32
    (every 4 consecutive vertices form one quad) and quad_material_ids is
    (M//4,) int32 with the material index for each quad.
    """
    hs = voxel_size / 2
    face_dirs = np.array(
        [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]],
        dtype=np.int64,
    )

    gc = grid_coords.astype(np.int64)
    offsets = gc.min(axis=0)
    gc_shifted = gc - offsets
    span = gc_shifted.max(axis=0) + 1
    pad_shape = tuple(int(x) + 2 for x in span)
    occ = np.zeros(pad_shape, dtype=bool)
    ix = gc_shifted[:, 0].astype(np.intp) + 1
    iy = gc_shifted[:, 1].astype(np.intp) + 1
    iz = gc_shifted[:, 2].astype(np.intp) + 1
    occ[ix, iy, iz] = True

    mat_grid_3d = np.full(pad_shape, -1, dtype=np.int32)
    mat_grid_3d[ix, iy, iz] = material_ids

    # Grid-to-world: world = origin + grid_shifted * voxel_size
    origin = positions[0] - gc_shifted[0].astype(np.float64) * voxel_size

    all_face_verts: list[np.ndarray] = []
    all_face_mats: list[int] = []

    for d in range(6):
        _mesh_direction(
            d,
            gc_shifted,
            ix,
            iy,
            iz,
            occ,
            mat_grid_3d,
            origin,
            voxel_size,
            hs,
            face_dirs,
            all_face_verts,
            all_face_mats,
        )

    if not all_face_verts:
        raise ValueError("No exterior faces found")

    return (
        np.concatenate(all_face_verts, axis=0).astype(np.float32),
        np.array(all_face_mats, dtype=np.int32),
    )


def round_triangle_scene(
    positions: np.ndarray,
    grid_coords: np.ndarray | None = None,
    voxel_size: float = 1.0,
    *,
    materials: Sequence[str] | None = None,
    material_colors: dict[str, Any] | None = None,
):
    """Convert exterior voxels to a DiffeRT TriangleScene for ray tracing.

    Only emits faces where a voxel borders empty space (exterior faces only).
    This gives a watertight hull with minimal triangles.

    Parameters
    ----------
    positions : (N, 3) voxel center positions in world coords [m]
    grid_coords : (N, 3) integer grid coords (for neighbor lookup). If None,
        positions are rounded to the nearest grid point.
    voxel_size : side length of each voxel [m]
    materials : per-voxel material names (optional)
    material_colors : mapping from material name to RGB color (optional)

    Returns
    -------
    DiffeRT TriangleScene ready for compute_paths().
    """
    _check_differt()

    import jax.numpy as jnp
    from differt.geometry import TriangleMesh
    from differt.scene import TriangleScene

    n = len(positions)
    if n == 0:
        raise ValueError("No voxels to convert")

    # Build occupancy set from grid coords
    if grid_coords is None:
        grid_coords = np.round(positions / voxel_size).astype(np.int64)
    else:
        grid_coords = grid_coords.astype(np.int64)

    # Convert material names to integer IDs
    if materials is not None and len(materials) > 0:
        unique_materials = sorted(set(materials))
        mat_name_to_id = {name: i for i, name in enumerate(unique_materials)}
        mat_ids = np.array([mat_name_to_id[m] for m in materials], dtype=np.int32)
    else:
        unique_materials = ["concrete"]
        mat_ids = np.zeros(n, dtype=np.int32)

    vertices, quad_mat_ids = _greedy_mesh_faces(grid_coords, positions, voxel_size, mat_ids)

    # Build triangle indices: every 4 vertices form a quad -> 2 triangles
    n_quads = len(vertices) // 4
    base = np.arange(n_quads, dtype=np.int32) * 4
    tri1 = np.column_stack([base, base + 1, base + 2])
    tri2 = np.column_stack([base, base + 2, base + 3])
    triangles = np.empty((n_quads * 2, 3), dtype=np.int32)
    triangles[0::2] = tri1
    triangles[1::2] = tri2

    # Per-triangle material index (2 triangles per quad, same material)
    face_materials = np.repeat(quad_mat_ids, 2)

    # Per-triangle colors from material_colors config
    _default_colors = {
        "concrete": [180, 180, 180],
        "asphalt": [80, 80, 80],
        "vegetation": [40, 160, 40],
        "brick": [200, 80, 50],
    }
    mc = material_colors if material_colors is not None else _default_colors
    color_array = np.zeros((len(triangles), 3), dtype=np.float32)
    for i, mat_name in enumerate(unique_materials):
        rgb = mc.get(mat_name, [200, 200, 200])
        mask = face_materials == i
        color_array[mask] = [c / 255.0 for c in rgb]

    print(f"  Voxel mesh: {n:,} voxels -> {len(vertices):,} vertices, {len(triangles):,} triangles")

    # Build DiffeRT TriangleScene
    mesh = TriangleMesh(
        vertices=jnp.array(vertices),
        triangles=jnp.array(triangles),
        face_colors=jnp.array(color_array),
        face_materials=jnp.array(face_materials),
        material_names=tuple(unique_materials),
        object_bounds=jnp.array([[0, len(triangles)]], dtype=jnp.int32),
    )

    scene = TriangleScene(
        transmitters=jnp.zeros((0, 3)),
        receivers=jnp.zeros((0, 3)),
        mesh=mesh,
    )

    return scene


def get_or_build_voxel_scene(
    positions: np.ndarray,
    grid_coords: np.ndarray | None = None,
    voxel_size: float = 1.0,
    cache_key: str = "default",
    materials: Sequence[str] | None = None,
    material_colors: dict[str, Any] | None = None,
):
    """Get cached voxel TriangleScene or build one."""
    with _voxel_scene_cache_lock:
        if cache_key in _voxel_scene_cache:
            return _voxel_scene_cache[cache_key]

    scene = round_triangle_scene(
        positions,
        grid_coords,
        voxel_size,
        materials=materials,
        material_colors=material_colors,
    )
    with _voxel_scene_cache_lock:
        _voxel_scene_cache[cache_key] = scene
    return scene


def scene_geometry_to_binary(scene_data: dict) -> tuple[bytes, dict]:
    """Serialize scene geometry for Three.js rendering.

    Returns (binary data, metadata).
    Binary: vertices (V*3 float32) + triangle indices (T*3 int32) + face_colors (T*3 float32).
    """
    vertices = scene_data["vertices"].astype(np.float32)
    triangles = scene_data["triangles"].astype(np.int32)

    data = vertices.tobytes() + triangles.tobytes()

    meta = {
        "n_vertices": scene_data["n_vertices"],
        "n_triangles": scene_data["n_triangles"],
        "material_names": scene_data["material_names"],
    }

    if scene_data["face_colors"] is not None:
        face_colors = scene_data["face_colors"].astype(np.float32)
        data += face_colors.tobytes()
        meta["has_face_colors"] = True
    else:
        meta["has_face_colors"] = False

    return data, meta
