# Material-aware greedy meshing

**Date:** 2026-03-20
**Status:** Draft
**Predecessor:** `2026-03-20-voxel-hull-greedy-meshing-design.md` (implemented the basic greedy mesh)
**Background:** `docs/internal/rt-mesh-optimization-report.md` (investigation into what matters for RT performance)

## Problem

The greedy meshing algorithm in `_greedy_mesh_faces()` ignores per-voxel material labels. `round_triangle_scene()` accepts `materials` and `material_colors` parameters but discards them, assigning all triangles to a single "concrete" material (lines 476-478). Adjacent voxels of different materials (concrete touching brick) get merged into one quad. For ray tracing, this means wrong reflection/transmission coefficients at material boundaries.

Elongated quad aspect ratios were also a concern, but investigation showed this is irrelevant for DiffeRT (which uses brute-force intersection, not BVH). See the RT mesh optimization report for details.

## Scope

One algorithmic change plus plumbing:

1. **Material-aware merging**: only merge faces whose voxels share the same material
2. **Pass materials through** the endpoint to the meshing function
3. **Display per-material colors** in the hull wireframe

Out of scope: aspect ratio optimization (unnecessary for DiffeRT), changing to a different meshing algorithm.

## Design

### Change 1: Material-aware `_greedy_mesh_faces()`

**Current signature:**
```python
def _greedy_mesh_faces(grid_coords, positions, voxel_size) -> np.ndarray
```

**New signature:**
```python
def _greedy_mesh_faces(grid_coords, positions, voxel_size, material_ids) -> tuple[np.ndarray, np.ndarray]
```

Where `material_ids` is a per-voxel integer array (same length as `grid_coords`), and the return is `(vertices, quad_material_ids)` where `quad_material_ids[i]` is the material index for quad `i`.

The caller (`round_triangle_scene`) always provides `material_ids`. When no materials are given by the user, `round_triangle_scene` defaults to all-zeros (every voxel is "concrete", material ID 0). So `_greedy_mesh_faces` can assume `material_ids` is always a valid int32 array.

**Algorithm change:** The 2D grid per slice currently stores a boolean (occupied or not). Change it to store the material ID (or -1 for empty). The merge loop checks that all cells in a candidate rectangle share the same material ID, not just that they're occupied.

Specifically, in the inner loop:
```python
# Current: grid_2d is bool
grid_2d[u_coords - u_min, v_coords - v_min] = True

# New: grid_2d stores material ID, -1 = empty
mat_grid = np.full((u_span, v_span), -1, dtype=np.int32)
mat_grid[u_coords - u_min, v_coords - v_min] = slice_mat_ids
```

And the merge condition changes from:
```python
if not grid_2d[u, v] or visited[u, v]:
    continue
# extend: grid_2d[u + w, v] and not visited[u + w, v]
```

To:
```python
cur_mat = mat_grid[u, v]
if cur_mat < 0 or visited[u, v]:
    continue
# extend: mat_grid[u + w, v] == cur_mat and not visited[u + w, v]
```

This naturally prevents merging across material boundaries with minimal overhead. The 2D grid changes from `bool` to `int32`, adding negligible memory.

### Change 2: Pass materials through the pipeline

**`routes/compute.py` (`api_voxels_hull_mesh`):**

Read `voxel_materials` from cache, apply the same `ext_mask` filter as positions, and pass to `get_or_build_voxel_scene()`:

```python
voxel_materials = cache.get("voxel_materials")
# ... after ext_mask ...
ext_materials = [voxel_materials[i] for i in np.where(ext_mask)[0]] if voxel_materials else None
scene = get_or_build_voxel_scene(ext_pos, ext_grid, voxel_size=vs, materials=ext_materials)
```

The same change applies to `api_compute_voxel_rt` (lines 288-360 of `compute.py`), which also calls `get_or_build_voxel_scene` without materials. Both endpoints need to read `voxel_materials` from cache and filter by `ext_mask`.

Note: `ext_mask` has the same length as the original `voxel_positions` array (the Y-up to Z-up transform in `prepare_for_raytracing` is element-wise, not a reorder), so indexing `voxel_materials` with it is safe.

**`raytracer.py` (`round_triangle_scene`):**

Convert the per-voxel material name list to integer IDs:
```python
unique_materials = sorted(set(materials)) if materials else ["concrete"]
mat_name_to_id = {name: i for i, name in enumerate(unique_materials)}
material_ids = np.array([mat_name_to_id[m] for m in materials], dtype=np.int32)
```

Pass `material_ids` to `_greedy_mesh_faces()`. Use the returned `quad_material_ids` to build `face_materials` (each quad becomes 2 triangles, both get the same material ID).

Build `face_colors` from the config `material_colors` mapping.

### Change 3: Per-material colors in hull wireframe

**Binary format:** `scene_geometry_to_binary()` already supports `face_colors` (appended after triangle indices, flagged by `has_face_colors`). We populate `face_colors` instead of passing `None`. No binary format change needed.

The `face_materials` data stays in the TriangleMesh object for DiffeRT's use but is not added to the binary wire format. The frontend only needs colors, not material indices. The `material_names` list is already sent in the X-Meta JSON header.

**Frontend (`index.html`):** Use the existing face_colors to set per-face vertex colors on the hull mesh geometry. This gives per-triangle material coloring within a single mesh. Read face_colors from binary, apply as a color attribute on the BufferGeometry with `vertexColors: true` on the material.

## Data flow (after changes)

```
cache: voxel_positions, voxel_materials, voxel_sizes
    |
    v
prepare_for_raytracing() -> z_up positions, grid_coords, voxel_size
extract_exterior() -> ext_mask
    |
    v
ext_positions, ext_grid, ext_materials (all filtered by ext_mask)
    |
    v
round_triangle_scene(positions, grid_coords, voxel_size, materials=ext_materials)
    |-- unique_materials = sorted(set(materials))
    |-- material_ids = [mat_name_to_id[m] for m in materials]
    |-- vertices, quad_mat_ids = _greedy_mesh_faces(grid_coords, positions, voxel_size, material_ids)
    |-- face_materials = quad_mat_ids repeated for each triangle pair
    |-- face_colors = material_colors[face_materials]
    |
    v
TriangleMesh(vertices, triangles, face_materials, material_names, face_colors)
    |
    v
scene_geometry_to_binary() -> binary with face_colors
    |
    v
Frontend: BufferGeometry with vertex colors per triangle
```

## What this does NOT change

- The voxel cube display (InstancedMesh, per-material coloring) is unchanged
- `extract_exterior()` logic is unchanged
- The binary serialization format is unchanged (face_colors field already supported, just newly populated)
- The DiffeRT TriangleScene interface is unchanged (face_materials already a field)
- No new dependencies
- The voxel scene cache (`_voxel_scene_cache`) is cleared on voxel reload via `clear_voxel_scene_cache()` in `server.py`, so stale material-less cache entries are not a concern

## Testing

- **Material boundary test:** Create a 4x4 grid where left half is "concrete" and right half is "brick". Verify no quad spans the material boundary. Assert face_materials has both material IDs.
- **Material color test:** Verify face_colors match the expected RGB from config `material_colors` for each material.
- **Regression:** Existing `test_voxel_rt_mesh.py` tests still pass (triangle counts may change slightly due to material boundaries preventing some merges).
- **Round-trip:** Build hull, serialize to binary, parse in test, verify face_colors and material_names are present and correct.

## Files changed

| File | Change |
|------|--------|
| `src/aegis/viewer/raytracer.py` | `_greedy_mesh_faces()`: add material_ids param, material-aware merge. `round_triangle_scene()`: wire up materials, build face_colors/face_materials. |
| `src/aegis/viewer/routes/compute.py` | `api_voxels_hull_mesh` and `api_compute_voxel_rt`: read voxel_materials from cache, pass through pipeline. |
| `src/aegis/viewer/templates/index.html` | Hull mesh: read face_colors from binary, apply as vertex colors on BufferGeometry. |
| `tests/test_voxel_rt_mesh.py` | Add material boundary, color, and round-trip tests. |
