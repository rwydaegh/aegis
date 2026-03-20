"""DiffeRT ray tracing integration for the interactive viewer.

Loads Sionna XML scenes, computes propagation paths from antenna to body,
and converts them to AEGIS PropagationPaths.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from aegis.paths import PropagationPaths

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


def clear_voxel_scene_cache() -> None:
    """Invalidate cached DiffeRT scenes built from voxels (call after reloading voxel data)."""
    _voxel_scene_cache.clear()


def list_available_scenes(scenes_dir: str | Path | None = None) -> list[dict]:
    """List available Sionna XML scenes.

    Returns list of dicts with keys: name, path, n_vertices, n_triangles.
    """
    if scenes_dir is None:
        # Use SIONNA_SCENES_DIR env var or return empty
        env_dir = os.environ.get("SIONNA_SCENES_DIR")
        if env_dir:
            scenes_dir = Path(env_dir)
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


def compute_paths_differt(
    scene_path: str | Path,
    tx_pos: np.ndarray,
    rx_pos: np.ndarray,
    max_order: int = 1,
    freq_hz: float = 28e9,
    tx_power_dbm: float = 30.0,
    # NOTE: Uses from_powers() with scalar power only. Polarisation direction
    # is irrelevant here because the viewer runs incoherent levels (0-6) where
    # only |psi|^2 matters. For coherent levels (7-8) with proper TE/TM
    # tracking, use aegis.integration.differt.paths_from_differt_scene().
) -> tuple[PropagationPaths, list[dict]]:
    """Run DiffeRT ray tracing and return AEGIS PropagationPaths.

    Parameters
    ----------
    scene_path : path to Sionna XML scene
    tx_pos : (3,) transmitter position [m]
    rx_pos : (3,) receiver (body center) position [m]
    max_order : max number of reflections (0=LOS only, 1=+single reflection, etc.)
    freq_hz : frequency [Hz]
    tx_power_dbm : transmit power [dBm]

    Returns
    -------
    (paths, path_viz_data) where path_viz_data is a list of dicts
    with 'vertices' key for Three.js line rendering.
    """
    _check_differt()

    import equinox as eqx
    import jax.numpy as jnp

    scene_data = load_scene(scene_path)
    scene = scene_data["scene"]

    tx = jnp.array([tx_pos.tolist()])
    rx = jnp.array([rx_pos.tolist()])

    scene = eqx.tree_at(lambda s: s.transmitters, scene, tx)
    scene = eqx.tree_at(lambda s: s.receivers, scene, rx)

    # Collect paths from all orders
    all_k_hat = []
    all_power = []
    path_viz = []

    tx_power_w = 10 ** ((tx_power_dbm - 30) / 10)

    for order in range(max_order + 1):
        try:
            paths = scene.compute_paths(order=order)
        except Exception:
            continue

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
            reflection_loss = 0.5**order
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


def _emit_exposed_faces(
    grid_coords: np.ndarray,
    positions: np.ndarray,
    voxel_size: float,
) -> np.ndarray:
    """Emit quad vertices for all exposed voxel faces.

    Returns (M, 3) float32 array of vertices, where every consecutive 4
    vertices form one quad (to be triangulated as [0,1,2] + [0,2,3]).
    """
    hs = voxel_size / 2
    face_dirs = np.array(
        [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]],
        dtype=np.int64,
    )
    face_corners = np.array(
        [
            [[hs, -hs, -hs], [hs, hs, -hs], [hs, hs, hs], [hs, -hs, hs]],  # +X
            [[-hs, -hs, hs], [-hs, hs, hs], [-hs, hs, -hs], [-hs, -hs, -hs]],  # -X
            [[-hs, hs, -hs], [-hs, hs, hs], [hs, hs, hs], [hs, hs, -hs]],  # +Y
            [[hs, -hs, -hs], [hs, -hs, hs], [-hs, -hs, hs], [-hs, -hs, -hs]],  # -Y
            [[-hs, -hs, hs], [hs, -hs, hs], [hs, hs, hs], [-hs, hs, hs]],  # +Z
            [[-hs, hs, -hs], [hs, hs, -hs], [hs, -hs, -hs], [-hs, -hs, -hs]],  # -Z
        ],
        dtype=np.float32,
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

    all_face_verts: list[np.ndarray] = []
    for d in range(6):
        dx, dy, dz = int(face_dirs[d, 0]), int(face_dirs[d, 1]), int(face_dirs[d, 2])
        ni = ix + dx
        nj = iy + dy
        nk = iz + dz
        exposed_mask = ~occ[ni, nj, nk]
        exposed_idx = np.where(exposed_mask)[0]
        if len(exposed_idx) == 0:
            continue

        centers = positions[exposed_idx]
        corners = face_corners[d]
        verts = centers[:, np.newaxis, :] + corners[np.newaxis, :, :]
        all_face_verts.append(verts.reshape(-1, 3))

    if not all_face_verts:
        raise ValueError("No exterior faces found")

    return np.concatenate(all_face_verts, axis=0).astype(np.float32)


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


def _greedy_mesh_faces(
    grid_coords: np.ndarray,
    positions: np.ndarray,
    voxel_size: float,
) -> np.ndarray:
    """Emit greedy-merged quad vertices for all exposed voxel faces.

    Returns (M, 3) float32 array of vertices, where every consecutive 4
    vertices form one quad (to be triangulated as [0,1,2] + [0,2,3]).
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

    # Grid-to-world: world = origin + grid_shifted * voxel_size
    origin = positions[0] - gc_shifted[0].astype(np.float64) * voxel_size

    all_face_verts: list[np.ndarray] = []

    for d in range(6):
        dx, dy, dz = int(face_dirs[d, 0]), int(face_dirs[d, 1]), int(face_dirs[d, 2])
        ni = ix + dx
        nj = iy + dy
        nk = iz + dz
        exposed_mask = ~occ[ni, nj, nk]
        exposed_idx = np.where(exposed_mask)[0]
        if len(exposed_idx) == 0:
            continue

        u_ax, v_ax, f_ax, f_sign = _FACE_UV_MAP[d]
        winding = _FACE_WINDING[d]

        exposed_gc = gc_shifted[exposed_idx]
        fixed_vals = exposed_gc[:, f_ax]
        unique_fixed = np.unique(fixed_vals)

        for fv in unique_fixed:
            slice_mask = fixed_vals == fv
            slice_gc = exposed_gc[slice_mask]

            u_coords = slice_gc[:, u_ax].astype(np.intp)
            v_coords = slice_gc[:, v_ax].astype(np.intp)
            u_min, u_max = int(u_coords.min()), int(u_coords.max())
            v_min, v_max = int(v_coords.min()), int(v_coords.max())
            u_span = u_max - u_min + 1
            v_span = v_max - v_min + 1

            grid_2d = np.zeros((u_span, v_span), dtype=bool)
            grid_2d[u_coords - u_min, v_coords - v_min] = True
            visited = np.zeros_like(grid_2d)

            for u in range(u_span):
                for v in range(v_span):
                    if not grid_2d[u, v] or visited[u, v]:
                        continue

                    w = 1
                    while u + w < u_span and grid_2d[u + w, v] and not visited[u + w, v]:
                        w += 1

                    h = 1
                    while v + h < v_span:
                        row_ok = True
                        for du in range(w):
                            if not grid_2d[u + du, v + h] or visited[u + du, v + h]:
                                row_ok = False
                                break
                        if not row_ok:
                            break
                        h += 1

                    visited[u : u + w, v : v + h] = True

                    gu0 = u + u_min
                    gv0 = v + v_min
                    gf = int(fv)

                    u_lo = origin[u_ax] + gu0 * voxel_size - hs
                    u_hi = origin[u_ax] + (gu0 + w) * voxel_size - hs
                    v_lo = origin[v_ax] + gv0 * voxel_size - hs
                    v_hi = origin[v_ax] + (gv0 + h) * voxel_size - hs
                    f_val = origin[f_ax] + gf * voxel_size + f_sign * hs

                    u_vals = [u_lo, u_hi]
                    v_vals = [v_lo, v_hi]
                    quad = np.zeros((4, 3), dtype=np.float32)
                    for ci, (ui, vi) in enumerate(winding):
                        quad[ci, u_ax] = u_vals[ui]
                        quad[ci, v_ax] = v_vals[vi]
                        quad[ci, f_ax] = f_val

                    all_face_verts.append(quad)

    if not all_face_verts:
        raise ValueError("No exterior faces found")

    return np.concatenate(all_face_verts, axis=0).astype(np.float32)


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

    vertices = _greedy_mesh_faces(grid_coords, positions, voxel_size)

    # Build triangle indices: every 4 vertices form a quad -> 2 triangles
    n_quads = len(vertices) // 4
    base = np.arange(n_quads, dtype=np.int32) * 4
    tri1 = np.column_stack([base, base + 1, base + 2])
    tri2 = np.column_stack([base, base + 2, base + 3])
    triangles = np.empty((n_quads * 2, 3), dtype=np.int32)
    triangles[0::2] = tri1
    triangles[1::2] = tri2

    print(f"  Voxel mesh: {n:,} voxels -> {len(vertices):,} vertices, {len(triangles):,} triangles")

    # Build DiffeRT TriangleScene
    mesh = TriangleMesh(
        vertices=jnp.array(vertices),
        triangles=jnp.array(triangles),
        face_colors=jnp.zeros((len(triangles), 3)),
        face_materials=jnp.zeros(len(triangles), dtype=jnp.int32),
        material_names=("concrete",),
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
    if cache_key in _voxel_scene_cache:
        return _voxel_scene_cache[cache_key]

    scene = round_triangle_scene(
        positions,
        grid_coords,
        voxel_size,
        materials=materials,
        material_colors=material_colors,
    )
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
