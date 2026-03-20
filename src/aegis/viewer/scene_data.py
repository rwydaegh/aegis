"""Data loading and binary serialization for the viewer."""

from __future__ import annotations

import colorsys
import json
from pathlib import Path

import numpy as np

from aegis.geometry.mesh import BodyMesh
from aegis.viewer.config import DEFAULTS

_config: dict = DEFAULTS


def set_config(config: dict) -> None:
    """Set the active config for scene_data operations."""
    global _config
    _config = config


# ---------------------------------------------------------------------------
# Material classification (from spike_viewer.py)
# ---------------------------------------------------------------------------


def _build_material_rules(mc: dict) -> list[dict]:
    """Build an ordered list of material classification rules from the config.

    Each rule has a "test" callable (hue, s, v) -> bool and a "name" string.
    The first matching rule wins.
    """
    vhr1 = mc["vegetation_hue_range_1"]
    vhr2 = mc["vegetation_hue_range_2"]
    bhr = mc["blue_hue_range"]
    bshr = mc["brick_secondary_hue_range"]

    return [
        # Low-saturation early exit: gray/dark colors
        {
            "test": lambda hue, s, v, _mc=mc: (
                s < _mc["saturation_gray_threshold"] and v < _mc["value_asphalt_threshold"]
            ),
            "name": "asphalt",
        },
        {
            "test": lambda hue, s, v, _mc=mc: s < _mc["saturation_gray_threshold"],
            "name": "concrete",
        },
        # Dark value: asphalt regardless of hue
        {
            "test": lambda hue, s, v, _mc=mc: v < _mc["value_dark_threshold"],
            "name": "asphalt",
        },
        # Vegetation hue range 1
        {
            "test": lambda hue, s, v, _vhr1=vhr1, _mc=mc: (
                _vhr1[0] < hue < _vhr1[1] and s > _mc["vegetation_sat_min_1"] and v > _mc["vegetation_val_min_1"]
            ),
            "name": "vegetation",
        },
        # Vegetation hue range 2
        {
            "test": lambda hue, s, v, _vhr2=vhr2, _mc=mc: (
                _vhr2[0] < hue < _vhr2[1] and s > _mc["vegetation_sat_min_2"] and v > _mc["vegetation_val_min_2"]
            ),
            "name": "vegetation",
        },
        # Brick: outside the central hue band with enough saturation
        {
            "test": lambda hue, s, v, _mc=mc: (
                (hue < _mc["brick_hue_low"] or hue > _mc["brick_hue_high"]) and s > _mc["brick_sat_min"]
            ),
            "name": "brick",
        },
        # Blue hue range: water, glass, or concrete sub-branches
        {
            "test": lambda hue, s, v, _bhr=bhr, _mc=mc: (
                _bhr[0] < hue < _bhr[1] and s > _mc["water_sat_min"] and v > _mc["water_val_min"]
            ),
            "name": "water",
        },
        {
            "test": lambda hue, s, v, _bhr=bhr, _mc=mc: (
                _bhr[0] < hue < _bhr[1] and s > _mc["glass_sat_min"] and v > _mc["glass_val_min"]
            ),
            "name": "glass",
        },
        {
            "test": lambda hue, s, v, _bhr=bhr: _bhr[0] < hue < _bhr[1],
            "name": "concrete",
        },
        # Low saturation outside blue range: asphalt or concrete by value
        {
            "test": lambda hue, s, v, _mc=mc: s < _mc["brick_sat_min"] and v < _mc["value_asphalt_threshold"],
            "name": "asphalt",
        },
        {
            "test": lambda hue, s, v, _mc=mc: s < _mc["brick_sat_min"],
            "name": "concrete",
        },
        # Brick secondary hue range
        {
            "test": lambda hue, s, v, _bshr=bshr, _mc=mc: (
                _bshr[0] < hue < _bshr[1] and s < _mc["brick_secondary_sat_max"]
            ),
            "name": "brick",
        },
    ]


def classify_material(r: int, g: int, b: int) -> str:
    mc = _config["material_classification"]
    rf, gf, bf = r / 255, g / 255, b / 255
    h, s, v = colorsys.rgb_to_hsv(rf, gf, bf)
    hue = h * 360

    for rule in _build_material_rules(mc):
        if rule["test"](hue, s, v):
            return rule["name"]
    return "concrete"


# ---------------------------------------------------------------------------
# ECEF to ENU (from spike_viewer.py)
# ---------------------------------------------------------------------------


def ecef_to_enu_matrix(lon_deg: float, lat_deg: float) -> np.ndarray:
    lon = np.radians(lon_deg)
    lat = np.radians(lat_deg)
    sl, cl = np.sin(lon), np.cos(lon)
    sp, cp = np.sin(lat), np.cos(lat)
    return np.array(
        [
            [-sl, cl, 0],
            [-sp * cl, -sp * sl, cp],
            [cp * cl, cp * sl, sp],
        ]
    )


# ---------------------------------------------------------------------------
# Exterior voxel extraction
# ---------------------------------------------------------------------------

_NEIGHBORS_6 = np.array(
    [
        [1, 0, 0],
        [-1, 0, 0],
        [0, 1, 0],
        [0, -1, 0],
        [0, 0, 1],
        [0, 0, -1],
    ],
    dtype=np.int64,
)


def extract_exterior(grid_coords: np.ndarray) -> np.ndarray:
    """Return boolean mask of exterior voxels (those touching at least one empty neighbor).

    Uses sorted-array binary search for fast vectorized neighbor lookup.
    """
    coords = grid_coords.astype(np.int64)
    n = len(coords)

    # Pack (x, y, z) into a single int64 for fast lookup
    packed = coords[:, 0] + coords[:, 1] * 10_000 + coords[:, 2] * 100_000_000
    sorted_packed = np.sort(packed)

    # A voxel is interior if ALL 6 neighbors exist
    interior = np.ones(n, dtype=bool)
    for dx, dy, dz in _NEIGHBORS_6:
        neighbor = packed + dx + dy * 10_000 + dz * 100_000_000
        idx = np.searchsorted(sorted_packed, neighbor)
        has_neighbor = (idx < len(sorted_packed)) & (sorted_packed[np.minimum(idx, len(sorted_packed) - 1)] == neighbor)
        interior &= has_neighbor

    return ~interior


# ---------------------------------------------------------------------------
# Voxel loading helpers
# ---------------------------------------------------------------------------


def _parse_voxel_json(
    path: str | Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Parse a single voxel JSON file into arrays.

    Returns (grid_coords (N,3 int64), positions (N,3 float64),
             colors (N,3 uint8), materials list[str]).
    """
    with open(str(path)) as f:
        data = json.load(f)

    voxels = data if isinstance(data, list) else data.get("voxels", [])

    n = len(voxels)
    grid_coords = np.zeros((n, 3), dtype=np.int64)
    positions = np.zeros((n, 3))
    colors = np.zeros((n, 3), dtype=np.uint8)
    materials = []

    for i, v in enumerate(voxels):
        grid_coords[i] = [v.get("x", 0), v.get("y", 0), v.get("z", 0)]
        if "wx" in v:
            positions[i] = [v["wx"], v["wy"], v["wz"]]
        else:
            positions[i] = grid_coords[i].astype(float)
        r, g, b = int(v.get("r", 128)), int(v.get("g", 128)), int(v.get("b", 128))
        colors[i] = [r, g, b]
        materials.append(classify_material(r, g, b))

    return grid_coords, positions, colors, materials


def _deduplicate(
    grid_coords: np.ndarray,
    positions: np.ndarray,
    colors: np.ndarray,
    materials: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Remove duplicate grid coordinates (from overlapping tiles)."""
    n = len(grid_coords)
    if n == 0:
        return grid_coords, positions, colors, materials
    _, unique_idx = np.unique(grid_coords, axis=0, return_index=True)
    unique_idx.sort()
    if len(unique_idx) < n:
        n_dups = n - len(unique_idx)
        print(f"  Dedup: {n:,} -> {len(unique_idx):,} ({n_dups:,} duplicates removed, {n_dups / n * 100:.1f}%)")
        grid_coords = grid_coords[unique_idx]
        positions = positions[unique_idx]
        colors = colors[unique_idx]
        materials = [materials[i] for i in unique_idx]
    return grid_coords, positions, colors, materials


def _crop_to_bbox(
    grid_coords: np.ndarray,
    positions: np.ndarray,
    colors: np.ndarray,
    materials: list[str],
    center: np.ndarray,
    bbox_radius: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Crop to a horizontal square bbox around center. Keeps all heights.

    Positions are in Y-up format [x, y_up, z_horiz], so horizontal = axes 0 and 2.
    For ECEF data the horizontal axes are still 0 and 2 before ENU transform.
    """
    n = len(positions)
    if n == 0:
        return grid_coords, positions, colors, materials

    mask = (np.abs(positions[:, 0] - center[0]) <= bbox_radius) & (np.abs(positions[:, 2] - center[2]) <= bbox_radius)
    n_kept = int(mask.sum())
    print(f"  Bbox crop ({bbox_radius * 2:.0f}m): {n:,} -> {n_kept:,} voxels")

    grid_coords = grid_coords[mask]
    positions = positions[mask]
    colors = colors[mask]
    materials = [m for m, k in zip(materials, mask, strict=True) if k]
    return grid_coords, positions, colors, materials


def _apply_filters(
    grid_coords: np.ndarray,
    positions: np.ndarray,
    colors: np.ndarray,
    materials: list[str],
    exterior_only: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Deduplicate and optionally remove interior voxels."""
    n = len(positions)
    if n == 0:
        return grid_coords, positions, colors, materials

    grid_coords, positions, colors, materials = _deduplicate(
        grid_coords,
        positions,
        colors,
        materials,
    )

    if exterior_only:
        ext_mask = extract_exterior(grid_coords)
        n_after = int(ext_mask.sum())
        n_interior = len(grid_coords) - n_after
        if n_interior > 0:
            print(f"  Exterior filter: {len(grid_coords):,} -> {n_after:,} ({n_interior:,} interior removed)")
            grid_coords = grid_coords[ext_mask]
            positions = positions[ext_mask]
            colors = colors[ext_mask]
            materials = [m for m, keep in zip(materials, ext_mask, strict=True) if keep]

    return grid_coords, positions, colors, materials


def _ecef_to_local(positions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Transform ECEF positions to ENU local coordinates.

    Computes the reference lon/lat from the centroid of the provided positions.
    Returns (transformed_positions, transform_4x4).
    """
    center_ecef = positions.mean(axis=0)
    positions = positions - center_ecef
    lon_rad = np.arctan2(center_ecef[1], center_ecef[0])
    lat_rad = np.arctan2(
        center_ecef[2],
        np.sqrt(center_ecef[0] ** 2 + center_ecef[1] ** 2),
    )
    R = ecef_to_enu_matrix(np.degrees(lon_rad), np.degrees(lat_rad))
    positions = positions @ R.T
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = -R @ center_ecef
    return positions, M


def _yup_to_zup(positions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert Y-up positions to Z-up by remapping axes.

    Y-up [x, y_up, z_horiz] -> Z-up [x, -z_horiz, y_up].
    Returns (transformed_positions, transform_4x4).
    """
    center = positions.mean(axis=0)
    positions = positions - center
    positions = np.column_stack(
        [
            positions[:, 0],
            -positions[:, 2],
            positions[:, 1],
        ]
    )
    R_swap = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)
    M = np.eye(4)
    M[:3, :3] = R_swap
    M[:3, 3] = -R_swap @ center
    return positions, M


def _transform_to_local(
    positions: np.ndarray,
    has_ecef: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """Transform positions to local Z-up coordinates.

    ECEF data gets rotated to ENU (already Z-up).
    Local data (from voxelearth/glTF) is Y-up and gets converted to Z-up
    so the JS Z-to-Y swap produces correct Three.js Y-up output.

    Returns (transformed_positions, transform_4x4).
    """
    if len(positions) == 0:
        return positions, np.eye(4)

    max_coord = np.abs(positions).max()
    if has_ecef and max_coord > _config["ecef"]["detection_threshold"]:
        return _ecef_to_local(positions)
    return _yup_to_zup(positions)


# ---------------------------------------------------------------------------
# Public loading API
# ---------------------------------------------------------------------------


def compute_voxel_size(
    grid_coords: np.ndarray,
    positions: np.ndarray,
) -> float:
    """Compute the world-space size of one voxel from adjacent grid cells."""
    if len(grid_coords) < 2:
        return 1.0
    ref_gc = grid_coords[0]
    ref_pos = positions[0]
    for j in range(1, min(len(grid_coords), 200)):
        diff = np.abs(grid_coords[j] - ref_gc)
        if diff.sum() == 1:
            return float(np.linalg.norm(positions[j] - ref_pos))
    gc_range = grid_coords.max(axis=0) - grid_coords.min(axis=0)
    pos_range = positions.max(axis=0) - positions.min(axis=0)
    gc_max = gc_range.max()
    if gc_max > 0:
        return float(pos_range.max() / gc_max)
    return 1.0


def load_voxels(
    path: str | Path,
    bbox_radius: float = 15.0,
    exterior_only: bool = True,
) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray, float, np.ndarray]:
    """Load voxel JSON, crop to bbox, filter, transform to local Z-up.

    Returns (positions, colors, materials, grid_coords, voxel_size).
    """
    grid_coords, positions, colors, materials = _parse_voxel_json(path)
    voxel_size = compute_voxel_size(grid_coords, positions)

    # Crop to bbox around center
    center = positions.mean(axis=0)
    grid_coords, positions, colors, materials = _crop_to_bbox(
        grid_coords,
        positions,
        colors,
        materials,
        center,
        bbox_radius,
    )

    grid_coords, positions, colors, materials = _apply_filters(
        grid_coords,
        positions,
        colors,
        materials,
        exterior_only,
    )

    has_ecef = np.abs(positions).max() > _config["ecef"]["detection_threshold"] if len(positions) > 0 else False
    positions, transform = _transform_to_local(positions, has_ecef)

    # Match grid_coords axes to the Z-up convention applied to positions.
    # Y-up [gx, gy_up, gz_horiz] -> Z-up [gx, -gz_horiz, gy_up]
    # Only for non-ECEF data (ECEF uses a rotation matrix).
    if not has_ecef and len(grid_coords) > 0:
        grid_coords = np.column_stack(
            [
                grid_coords[:, 0],
                -grid_coords[:, 2],
                grid_coords[:, 1],
            ]
        )

    return positions, colors, materials, grid_coords, voxel_size, transform


def load_voxels_directory(
    dir_path: str | Path,
    bbox_radius: float = 15.0,
    exterior_only: bool = True,
) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray, float, np.ndarray]:
    """Load all voxel JSONs from a directory, crop to bbox, filter, transform.

    Returns (positions, colors, materials, grid_coords, voxel_size).
    """
    dir_path = Path(dir_path)
    files = sorted(dir_path.glob("*_voxels.json"))
    if not files:
        files = sorted(dir_path.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No voxel JSON files found in {dir_path}")

    all_grid = []
    all_pos = []
    all_colors = []
    all_materials: list[str] = []
    per_tile_sizes: list[float] = []

    for f in files:
        try:
            gc, pos, col, mats = _parse_voxel_json(f)
            if len(pos) > 0:
                all_grid.append(gc)
                all_pos.append(pos)
                all_colors.append(col)
                all_materials.extend(mats)
                if len(gc) >= 2:
                    tile_vs = compute_voxel_size(gc, pos)
                    if 0 < tile_vs < 10:
                        per_tile_sizes.append(tile_vs)
                print(f"  Loaded {f.name}: {len(pos):,} voxels")
        except Exception as e:
            print(f"  Warning: skipping {f.name}: {e}")

    if not all_pos:
        raise ValueError(f"No valid voxel data found in {dir_path}")

    positions = np.concatenate(all_pos, axis=0)
    colors = np.concatenate(all_colors, axis=0)

    # Use median per-tile voxel size for robustness across tiles with
    # different resolutions (Google 3D Tiles LOD variation).
    voxel_size = float(np.median(per_tile_sizes)) if per_tile_sizes else 1.0

    # Recompute grid_coords globally from world positions so they form a
    # single consistent grid. Tile-local grid coords are not aligned across
    # tiles with different resolutions.
    grid_coords = np.round(positions / voxel_size).astype(np.int64)

    print(f"  Total merged: {len(positions):,} voxels from {len(files)} files")
    print(f"  Voxel size: {voxel_size:.4f} world units (median of {len(per_tile_sizes)} tiles)")

    # Crop to bbox BEFORE expensive dedup/exterior filter
    center = positions.mean(axis=0)
    grid_coords, positions, colors, all_materials = _crop_to_bbox(
        grid_coords,
        positions,
        colors,
        all_materials,
        center,
        bbox_radius,
    )

    grid_coords, positions, colors, all_materials = _apply_filters(
        grid_coords,
        positions,
        colors,
        all_materials,
        exterior_only,
    )

    has_ecef = np.abs(positions).max() > _config["ecef"]["detection_threshold"] if len(positions) > 0 else False
    positions, transform = _transform_to_local(positions, has_ecef)

    # Match grid_coords axes to the Z-up convention applied to positions.
    # Y-up [gx, gy_up, gz_horiz] -> Z-up [gx, -gz_horiz, gy_up]
    # Only for non-ECEF data (ECEF uses a rotation matrix).
    if not has_ecef and len(grid_coords) > 0:
        grid_coords = np.column_stack(
            [
                grid_coords[:, 0],
                -grid_coords[:, 2],
                grid_coords[:, 1],
            ]
        )

    return positions, colors, all_materials, grid_coords, voxel_size, transform


# ---------------------------------------------------------------------------
# Body mesh loading
# ---------------------------------------------------------------------------


def load_body(name: str, data_dir: str) -> BodyMesh:
    """Load a body mesh by name from the data directory."""
    stl_path = Path(data_dir) / f"{name}.stl"
    if not stl_path.exists():
        raise FileNotFoundError(f"Body mesh not found: {stl_path}")
    return BodyMesh.load(str(stl_path))


# ---------------------------------------------------------------------------
# Binary serialization for efficient transfer to Three.js
# ---------------------------------------------------------------------------


def body_to_binary(body: BodyMesh) -> tuple[bytes, dict]:
    """Serialize body mesh for Three.js BufferGeometry."""
    flat_v = body.vertices.reshape(-1, 3).astype(np.float32)
    flat_n = np.repeat(body.normals, 3, axis=0).astype(np.float32)

    data = flat_v.tobytes() + flat_n.tobytes()
    meta = {
        "n_triangles": body.n_triangles,
        "n_vertices": len(flat_v),
        "total_area_cm2": round(body.total_area * 1e4, 1),
        "name": body.name,
    }
    return data, meta


def voxels_to_binary(
    positions: np.ndarray,
    colors: np.ndarray,
    materials: list[str],
    voxel_size: float = 1.0,
) -> tuple[bytes, dict]:
    """Serialize voxels for Three.js InstancedMesh."""
    pos_bytes = positions.astype(np.float32).tobytes()
    col_bytes = colors.astype(np.uint8).tobytes()
    data = pos_bytes + col_bytes

    from collections import Counter

    mat_counts = Counter(materials)

    unique_mats = sorted(set(materials))
    mat_to_idx = {m: i for i, m in enumerate(unique_mats)}
    mat_indices = np.array([mat_to_idx[m] for m in materials], dtype=np.uint8)

    data += mat_indices.tobytes()

    meta = {
        "n_voxels": len(positions),
        "materials": unique_mats,
        "material_counts": {m: c for m, c in mat_counts.items()},
        "voxel_size": voxel_size,
    }
    return data, meta


def find_body_placement(positions: np.ndarray, materials: list[str]) -> list[float]:
    """Find a good street-level position to place the body.

    Returns [x, y, z] in Z-up coordinates (z = vertical).
    """
    mc = _config["material_classification"]
    min_voxels = mc["min_voxels_for_material"]
    pct = mc["ground_height_percentile"]
    margin = mc["ground_height_margin"]
    z_offset = mc["ground_center_z_offset"]

    mat_arr = np.array(materials)

    for target in ["asphalt", "concrete"]:
        mask = mat_arr == target
        if mask.sum() < min_voxels:
            continue
        subset = positions[mask]
        z_vals = subset[:, 2]
        z_low = np.percentile(z_vals, pct)
        ground_mask = z_vals <= z_low + margin
        ground = subset[ground_mask]
        if len(ground) > 0:
            center = np.median(ground, axis=0)
            center[2] = z_low + z_offset
            return center.tolist()

    z_vals = positions[:, 2]
    z_low = np.percentile(z_vals, pct)
    ground = positions[z_vals <= z_low + margin]
    center = np.median(ground, axis=0) if len(ground) > 0 else positions.mean(axis=0)
    center[2] = z_low + z_offset
    return center.tolist()


def sab_to_binary(sab: np.ndarray) -> bytes:
    """Serialize S_ab array for vertex color update."""
    return sab.astype(np.float32).tobytes()
