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
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str], float | None]:
    """Parse a single voxel JSON file into arrays.

    Returns (grid_coords (N,3 int64), positions (N,3 float64),
             colors (N,3 uint8), materials list[str], tile_unit float | None).
    tile_unit is read from the top-level "unit.x" field when present.
    """
    with open(str(path)) as f:
        data = json.load(f)

    tile_unit = None
    if isinstance(data, dict):
        unit_obj = data.get("unit")
        if unit_obj is not None:
            tile_unit = float(unit_obj["x"])
        voxels = data.get("voxels", [])
    else:
        voxels = data

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

    return grid_coords, positions, colors, materials, tile_unit


def _crop_to_bbox(
    grid_coords: np.ndarray,
    positions: np.ndarray,
    colors: np.ndarray,
    materials: list[str],
    center: np.ndarray,
    bbox_radius: float,
    *,
    voxel_sizes: np.ndarray | None = None,
) -> tuple:
    """Crop to a horizontal square bbox around center. Keeps all heights.

    Positions are in Y-up format [x, y_up, z_horiz], so horizontal = axes 0 and 2.
    For ECEF data the horizontal axes are still 0 and 2 before ENU transform.
    """
    n = len(positions)
    if n == 0:
        result = (grid_coords, positions, colors, materials)
        if voxel_sizes is not None:
            return result + (voxel_sizes,)
        return result

    mask = (np.abs(positions[:, 0] - center[0]) <= bbox_radius) & (np.abs(positions[:, 2] - center[2]) <= bbox_radius)
    n_kept = int(mask.sum())
    print(f"  Bbox crop ({bbox_radius * 2:.0f}m): {n:,} -> {n_kept:,} voxels")

    result = (
        grid_coords[mask],
        positions[mask],
        colors[mask],
        [m for m, k in zip(materials, mask, strict=True) if k],
    )
    if voxel_sizes is not None:
        return result + (voxel_sizes[mask],)
    return result


def _apply_filters(
    grid_coords: np.ndarray,
    positions: np.ndarray,
    colors: np.ndarray,
    materials: list[str],
    exterior_only: bool = True,
    *,
    voxel_sizes: np.ndarray | None = None,
) -> tuple:
    """Optionally remove interior voxels."""
    n = len(positions)
    if n == 0:
        result = (grid_coords, positions, colors, materials)
        if voxel_sizes is not None:
            return result + (voxel_sizes,)
        return result

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
            if voxel_sizes is not None:
                voxel_sizes = voxel_sizes[ext_mask]

    result = (grid_coords, positions, colors, materials)
    if voxel_sizes is not None:
        return result + (voxel_sizes,)
    return result


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
    exterior_only: bool = False,
) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    """Load voxel JSON, crop to bbox, filter.

    Returns (positions, colors, materials, voxel_sizes).
    Positions are in Y-up local frame (meters), unchanged from JSON.
    voxel_sizes is a per-voxel float32 array.
    """
    grid_coords, positions, colors, materials, tile_unit = _parse_voxel_json(path)

    vs = tile_unit if tile_unit is not None else compute_voxel_size(grid_coords, positions)

    voxel_sizes = np.full(len(positions), vs, dtype=np.float32)

    center = positions.mean(axis=0)
    grid_coords, positions, colors, materials, voxel_sizes = _crop_to_bbox(
        grid_coords,
        positions,
        colors,
        materials,
        center,
        bbox_radius,
        voxel_sizes=voxel_sizes,
    )

    grid_coords, positions, colors, materials, voxel_sizes = _apply_filters(
        grid_coords,
        positions,
        colors,
        materials,
        exterior_only,
        voxel_sizes=voxel_sizes,
    )

    return positions, colors, materials, voxel_sizes


def _spatial_deduplicate(
    positions: np.ndarray,
    colors: np.ndarray,
    materials: list[str],
    voxel_sizes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    """Remove spatially overlapping voxels, keeping higher-resolution ones."""
    from scipy.spatial import cKDTree

    n = len(positions)
    if n == 0:
        return positions, colors, materials, voxel_sizes

    tree = cKDTree(positions)
    max_size = float(np.max(voxel_sizes))
    candidate_pairs = tree.query_pairs(max_size * 0.5)

    keep = np.ones(n, dtype=bool)
    for i, j in candidate_pairs:
        if not keep[i] or not keep[j]:
            continue
        threshold = min(voxel_sizes[i], voxel_sizes[j]) * 0.5
        dist = np.linalg.norm(positions[i] - positions[j])
        if dist > threshold:
            continue
        if voxel_sizes[i] <= voxel_sizes[j]:
            keep[j] = False
        else:
            keep[i] = False

    n_removed = n - keep.sum()
    if n_removed > 0:
        print(f"  Spatial dedup: {n:,} -> {keep.sum():,} ({n_removed:,} removed, {n_removed / n * 100:.1f}%)")

    return (
        positions[keep],
        colors[keep],
        [m for m, k in zip(materials, keep, strict=True) if k],
        voxel_sizes[keep],
    )


def load_voxels_directory(
    dir_path: str | Path,
    bbox_radius: float = 15.0,
    exterior_only: bool = False,
) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    """Load all voxel JSONs from a directory, crop, dedup, classify.

    Returns (positions, colors, materials, voxel_sizes).
    Positions are in Y-up local frame (meters).
    """
    dir_path = Path(dir_path)
    files = sorted(dir_path.glob("*_voxels.json"))
    if not files:
        files = sorted(dir_path.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No voxel JSON files found in {dir_path}")

    all_pos, all_colors, all_materials, all_sizes = [], [], [], []

    for f in files:
        gc, pos, col, mats, tile_unit = _parse_voxel_json(f)
        if len(pos) == 0:
            continue
        vs = tile_unit if tile_unit is not None else compute_voxel_size(gc, pos)
        all_pos.append(pos)
        all_colors.append(col)
        all_materials.extend(mats)
        all_sizes.append(np.full(len(pos), vs, dtype=np.float32))
        print(f"  Loaded {f.name}: {len(pos):,} voxels, unit={vs:.4f}")

    if not all_pos:
        raise ValueError(f"No valid voxel data found in {dir_path}")

    positions = np.concatenate(all_pos, axis=0)
    colors = np.concatenate(all_colors, axis=0)
    voxel_sizes = np.concatenate(all_sizes, axis=0)

    print(f"  Total merged: {len(positions):,} voxels from {len(files)} files")

    # Crop to bbox
    center = positions.mean(axis=0)
    # _crop_to_bbox now accepts voxel_sizes keyword
    result = _crop_to_bbox(
        np.zeros((len(positions), 3), dtype=np.int64),  # dummy grid_coords (not used for rendering)
        positions,
        colors,
        all_materials,
        center,
        bbox_radius,
        voxel_sizes=voxel_sizes,
    )
    _, positions, colors, all_materials, voxel_sizes = result

    # Spatial dedup
    positions, colors, all_materials, voxel_sizes = _spatial_deduplicate(
        positions,
        colors,
        all_materials,
        voxel_sizes,
    )

    # Optional exterior filter (needs grid coords)
    if exterior_only and len(positions) > 0:
        dominant_size = float(np.median(voxel_sizes))
        centered = positions - positions.mean(axis=0)
        gc = np.round(centered / dominant_size).astype(np.int64)
        ext_mask = extract_exterior(gc)
        n_interior = len(positions) - int(ext_mask.sum())
        if n_interior > 0:
            print(f"  Exterior filter: {len(positions):,} -> {int(ext_mask.sum()):,} ({n_interior:,} interior removed)")
            positions = positions[ext_mask]
            colors = colors[ext_mask]
            all_materials = [m for m, keep in zip(all_materials, ext_mask, strict=True) if keep]
            voxel_sizes = voxel_sizes[ext_mask]

    return positions, colors, all_materials, voxel_sizes


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
    voxel_sizes: np.ndarray | None = None,
    voxel_size: float = 1.0,
) -> tuple[bytes, dict]:
    """Serialize voxels for Three.js InstancedMesh."""
    pos_bytes = positions.astype(np.float32).tobytes()

    if voxel_sizes is not None:
        size_bytes = voxel_sizes.astype(np.float32).tobytes()
    else:
        size_bytes = np.full(len(positions), voxel_size, dtype=np.float32).tobytes()

    col_bytes = colors.astype(np.uint8).tobytes()

    from collections import Counter

    mat_counts = Counter(materials)

    unique_mats = sorted(set(materials))
    mat_to_idx = {m: i for i, m in enumerate(unique_mats)}
    mat_indices = np.array([mat_to_idx[m] for m in materials], dtype=np.uint8)

    data = pos_bytes + size_bytes + col_bytes + mat_indices.tobytes()

    meta = {
        "n_voxels": len(positions),
        "materials": unique_mats,
        "material_counts": {m: c for m, c in mat_counts.items()},
        "voxel_size": float(np.median(voxel_sizes)) if voxel_sizes is not None else voxel_size,
        "has_per_voxel_sizes": voxel_sizes is not None,
    }
    return data, meta


def prepare_for_raytracing(
    positions: np.ndarray,
    voxel_sizes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Convert Y-up positions to Z-up and compute grid coords for greedy meshing.

    Y-up [x, y_up, z_horiz] -> Z-up [x, -z_horiz, y_up].

    Returns (z_up_positions, grid_coords, dominant_voxel_size).
    """
    dominant_size = float(np.median(voxel_sizes))

    z_up = np.column_stack(
        [
            positions[:, 0],
            -positions[:, 2],
            positions[:, 1],
        ]
    )

    center = z_up.mean(axis=0)
    centered = z_up - center
    grid_coords = np.round(centered / dominant_size).astype(np.int64)

    return z_up, grid_coords, dominant_size


def find_body_placement(positions: np.ndarray, materials: list[str]) -> list[float]:
    """Find a good street-level position to place the body.

    Returns [x, y, z] in Y-up coordinates (y = vertical).
    """
    mc = _config["material_classification"]
    min_voxels = mc["min_voxels_for_material"]
    pct = mc["ground_height_percentile"]
    margin = mc["ground_height_margin"]
    y_offset = mc["ground_center_vertical_offset"]

    mat_arr = np.array(materials)

    for target in ["asphalt", "concrete"]:
        mask = mat_arr == target
        if mask.sum() < min_voxels:
            continue
        subset = positions[mask]
        y_vals = subset[:, 1]
        y_low = np.percentile(y_vals, pct)
        ground_mask = y_vals <= y_low + margin
        ground = subset[ground_mask]
        if len(ground) > 0:
            center = np.median(ground, axis=0)
            center[1] = y_low + y_offset
            return center.tolist()

    y_vals = positions[:, 1]
    y_low = np.percentile(y_vals, pct)
    ground = positions[y_vals <= y_low + margin]
    center = np.median(ground, axis=0) if len(ground) > 0 else positions.mean(axis=0)
    center[1] = y_low + y_offset
    return center.tolist()


def sab_to_binary(sab: np.ndarray) -> bytes:
    """Serialize S_ab array for vertex color update."""
    return sab.astype(np.float32).tobytes()
