# Voxel hull: fix axis bug, greedy meshing, wireframe display

**Date:** 2026-03-20
**Status:** Draft

## Problem

The ray-tracing hull mesh displayed in the AEGIS viewer shows "venetian blinds" instead of flat surfaces. Root cause: `grid_coords` (used for neighbor detection) stay in Y-up coordinates from Voxel Earth, while `positions` (used for vertex placement) are transformed to Z-up by `_transform_to_local()`. The axis mismatch causes the wrong faces to be emitted.

Additionally, the hull emits two triangles per exposed voxel face with no merging. A flat floor of 1000 voxels produces 2000+ triangles instead of 2. This inflates DiffeRT ray-tracing cost linearly.

## Scope

Three changes, all in the existing voxel-to-hull pipeline:

1. **Fix axis mismatch** in grid_coords
2. **Greedy meshing** to merge coplanar faces
3. **Wireframe display** in the viewer

ECEF branch grid_coords handling is out of scope for this change (ECEF applies a rotation matrix, which would produce non-integer grid coords). The ECEF path is rarely used and can be addressed separately.

## Design

### Layer 1: Fix axis mismatch

**File:** `src/aegis/viewer/scene_data.py`

In `load_voxels()` and `load_voxels_directory()`, **immediately after** `_transform_to_local()` transforms positions from Y-up to Z-up, apply the same axis swap to `grid_coords`:

```python
positions, transform = _transform_to_local(positions, has_ecef)

# Match grid_coords to the same Z-up convention as positions.
# Only needed for non-ECEF (Y-up) data.
if not has_ecef:
    grid_coords = np.column_stack([
        grid_coords[:, 0],
        -grid_coords[:, 2],
        grid_coords[:, 1],
    ])
```

**Placement rationale:** `compute_voxel_size()` runs before `_transform_to_local()` while both grid_coords and positions are still Y-up, so it is unaffected. `extract_exterior()` (called inside `_apply_filters()`) also runs before the swap. `extract_exterior()` produces a per-voxel boolean mask (is this voxel on the surface?), which is invariant under axis permutation since 6-neighbor connectivity is symmetric. The per-face exposure test in `round_triangle_scene()` is the axis-dependent part, and it runs later with both arrays now consistently in Z-up.

The negation (`-grid_coords[:, 2]`) can produce negative integer coordinates. This is safe because `round_triangle_scene()` shifts grid coords to a tight non-negative box via `gc_shifted = gc - offsets` before building the occupancy array.

**Validation:** A single-layer floor of voxels should produce only +Z and -Z faces (horizontal), no vertical side faces except at edges.

### Layer 2: Greedy meshing

**File:** `src/aegis/viewer/raytracer.py`, new function `greedy_mesh_faces()`

After identifying exposed faces per direction (the existing loop in `round_triangle_scene()`), instead of emitting one quad per face, run a greedy merge on the 2D grid of exposed faces for that direction.

**Algorithm** (per face direction):

1. Collect all exposed face grid positions for this direction into a 2D grid. For a +Z face, the grid axes are X and Y. For a +X face, the grid axes are Y and Z. Etc.
2. Create a boolean 2D mask of which grid cells have an exposed face.
3. Greedy sweep: iterate rows. For each unvisited cell, expand right as far as possible (all cells in the row are exposed and unvisited). Then expand down as far as possible (all cells in those rows across the same column span are exposed and unvisited). Mark the rectangle as visited. Emit one quad (2 triangles) for the merged rectangle.

**Mapping from face direction to 2D grid axes and fixed axis:**

| Direction | Fixed axis (value) | Grid axis u (index) | Grid axis v (index) |
|-----------|-------------------|---------------------|---------------------|
| +X        | x = +hs           | 1 (y)               | 2 (z)               |
| -X        | x = -hs           | 1 (y)               | 2 (z)               |
| +Y        | y = +hs           | 0 (x)               | 2 (z)               |
| -Y        | y = -hs           | 0 (x)               | 2 (z)               |
| +Z        | z = +hs           | 0 (x)               | 1 (y)               |
| -Z        | z = -hs           | 0 (x)               | 1 (y)               |

**Vertex generation for a merged rectangle** spanning grid cells `[u0..u1, v0..v1]`:

Compute world-space corners from grid coordinates and voxel_size, not from `positions[]` lookups. This avoids depending on positions being perfectly grid-aligned.

For a +Z face merging grid cells x in [x0, x1], y in [y0, y1] at grid z-level `gz`:

```python
# World-space origin of the merged rectangle (corner of first voxel)
# Use the grid-to-world mapping: world = (grid_coord - offset) * voxel_size + origin
# Then add face corner offsets.
hs = voxel_size / 2
world_x0 = base_x + x0 * voxel_size - hs
world_x1 = base_x + (x1 + 1) * voxel_size - hs  # +1 because x1 is inclusive
world_y0 = base_y + y0 * voxel_size - hs
world_y1 = base_y + (y1 + 1) * voxel_size - hs
world_z  = base_z + gz * voxel_size + hs  # +hs for top face

# Four corners, same winding as face_corners[4] (+Z):
# [bottom-left, bottom-right, top-right, top-left]
corners = [
    [world_x0, world_y0, world_z],  # was [-hs, -hs, hs]
    [world_x1, world_y0, world_z],  # was [+hs, -hs, hs]
    [world_x1, world_y1, world_z],  # was [+hs, +hs, hs]
    [world_x0, world_y1, world_z],  # was [-hs, +hs, hs]
]
```

Each face direction follows the same pattern: the two grid axes expand from single-voxel half-size offsets to the full rectangle extent, while the fixed axis keeps its half-voxel offset. The vertex order matches the corresponding entry in the existing `face_corners` array, preserving outward-facing normals.

**Complexity:** O(N) per face direction where N is the number of exposed faces. The 2D grid is dense (allocated as a boolean array sized to the bounding box of exposed faces for that direction/slice), which is acceptable given typical voxel densities. Total across all 6 directions equals total exposed faces.

**Output:** The function replaces the inner loop of `round_triangle_scene()`. The rest of the function (occupancy grid, DiffeRT scene construction) stays the same.

### Layer 3: Wireframe display

**File:** `src/aegis/viewer/templates/index.html`

When the "Ray-tracing hull mesh" display mode is selected, render the hull as wireframe:

```javascript
const mat = new THREE.MeshStandardMaterial({
    color: hexToInt(sCfg.color),
    wireframe: true,
    side: THREE.DoubleSide,
});
```

The hull mesh should also be included in the existing global wireframe toggle (lines 1806-1812) so that the user can switch between wireframe and solid views. Default to wireframe when hull mode is first selected.

Update the hint text to show triangle count.

## What this does NOT change

- The voxel cube display (InstancedMesh) is unchanged.
- `extract_exterior()` logic is unchanged.
- The DiffeRT TriangleScene output format is unchanged. Ray tracing code sees fewer triangles but the same interface.
- The binary serialization format is unchanged.
- No new dependencies.
- ECEF branch grid_coords handling (out of scope).

## Testing

- **Existing test:** `test_voxel_rt_mesh.py` has triangle count assertions. These will change (fewer triangles after greedy meshing). Update expected counts.
- **New test: axis swap.** Build hull from a known flat floor (single Z-layer). Compute face normals for all triangles. Assert interior faces have normals pointing +Z or -Z only (no vertical normals except at edges).
- **New test: greedy merge counts.** A 4x4 flat floor should produce exactly 2 triangles on top, 2 on bottom, plus 16 edge side-face triangles (4 sides, 4 voxels per side, 2 triangles each). Total: 36 triangles.
- **New test: L-shape.** 5 voxels in an L (3 + 2 overlapping at corner). Top face splits into 2 rectangles, producing 4 top-face triangles, 4 bottom-face triangles, plus side faces. Assert exact count.
- **New test: normal direction.** For every triangle in the hull, compute the normal and verify it points outward (dot product of face normal with the face direction vector is positive). This catches winding order bugs.
- **New test: non-unit voxel size.** Run greedy meshing with voxel_size=0.5. Verify merged rectangle extents are correct (world-space dimensions should be voxel_size * grid_span).
- **Visual verification:** Load the viewer, switch to hull mode, confirm the floor shows as large triangles in wireframe, not venetian blinds.

## Files changed

| File | Change |
|------|--------|
| `src/aegis/viewer/scene_data.py` | Swap grid_coords axes immediately after `_transform_to_local()` |
| `src/aegis/viewer/raytracer.py` | Add `greedy_mesh_faces()`, integrate into `round_triangle_scene()` |
| `src/aegis/viewer/templates/index.html` | Wireframe material for hull mesh, integrate with global wireframe toggle |
| `tests/test_voxel_rt_mesh.py` | Update triangle counts, add axis/greedy/normal/voxel-size tests |
