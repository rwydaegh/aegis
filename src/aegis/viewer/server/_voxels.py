"""Voxel preload helpers used by the app factory."""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

from aegis.viewer.scene_data import (
    find_body_placement,
    load_voxels,
    load_voxels_directory,
    voxels_to_binary,
)

from ._cache import _cache, _cache_lock


def _clear_raytracer_voxel_cache() -> None:
    """Best-effort invalidation of the raytracer's voxel scene cache."""
    try:
        from aegis.viewer.raytracer import clear_voxel_scene_cache

        clear_voxel_scene_cache()
    except ImportError:
        pass


def _cache_loaded_voxels(
    positions,
    colors,
    materials,
    voxel_sizes,
) -> None:
    """Write a loaded voxel set into the shared cache."""
    with _cache_lock:
        _cache["voxel_positions"] = positions
        _cache["voxel_materials"] = materials
        _cache["voxel_sizes"] = voxel_sizes
        _cache["voxel_binary"], _cache["voxel_meta"] = voxels_to_binary(
            positions,
            colors,
            materials,
            voxel_sizes=voxel_sizes,
        )
        _cache["body_placement"] = find_body_placement(positions, materials)
    _clear_raytracer_voxel_cache()


def _load_and_cache_voxels_single(voxel_json: str, bbox_radius: float) -> None:
    """Load a single voxel JSON file into _cache."""
    positions, colors, materials, voxel_sizes = load_voxels(
        voxel_json,
        bbox_radius=bbox_radius,
    )
    _cache_loaded_voxels(positions, colors, materials, voxel_sizes)
    vs = float(np.median(voxel_sizes)) if len(voxel_sizes) > 0 else 0
    print(f"  Voxels: {len(positions):,} loaded, median_size={vs:.4f}")
    print(f"  Body placement: {_cache['body_placement']}")


def _load_and_cache_voxels_dir(voxel_dir: str, bbox_radius: float) -> None:
    """Load all voxel JSONs from a directory into _cache."""
    positions, colors, materials, voxel_sizes = load_voxels_directory(
        voxel_dir,
        bbox_radius=bbox_radius,
    )
    _cache_loaded_voxels(positions, colors, materials, voxel_sizes)
    vs = float(np.median(voxel_sizes)) if len(voxel_sizes) > 0 else 0
    print(f"  Body placement: {_cache['body_placement']}")
    print(f"  Voxels (directory): {len(positions):,} loaded, median_size={vs:.4f}")


def _clear_voxel_cache(cache: dict) -> None:
    cache["voxel_binary"] = None
    cache["voxel_meta"] = None
    cache["voxel_sizes"] = None
    cache["body_placement"] = None
    cache["voxel_positions"] = None


def _try_load_voxels(
    voxel_json: str | None,
    voxel_dir: str | None,
    bbox_radius: float,
    cache: dict,
) -> None:
    """Dispatch to single-file or directory loader, clearing cache on failure."""
    if voxel_dir:
        try:
            _load_and_cache_voxels_dir(voxel_dir, bbox_radius)
        except Exception as e:
            print(f"  Warning: voxel directory load failed: {e}")
            _clear_voxel_cache(cache)
    elif voxel_json:
        try:
            _load_and_cache_voxels_single(voxel_json, bbox_radius)
        except Exception as e:
            print(f"  Warning: voxel load failed: {e}")
            _clear_voxel_cache(cache)
    else:
        _clear_voxel_cache(cache)


def _resolve_tiles_dir(
    voxel_json: str | None,
    voxel_dir: str | None,
    cache: dict,
) -> None:
    """Find the tiles/ directory sibling to the voxel source, if any."""
    cache["tiles_dir"] = None
    _vs = voxel_dir or (str(Path(voxel_json).parent) if voxel_json else None)
    if not _vs:
        return
    _tc = Path(_vs).parent / "tiles"
    if _tc.is_dir() and any(_tc.glob("*.glb")):
        cache["tiles_dir"] = _tc
        from aegis.viewer.pipeline import fix_glb_tiles_dir

        n_fixed = fix_glb_tiles_dir(_tc)
        n_total = len(list(_tc.glob("*.glb")))
        suffix = f" ({n_fixed} fixed)" if n_fixed else ""
        print(f"  Tiles: {n_total} GLB files{suffix}")


def preload_voxels(
    voxel_json: str | None,
    voxel_dir: str | None,
    bbox_radius: float,
    cache: dict,
    cache_lock: threading.RLock,
) -> None:
    """Load voxels and tiles into cache from either a single JSON or a directory."""
    with cache_lock:
        cache["voxel_json_path"] = voxel_json
        _try_load_voxels(voxel_json, voxel_dir, bbox_radius, cache)
        _resolve_tiles_dir(voxel_json, voxel_dir, cache)
