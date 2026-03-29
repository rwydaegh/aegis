"""Facade decomposition: per-level wall geometry with window and door openings.

Decomposes each wall edge into a grid of wall quads with recessed glass panes
for windows and wood panels for doors.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aegis.environment import MaterialType
from aegis.environment.roofs import _ROOF_DISPATCH
from aegis.environment.styles import BuildingStyle, resolve_style

# Recess depth for glass panes (meters)
_GLASS_RECESS = 0.05


@dataclass
class FacadeGeometry:
    """Collected geometry from decomposing one facade segment."""

    wall_verts: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    wall_tris: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.uint32))
    wall_mats: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    window_verts: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    window_tris: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.uint32))
    window_mats: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    door_verts: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    door_tris: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.uint32))
    door_mats: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))


def _make_quad(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, base_idx: int):
    """Create two triangles for a quad (p0, p1, p2, p3) with CCW winding.

    Returns (verts (4,3), tris (2,3)).
    """
    verts = np.array([p0, p1, p2, p3], dtype=np.float64)
    tris = np.array(
        [[base_idx, base_idx + 1, base_idx + 2], [base_idx, base_idx + 2, base_idx + 3]],
        dtype=np.uint32,
    )
    return verts, tris


def _add_opening(
    wall_verts_list: list,
    wall_tris_list: list,
    glass_verts_list: list,
    glass_tris_list: list,
    wall_vert_offset: int,
    glass_vert_offset: int,
    left_3d: np.ndarray,
    right_3d: np.ndarray,
    normal_3d: np.ndarray,
    z_bottom: float,
    z_top: float,
    opening_left: float,
    opening_right: float,
    opening_bottom: float,
    opening_top: float,
) -> tuple[int, int]:
    """Add wall quads framing an opening plus a recessed glass/door pane.

    Returns (wall_verts_emitted, glass_verts_emitted) so the caller can
    update offsets correctly.
    """
    # opening_left/right are fractions along the left_3d -> right_3d direction
    # opening_bottom/top are absolute z values
    facade_dir = right_3d - left_3d
    p_left = left_3d + opening_left * facade_dir
    p_right = left_3d + opening_right * facade_dir

    wall_verts_emitted = 0
    glass_verts_emitted = 0

    # --- Left margin strip (full height) ---
    bl = left_3d + np.array([0, 0, z_bottom])
    br = p_left + np.array([0, 0, z_bottom])
    tr = p_left + np.array([0, 0, z_top])
    tl = left_3d + np.array([0, 0, z_top])
    v, t = _make_quad(bl, br, tr, tl, wall_vert_offset + wall_verts_emitted)
    wall_verts_list.append(v)
    wall_tris_list.append(t)
    wall_verts_emitted += 4

    # --- Right margin strip (full height) ---
    bl = p_right + np.array([0, 0, z_bottom])
    br = right_3d + np.array([0, 0, z_bottom])
    tr = right_3d + np.array([0, 0, z_top])
    tl = p_right + np.array([0, 0, z_top])
    v, t = _make_quad(bl, br, tr, tl, wall_vert_offset + wall_verts_emitted)
    wall_verts_list.append(v)
    wall_tris_list.append(t)
    wall_verts_emitted += 4

    # --- Bottom strip (below opening) ---
    if opening_bottom > z_bottom + 1e-6:
        bl = p_left + np.array([0, 0, z_bottom])
        br = p_right + np.array([0, 0, z_bottom])
        tr = p_right + np.array([0, 0, opening_bottom])
        tl = p_left + np.array([0, 0, opening_bottom])
        v, t = _make_quad(bl, br, tr, tl, wall_vert_offset + wall_verts_emitted)
        wall_verts_list.append(v)
        wall_tris_list.append(t)
        wall_verts_emitted += 4

    # --- Top strip (above opening) ---
    if opening_top < z_top - 1e-6:
        bl = p_left + np.array([0, 0, opening_top])
        br = p_right + np.array([0, 0, opening_top])
        tr = p_right + np.array([0, 0, z_top])
        tl = p_left + np.array([0, 0, z_top])
        v, t = _make_quad(bl, br, tr, tl, wall_vert_offset + wall_verts_emitted)
        wall_verts_list.append(v)
        wall_tris_list.append(t)
        wall_verts_emitted += 4

    # --- Recessed glass/door pane ---
    recess = normal_3d * _GLASS_RECESS
    bl = p_left + np.array([0, 0, opening_bottom]) - recess
    br = p_right + np.array([0, 0, opening_bottom]) - recess
    tr = p_right + np.array([0, 0, opening_top]) - recess
    tl = p_left + np.array([0, 0, opening_top]) - recess
    v, t = _make_quad(bl, br, tr, tl, glass_vert_offset + glass_verts_emitted)
    glass_verts_list.append(v)
    glass_tris_list.append(t)
    glass_verts_emitted += 4

    return wall_verts_emitted, glass_verts_emitted


def decompose_facade(
    start: np.ndarray,
    end: np.ndarray,
    z_bottom: float,
    z_top: float,
    style: BuildingStyle,
    is_ground: bool = False,
    seed: int = 0,
) -> FacadeGeometry:
    """Decompose a single wall edge into wall quads with window/door openings.

    Args:
        start: 2D point (x, y) of the wall edge start.
        end: 2D point (x, y) of the wall edge end.
        z_bottom: Z coordinate of the bottom of this level.
        z_top: Z coordinate of the top of this level.
        style: Building style with window/door parameters.
        is_ground: Whether this is the ground floor (adds a door).
        seed: Random seed for deterministic variation.

    Returns:
        FacadeGeometry with wall, window, and door geometry.
    """
    start = np.asarray(start, dtype=np.float64)
    end = np.asarray(end, dtype=np.float64)
    edge_vec = end - start
    facade_width = float(np.linalg.norm(edge_vec))

    if facade_width < 1e-6:
        return FacadeGeometry()

    # Unit vectors
    edge_dir = edge_vec / facade_width
    # Outward normal (rotate edge_dir 90 degrees CCW in 2D, then make 3D)
    normal_2d = np.array([-edge_dir[1], edge_dir[0]])
    normal_3d = np.array([normal_2d[0], normal_2d[1], 0.0])

    # 3D basis: left_3d is the start point projected onto XY plane (z=0)
    # We build geometry relative to start, adding z offsets via arrays
    left_3d = np.array([start[0], start[1], 0.0])
    right_3d = np.array([end[0], end[1], 0.0])

    wp = style.window
    n_windows = wp.count_for_width(facade_width)

    # If no windows fit, emit a single plain wall quad
    if n_windows == 0:
        bl = np.array([start[0], start[1], z_bottom])
        br = np.array([end[0], end[1], z_bottom])
        tr = np.array([end[0], end[1], z_top])
        tl = np.array([start[0], start[1], z_top])
        verts = np.array([bl, br, tr, tl], dtype=np.float64)
        tris = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.uint32)
        mats = np.array([int(MaterialType.CONCRETE), int(MaterialType.CONCRETE)], dtype=np.int32)
        return FacadeGeometry(wall_verts=verts, wall_tris=tris, wall_mats=mats)

    # Center the window pattern on the facade
    pattern_width = n_windows * wp.total_width
    padding = (facade_width - pattern_width) / 2.0

    # Determine which slot becomes a door (if ground floor)
    rng = np.random.RandomState(seed)
    door_slot = -1
    if is_ground and style.has_ground_floor_doors and n_windows > 0:
        door_slot = rng.randint(0, n_windows)

    # Collect geometry
    wall_verts_list: list[np.ndarray] = []
    wall_tris_list: list[np.ndarray] = []
    window_verts_list: list[np.ndarray] = []
    window_tris_list: list[np.ndarray] = []
    door_verts_list: list[np.ndarray] = []
    door_tris_list: list[np.ndarray] = []

    wall_vo = 0  # wall vertex offset
    win_vo = 0  # window vertex offset
    door_vo = 0  # door vertex offset

    # Left padding strip (full height)
    if padding > 1e-6:
        p_left = left_3d
        p_right_pad = left_3d + (padding / facade_width) * (right_3d - left_3d)
        bl = p_left + np.array([0, 0, z_bottom])
        br = p_right_pad + np.array([0, 0, z_bottom])
        tr = p_right_pad + np.array([0, 0, z_top])
        tl = p_left + np.array([0, 0, z_top])
        v, t = _make_quad(bl, br, tr, tl, wall_vo)
        wall_verts_list.append(v)
        wall_tris_list.append(t)
        wall_vo += 4

    # Each window slot
    for i in range(n_windows):
        slot_start = padding + i * wp.total_width
        slot_end = slot_start + wp.total_width

        is_door = i == door_slot
        if is_door:
            dp = style.door
            # Door: starts at z_bottom, use door dimensions
            opening_bottom = z_bottom
            opening_top = z_bottom + dp.height
            # Clamp top to z_top
            if opening_top > z_top:
                opening_top = z_top

            door_center = slot_start + wp.total_width / 2.0

            slot_left_3d = left_3d + (slot_start / facade_width) * (right_3d - left_3d)
            slot_right_3d = left_3d + (slot_end / facade_width) * (right_3d - left_3d)

            w_emitted, g_emitted = _add_opening(
                wall_verts_list,
                wall_tris_list,
                door_verts_list,
                door_tris_list,
                wall_vo,
                door_vo,
                slot_left_3d,
                slot_right_3d,
                normal_3d,
                z_bottom,
                z_top,
                (door_center - dp.width / 2.0 - slot_start) / wp.total_width,
                (door_center + dp.width / 2.0 - slot_start) / wp.total_width,
                opening_bottom,
                opening_top,
            )
            wall_vo += w_emitted
            door_vo += g_emitted
        else:
            # Window opening
            opening_bottom = z_bottom + wp.sill_height
            opening_top = opening_bottom + wp.height
            # Clamp
            if opening_top > z_top:
                opening_top = z_top
            if opening_bottom >= opening_top:
                # Window doesn't fit vertically, emit plain wall
                slot_left_3d = left_3d + (slot_start / facade_width) * (right_3d - left_3d)
                slot_right_3d = left_3d + (slot_end / facade_width) * (right_3d - left_3d)
                bl = slot_left_3d + np.array([0, 0, z_bottom])
                br = slot_right_3d + np.array([0, 0, z_bottom])
                tr = slot_right_3d + np.array([0, 0, z_top])
                tl = slot_left_3d + np.array([0, 0, z_top])
                v, t = _make_quad(bl, br, tr, tl, wall_vo)
                wall_verts_list.append(v)
                wall_tris_list.append(t)
                wall_vo += 4
                continue

            slot_left_3d = left_3d + (slot_start / facade_width) * (right_3d - left_3d)
            slot_right_3d = left_3d + (slot_end / facade_width) * (right_3d - left_3d)

            w_emitted, g_emitted = _add_opening(
                wall_verts_list,
                wall_tris_list,
                window_verts_list,
                window_tris_list,
                wall_vo,
                win_vo,
                slot_left_3d,
                slot_right_3d,
                normal_3d,
                z_bottom,
                z_top,
                wp.margin_left / wp.total_width,
                (wp.margin_left + wp.width) / wp.total_width,
                opening_bottom,
                opening_top,
            )
            wall_vo += w_emitted
            win_vo += g_emitted

    # Right padding strip (full height)
    if padding > 1e-6:
        p_left_pad = left_3d + ((facade_width - padding) / facade_width) * (right_3d - left_3d)
        p_right = right_3d
        bl = p_left_pad + np.array([0, 0, z_bottom])
        br = p_right + np.array([0, 0, z_bottom])
        tr = p_right + np.array([0, 0, z_top])
        tl = p_left_pad + np.array([0, 0, z_top])
        v, t = _make_quad(bl, br, tr, tl, wall_vo)
        wall_verts_list.append(v)
        wall_tris_list.append(t)
        wall_vo += 4

    # Assemble arrays
    def _concat_or_empty(vlist, tlist, mat_type):
        if vlist:
            verts = np.concatenate(vlist)
            tris = np.concatenate(tlist)
            mats = np.full(len(tris), int(mat_type), dtype=np.int32)
            return verts, tris, mats
        return (
            np.empty((0, 3), dtype=np.float64),
            np.empty((0, 3), dtype=np.uint32),
            np.empty(0, dtype=np.int32),
        )

    wv, wt, wm = _concat_or_empty(wall_verts_list, wall_tris_list, MaterialType.CONCRETE)
    gv, gt, gm = _concat_or_empty(window_verts_list, window_tris_list, MaterialType.GLASS)
    dv, dt, dm = _concat_or_empty(door_verts_list, door_tris_list, MaterialType.WOOD)

    return FacadeGeometry(
        wall_verts=wv,
        wall_tris=wt,
        wall_mats=wm,
        window_verts=gv,
        window_tris=gt,
        window_mats=gm,
        door_verts=dv,
        door_tris=dt,
        door_mats=dm,
    )


def generate_detailed_building(
    footprint: np.ndarray,
    height: float,
    roof_shape: str = "flat",
    roof_height: float = 2.0,
    material: MaterialType = MaterialType.CONCRETE,
    roof_material: MaterialType = MaterialType.CONCRETE,
    tags: dict[str, str] | None = None,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate detailed building geometry with per-level facades, windows, and doors.

    Same interface as ``generate_building`` plus optional ``tags`` and ``seed`` params.

    Returns: (vertices (V,3), triangles (T,3), materials (T,))
    """
    footprint = np.asarray(footprint, dtype=np.float64)

    style = resolve_style(tags) if tags is not None else BuildingStyle()

    num_levels = style.compute_num_levels(height)

    # Compute level heights
    level_bottoms = []
    level_tops = []
    z = 0.0
    for lvl in range(num_levels):
        lvl_h = style.ground_level_height if lvl == 0 else style.level_height
        top = min(z + lvl_h, height)
        level_bottoms.append(z)
        level_tops.append(top)
        z = top
        if z >= height - 1e-6:
            break

    # Collect all facade geometry
    all_wall_verts = []
    all_wall_tris = []
    all_wall_mats = []
    all_win_verts = []
    all_win_tris = []
    all_win_mats = []
    all_door_verts = []
    all_door_tris = []
    all_door_mats = []

    wall_offset = 0
    win_offset = 0
    door_offset = 0

    n = len(footprint)
    edge_seed = seed

    for lvl_idx, (zb, zt) in enumerate(zip(level_bottoms, level_tops, strict=True)):
        is_ground = lvl_idx == 0
        for edge_i in range(n):
            edge_j = (edge_i + 1) % n
            start = footprint[edge_i]
            end = footprint[edge_j]
            edge_seed += 1

            geo = decompose_facade(start, end, zb, zt, style, is_ground=is_ground, seed=edge_seed)

            if geo.wall_verts.shape[0] > 0:
                all_wall_verts.append(geo.wall_verts)
                all_wall_tris.append(geo.wall_tris + wall_offset)
                all_wall_mats.append(geo.wall_mats)
                wall_offset += len(geo.wall_verts)

            if geo.window_verts.shape[0] > 0:
                all_win_verts.append(geo.window_verts)
                all_win_tris.append(geo.window_tris + win_offset)
                all_win_mats.append(geo.window_mats)
                win_offset += len(geo.window_verts)

            if geo.door_verts.shape[0] > 0:
                all_door_verts.append(geo.door_verts)
                all_door_tris.append(geo.door_tris + door_offset)
                all_door_mats.append(geo.door_mats)
                door_offset += len(geo.door_verts)

    # Roof
    roof_fn = _ROOF_DISPATCH.get(roof_shape)
    if roof_fn is None:
        raise ValueError(f"Unknown roof shape: {roof_shape!r}")
    roof_verts, roof_tris = roof_fn(footprint, height, roof_height)
    roof_mats = np.full(len(roof_tris), int(roof_material), dtype=np.int32)

    # Combine everything: walls, windows, doors, roof
    parts_verts = []
    parts_tris = []
    parts_mats = []
    combined_offset = 0

    # Walls
    if all_wall_verts:
        wv = np.concatenate(all_wall_verts)
        wt = np.concatenate(all_wall_tris) + combined_offset
        wm = np.concatenate(all_wall_mats)
        parts_verts.append(wv)
        parts_tris.append(wt)
        parts_mats.append(wm)
        combined_offset += len(wv)

    # Windows
    if all_win_verts:
        gv = np.concatenate(all_win_verts)
        gt = np.concatenate(all_win_tris) + combined_offset
        gm = np.concatenate(all_win_mats)
        parts_verts.append(gv)
        parts_tris.append(gt)
        parts_mats.append(gm)
        combined_offset += len(gv)

    # Doors
    if all_door_verts:
        dv = np.concatenate(all_door_verts)
        dt = np.concatenate(all_door_tris) + combined_offset
        dm = np.concatenate(all_door_mats)
        parts_verts.append(dv)
        parts_tris.append(dt)
        parts_mats.append(dm)
        combined_offset += len(dv)

    # Roof
    parts_verts.append(roof_verts)
    parts_tris.append(roof_tris + combined_offset)
    parts_mats.append(roof_mats)

    all_verts = np.concatenate(parts_verts)
    all_tris = np.concatenate(parts_tris)
    all_mats = np.concatenate(parts_mats)

    return all_verts, all_tris, all_mats
