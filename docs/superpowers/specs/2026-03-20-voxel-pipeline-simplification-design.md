# Voxel pipeline simplification

## Problem

The AEGIS viewer post-processes voxel data from VoxelEarth in ways that introduce visual artifacts (gaps and overlaps between voxels). Empirical measurement shows 55% of voxels drift by more than half a voxel width from their true position, and 39% of voxels are falsely removed as "duplicates." The root cause is that we force all tiles onto a single grid by rounding, when the upstream data already contains correct world positions.

## Context

VoxelEarth's `nodejs-voxelearth` pipeline voxelizes Google 3D Tiles into per-tile JSON files. Each file contains:

- Per-voxel integer grid coordinates (`x`, `y`, `z`) in tile-local space
- Per-voxel world positions (`wx`, `wy`, `wz`) in a local Y-up frame (meters, shared origin across tiles)
- Tile metadata: `unit` (voxel size, always cubic), `bbox`, `worldOffset`, `gridSize`
- Surface-only voxels (hollow shell, not solid fill) produced by a 2.5D surface scan

Tiles arrive at different resolutions because Google serves different LODs. A scene might have tiles with voxel sizes ranging from 0.018m to 0.227m (observed in Boston dataset, 12x range). Even nearby tiles (Ghent) show 2.5% size differences.

The AEGIS viewer renders these voxels in Three.js (Y-up) and optionally feeds them into a greedy meshing pipeline for ray tracing (Z-up).

## Current pipeline (what is wrong)

```
voxelearth JSON
  -> parse wx/wy/wz + grid coords
  -> compute_voxel_size() from adjacent grid cells (ignores metadata)
  -> crop to bbox
  -> dedup by grid coords (after snapping to single median grid)
  -> exterior filter (6-neighbor adjacency)
  -> Y-up -> Z-up transform (for AEGIS internal convention)
  -> grid coord axis swap
  -> serialize to binary
  -> JS loads, applies Z-up -> Y-up swap
  -> render
```

Problems:
1. **Grid snapping destroys position accuracy.** `np.round(positions / median_voxel_size)` forces all tiles onto one grid. Measured drift: mean 0.13m, 55% of voxels move > half a voxel width.
2. **False dedup.** Grid snapping maps distinct voxels from overlapping tiles to the same cell. 39% of voxels removed (70k in Ghent dataset). Many are not true duplicates.
3. **Redundant coordinate round-trip.** Y-up -> Z-up in Python, then Z-up -> Y-up in JS. Data starts Y-up, Three.js wants Y-up. Net effect: precision noise.
4. **Redundant voxel size computation.** `compute_voxel_size()` heuristically measures distance between adjacent grid cells. The JSON metadata already has the exact `unit` field.
5. **Redundant exterior filter.** VoxelEarth's 2.5D scan only outputs surface voxels. The 6-neighbor filter does almost nothing but costs O(n log n).
6. **Dead ECEF code path.** `_ecef_to_local()` handles raw Earth-centered coordinates, but voxelearth always rotates to local frame before outputting. No user ever feeds ECEF voxels.

## Proposed pipeline

### Rendering path (no coordinate transforms)

```
voxelearth JSON
  -> parse wx/wy/wz + read unit.x from tile metadata
  -> crop to bbox (Y-up: horizontal axes 0 and 2)
  -> spatial dedup (position proximity, not grid snapping)
  -> material classify (RGB -> EM material)
  -> serialize to binary (Y-up positions, per-voxel or per-group size)
  -> JS renders directly at (wx, wy, wz) with BoxGeometry(unit, unit, unit)
```

### Ray tracing path (on-demand Z-up conversion)

```
Y-up positions + per-tile unit
  -> Y-up -> Z-up axis swap
  -> compute integer grid coords (from Z-up positions / unit)
  -> greedy mesh -> TriangleScene
```

This conversion happens only when the user triggers ray tracing, not on every load.

## Changes in detail

### 1. Read voxel size from metadata

Replace `compute_voxel_size()` with reading `unit.x` from the JSON top-level object. For backward compatibility with old-format files that lack metadata (just a bare array of voxels), fall back to the current heuristic.

**Single tile:** use that tile's `unit.x` directly.

**Multi-tile:** each tile keeps its own `unit`. The binary format sends a per-voxel or per-resolution-group size to the frontend.

### 2. Remove coordinate round-trip

Delete `_yup_to_zup()`, `_ecef_to_local()`, `_transform_to_local()`, and the grid coord axis swap (lines 431-438 of scene_data.py). Positions stay in native Y-up throughout the rendering pipeline.

Remove the JS-side coordinate swap in `index.html` (`dummy.position.set(positions[i*3], positions[i*3+2], -positions[i*3+1])` becomes `dummy.position.set(positions[i*3], positions[i*3+1], positions[i*3+2])`).

The `_crop_to_bbox` function currently crops on axes 0 and 2 (horizontal in Y-up). This stays correct since positions remain Y-up.

### 3. Spatial dedup instead of grid-based dedup

Replace `_deduplicate()` (which uses `np.unique` on grid coords) with spatial proximity dedup:

- During parsing, `_parse_voxel_json()` returns a per-voxel `tile_unit` float alongside positions and colors. `load_voxels_directory()` concatenates these into a `voxel_sizes` float32 array so each voxel knows its source tile's resolution.
- Build a KD-tree on all voxel positions
- For each pair of voxels within `min(unit_a, unit_b) * 0.5` distance, keep the one from the higher-resolution tile (smaller unit in the `voxel_sizes` array)
- This correctly handles multi-resolution overlap without destroying position accuracy

### 4. Exterior filter default off

Change `exterior_only` default from `True` to `False` in both `load_voxels()` and `load_voxels_directory()`. Keep the function available as an opt-in parameter for edge cases.

### 5. Remove dead ECEF path

Delete `_ecef_to_local()`, `ecef_to_enu_matrix()` references, and the ECEF detection threshold config. VoxelEarth always outputs local-frame coordinates.

### 6. Multi-resolution rendering

Currently the frontend creates one `BoxGeometry(cubeSize, cubeSize, cubeSize)` for all voxels. With multi-resolution tiles, voxels have different sizes.

Approach: group voxels by resolution (round `unit` to 4 decimal places to bucket nearly-identical sizes). Each group gets its own `InstancedMesh` with appropriately sized `BoxGeometry`. This is a small change since the frontend already creates one `InstancedMesh` per material class. The new grouping is by (material, resolution) pairs.

### 7. Return value changes

`load_voxels()` and `load_voxels_directory()` currently return a single `voxel_size` float. This changes to return per-voxel sizes (a float32 array) or a resolution group mapping. The `transform` matrix return value is removed (no transform applied).

Updated signature:
```python
def load_voxels_directory(
    dir_path: str | Path,
    bbox_radius: float = 15.0,
    exterior_only: bool = False,
) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    """Load voxel JSONs, crop, dedup, classify.

    Returns (positions, colors, materials, voxel_sizes).
    Positions are in Y-up local frame (meters).
    voxel_sizes is a float32 array with per-voxel size.
    """
```

### 8. Ray tracing adapter

A new function converts Y-up rendering data to Z-up for the greedy meshing pipeline:

```python
def prepare_for_raytracing(
    positions: np.ndarray,
    voxel_sizes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Convert Y-up positions to Z-up and compute grid coords for greedy meshing.

    Returns (z_up_positions, grid_coords, dominant_voxel_size).
    """
```

This replaces the scattered coordinate transforms currently embedded in the loading pipeline.

The `dominant_voxel_size` is the median of all voxel sizes in the scene. Voxels with very different sizes (the 0.018m outliers in Boston) get snapped to this grid for ray tracing purposes only. This is acceptable because ray tracing needs a uniform grid for greedy meshing, and visual rendering (which uses native positions) is unaffected. Minority-resolution voxels may lose some spatial precision in the ray-traced mesh, but this is a minor effect on ray tracing accuracy.

The compute routes (`routes/compute.py`) and hull mesh endpoint call `extract_exterior()` and `get_or_build_voxel_scene()` on cached grid_coords. These must be updated to call `prepare_for_raytracing()` first, producing Z-up grid_coords on demand rather than expecting them in the cache.

### 9. Update `find_body_placement` for Y-up

`find_body_placement()` in `scene_data.py` uses axis index 2 as vertical (`z_vals = subset[:, 2]`). With positions staying Y-up, vertical is axis 1. Update all vertical-axis references in this function from index 2 to index 1.

### 10. GLB tile transform

The tiles endpoint in `routes/data.py` reads `cache["voxel_transform"]` and composes it with a Z-to-Y swap matrix before sending to the frontend. Since positions now stay Y-up (no Z-up conversion ever happens), both the Z-to-Y swap and the `voxel_transform` are unnecessary. The entire transform block in the tiles endpoint should be removed or replaced with `transform_list = None`. The `voxel_transform` cache entry becomes `None` (no transform). The frontend receives tiles in their native Y-up coordinates, matching the voxel positions.

### 10a. Config key rename

The config key `ground_center_z_offset` in `material_classification` refers to the vertical axis. In Z-up that was axis 2 (Z), but in Y-up it is axis 1 (Y). Rename to `ground_center_vertical_offset` for clarity. Update `find_body_placement` and any config references accordingly.

### 11. Binary serialization format

The binary buffer uses a block layout (matching the existing non-interleaved format): `positions(n*3 float32) + sizes(n float32) + colors(n*3 uint8) + material_indices(n uint8)`. No header. The `n_voxels` count and metadata (including median `voxel_size` for backward compat) are sent in the `X-Meta` JSON response header, same as today.

Frontend parsing in `index.html` reads the `sizes` block and groups voxels by (material, rounded size) for multi-resolution instanced mesh creation.

## What stays the same

- **Bbox cropping** -- AEGIS-specific scene framing, stays as-is
- **Material classification** -- RGB to EM material type, no changes
- **Greedy meshing** -- the algorithm itself is fine, just receives Z-up data from the new adapter
- **`size_scale: 0.99`** -- intentional 1% shrink to prevent z-fighting, stays as-is
- **Binary serialization format** -- extends to include per-voxel size, but same overall structure

## Files affected

| File | Change |
|------|--------|
| `src/aegis/viewer/scene_data.py` | Major: rewrite loading pipeline, remove transforms, add spatial dedup, new return types |
| `src/aegis/viewer/templates/index.html` | Remove Z-to-Y swap, support multi-resolution instanced meshes |
| `src/aegis/viewer/config.py` | Remove ECEF config, add spatial dedup threshold |
| `src/aegis/viewer/server.py` | Update to match new return types from scene_data, cache per-voxel sizes |
| `src/aegis/viewer/raytracer.py` | Use new `prepare_for_raytracing()` adapter |
| `src/aegis/viewer/routes/compute.py` | Call `prepare_for_raytracing()` before exterior filter and scene building |
| `src/aegis/viewer/routes/data.py` | Update voxel_transform to identity, update cache key access |
| `tests/test_voxel_rt_mesh.py` | Update for new API, add regression test for position accuracy |

## Validation

1. **Position accuracy test:** Load Ghent dataset through new pipeline, verify max drift from raw `wx/wy/wz` is zero (positions pass through unchanged).
2. **Visual regression:** Load Ghent and Boston in the viewer, screenshot, verify no visible gaps between voxels of the same tile.
3. **Dedup correctness:** Verify voxel count after spatial dedup is higher than after grid-based dedup (fewer false positives).
4. **Ray tracing still works:** Greedy mesh from `prepare_for_raytracing()` produces valid TriangleScene. Existing hull mesh tests pass.
5. **Backward compatibility:** Old-format voxel JSON (bare array, no metadata) still loads with fallback heuristics.

## Out of scope

- Changing VoxelEarth's pipeline or output format
- Voxel LOD streaming (loading/unloading tiles dynamically based on camera distance)
- Changing the greedy meshing algorithm itself
- Heightmap rendering mode (separate code path, unaffected)
