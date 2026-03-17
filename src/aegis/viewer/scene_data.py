"""Data loading and binary serialization for the viewer."""

from __future__ import annotations

import colorsys
import json
from pathlib import Path

import numpy as np

from aegis.geometry.mesh import BodyMesh

# ---------------------------------------------------------------------------
# Material classification (from spike_viewer.py)
# ---------------------------------------------------------------------------


def classify_material(r: int, g: int, b: int) -> str:
    rf, gf, bf = r / 255, g / 255, b / 255
    h, s, v = colorsys.rgb_to_hsv(rf, gf, bf)
    hue = h * 360

    if s < 0.08:
        return "asphalt" if v < 0.35 else "concrete"
    if v < 0.15:
        return "asphalt"
    if 60 < hue < 150 and s > 0.15 and v > 0.2:
        return "vegetation"
    if 40 < hue < 60 and s > 0.25 and v > 0.25:
        return "vegetation"
    if (hue < 40 or hue > 330) and s > 0.15:
        return "brick"
    if 160 < hue < 280:
        if s > 0.6 and v > 0.4:
            return "water"
        if s > 0.45 and v > 0.55:
            return "glass"
        return "concrete"
    if s < 0.15:
        return "asphalt" if v < 0.35 else "concrete"
    if 20 < hue < 50 and s < 0.4:
        return "brick"
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

    Parameters
    ----------
    grid_coords : (N, 3) integer grid positions

    Returns
    -------
    (N,) boolean mask, True for exterior voxels.
    """
    coords = grid_coords.astype(np.int64)
    occupied = set(map(tuple, coords))

    mask = np.zeros(len(coords), dtype=bool)
    for i, (x, y, z) in enumerate(coords):
        for dx, dy, dz in _NEIGHBORS_6:
            if (x + dx, y + dy, z + dz) not in occupied:
                mask[i] = True
                break

    return mask


# ---------------------------------------------------------------------------
# Voxel loading
# ---------------------------------------------------------------------------


def _parse_voxel_json(path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
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


def _apply_exterior_filter(
    grid_coords: np.ndarray,
    positions: np.ndarray,
    colors: np.ndarray,
    materials: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Remove interior voxels and return filtered arrays."""
    n = len(positions)
    if n == 0:
        return grid_coords, positions, colors, materials

    ext_mask = extract_exterior(grid_coords)
    n_interior = n - int(ext_mask.sum())
    if n_interior > 0:
        print(
            f"  Exterior filter: {n:,} -> {int(ext_mask.sum()):,} "
            f"({n_interior:,} interior removed, {n_interior / n * 100:.1f}%)"
        )
        grid_coords = grid_coords[ext_mask]
        positions = positions[ext_mask]
        colors = colors[ext_mask]
        materials = [m for m, keep in zip(materials, ext_mask, strict=True) if keep]

    return grid_coords, positions, colors, materials


def _subsample(
    positions: np.ndarray,
    colors: np.ndarray,
    materials: list[str],
    max_voxels: int,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Subsample if over max_voxels."""
    n = len(positions)
    if n > max_voxels:
        step = n // max_voxels
        idx = np.arange(0, n, step)[:max_voxels]
        positions = positions[idx]
        colors = colors[idx]
        materials = [materials[i] for i in idx]
        print(f"  Subsampled {n:,} -> {len(positions):,} voxels")
    return positions, colors, materials


def _transform_to_local(positions: np.ndarray, has_ecef: bool) -> np.ndarray:
    """Transform positions to local coordinates (ECEF-to-ENU if needed, else center)."""
    if len(positions) == 0:
        return positions

    max_coord = np.abs(positions).max()
    if has_ecef and max_coord > 100000:
        center_ecef = positions.mean(axis=0)
        positions = positions - center_ecef
        lon_rad = np.arctan2(center_ecef[1], center_ecef[0])
        lat_rad = np.arctan2(center_ecef[2], np.sqrt(center_ecef[0] ** 2 + center_ecef[1] ** 2))
        R = ecef_to_enu_matrix(np.degrees(lon_rad), np.degrees(lat_rad))
        positions = positions @ R.T
    else:
        positions = positions - positions.mean(axis=0)

    return positions


def load_voxels(
    path: str | Path,
    max_voxels: int = 60000,
    exterior_only: bool = True,
) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    """Load voxel JSON, remove interior voxels, transform to local coords.

    Parameters
    ----------
    path : path to voxel JSON file
    max_voxels : subsample cap (applied after exterior extraction)
    exterior_only : if True, remove voxels completely surrounded by neighbors

    Returns (positions (N,3), colors (N,3 uint8), materials list[str],
             grid_coords (N,3 int64)).
    """
    grid_coords, positions, colors, materials = _parse_voxel_json(path)

    if exterior_only:
        grid_coords, positions, colors, materials = _apply_exterior_filter(grid_coords, positions, colors, materials)

    positions, colors, materials = _subsample(positions, colors, materials, max_voxels)

    has_ecef = np.abs(positions).max() > 100000 if len(positions) > 0 else False
    positions = _transform_to_local(positions, has_ecef)

    return positions, colors, materials, grid_coords


def load_voxels_directory(
    dir_path: str | Path,
    max_voxels: int = 60000,
    exterior_only: bool = True,
) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    """Load all voxel JSONs from a directory, merge, filter, and transform.

    Parameters
    ----------
    dir_path : directory containing *_voxels.json files
    max_voxels : subsample cap after merge
    exterior_only : if True, remove interior voxels from the merged set

    Returns (positions (N,3), colors (N,3 uint8), materials list[str],
             grid_coords (N,3 int64)).
    """
    dir_path = Path(dir_path)
    files = sorted(dir_path.glob("*_voxels.json"))
    if not files:
        # Fall back to any .json file
        files = sorted(dir_path.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No voxel JSON files found in {dir_path}")

    all_grid = []
    all_pos = []
    all_colors = []
    all_materials: list[str] = []

    for f in files:
        try:
            gc, pos, col, mats = _parse_voxel_json(f)
            if len(pos) > 0:
                all_grid.append(gc)
                all_pos.append(pos)
                all_colors.append(col)
                all_materials.extend(mats)
                print(f"  Loaded {f.name}: {len(pos):,} voxels")
        except Exception as e:
            print(f"  Warning: skipping {f.name}: {e}")

    if not all_pos:
        raise ValueError(f"No valid voxel data found in {dir_path}")

    grid_coords = np.concatenate(all_grid, axis=0)
    positions = np.concatenate(all_pos, axis=0)
    colors = np.concatenate(all_colors, axis=0)
    print(f"  Total merged: {len(positions):,} voxels from {len(files)} files")

    if exterior_only:
        grid_coords, positions, colors, all_materials = _apply_exterior_filter(
            grid_coords, positions, colors, all_materials
        )

    positions, colors, all_materials = _subsample(positions, colors, all_materials, max_voxels)

    has_ecef = np.abs(positions).max() > 100000 if len(positions) > 0 else False
    positions = _transform_to_local(positions, has_ecef)

    return positions, colors, all_materials, grid_coords


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
    """Serialize body mesh for Three.js BufferGeometry.

    Returns (binary data, metadata dict).
    The binary data contains: positions (M*3*3 float32), normals (M*3 float32).
    """
    # Flatten: (M, 3, 3) -> (M*3, 3) for positions
    flat_v = body.vertices.reshape(-1, 3).astype(np.float32)
    # Repeat face normals for each vertex: (M, 3) -> (M*3, 3)
    flat_n = np.repeat(body.normals, 3, axis=0).astype(np.float32)

    data = flat_v.tobytes() + flat_n.tobytes()
    meta = {
        "n_triangles": body.n_triangles,
        "n_vertices": len(flat_v),
        "total_area_cm2": round(body.total_area * 1e4, 1),
        "name": body.name,
    }
    return data, meta


def voxels_to_binary(positions: np.ndarray, colors: np.ndarray, materials: list[str]) -> tuple[bytes, dict]:
    """Serialize voxels for Three.js InstancedMesh.

    Returns (binary data, metadata dict).
    Binary: positions (N*3 float32) + colors (N*3 uint8).
    """
    pos_bytes = positions.astype(np.float32).tobytes()
    col_bytes = colors.astype(np.uint8).tobytes()
    data = pos_bytes + col_bytes

    from collections import Counter

    mat_counts = Counter(materials)

    # Material indices for grouping
    unique_mats = sorted(set(materials))
    mat_to_idx = {m: i for i, m in enumerate(unique_mats)}
    mat_indices = np.array([mat_to_idx[m] for m in materials], dtype=np.uint8)

    data += mat_indices.tobytes()

    meta = {
        "n_voxels": len(positions),
        "materials": unique_mats,
        "material_counts": {m: c for m, c in mat_counts.items()},
    }
    return data, meta


def find_body_placement(positions: np.ndarray, materials: list[str]) -> list[float]:
    """Find a good street-level position to place the body.

    Looks for asphalt (street) voxels near the ground. Falls back to the
    lowest open area if no asphalt exists.

    Returns [x, y, z] in the same coordinate system as the voxel positions.
    """
    mat_arr = np.array(materials)

    # Try asphalt first (streets), then concrete
    for target in ["asphalt", "concrete"]:
        mask = mat_arr == target
        if mask.sum() < 5:
            continue
        subset = positions[mask]
        # Pick voxels near the lowest Z (ground level)
        z_vals = subset[:, 2]
        z_low = np.percentile(z_vals, 10)
        ground_mask = z_vals <= z_low + 2.0
        ground = subset[ground_mask]
        if len(ground) > 0:
            # Pick the median position among ground voxels
            center = np.median(ground, axis=0)
            # Place body on top of the ground voxel (offset Z by +1)
            center[2] = z_low + 1.0
            return center.tolist()

    # Fallback: lowest 10% of all voxels, median position
    z_vals = positions[:, 2]
    z_low = np.percentile(z_vals, 10)
    ground = positions[z_vals <= z_low + 2.0]
    center = np.median(ground, axis=0) if len(ground) > 0 else positions.mean(axis=0)
    center[2] = z_low + 1.0
    return center.tolist()


def sab_to_binary(sab: np.ndarray) -> bytes:
    """Serialize S_ab array for vertex color update.

    Returns per-face S_ab as float32 bytes.
    """
    return sab.astype(np.float32).tobytes()
