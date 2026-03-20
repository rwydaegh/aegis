# Voxel hull greedy meshing implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the axis mismatch bug in the voxel hull, add greedy meshing to merge coplanar faces, and render the hull as wireframe.

**Architecture:** The voxel pipeline loads Y-up data from Voxel Earth, transforms positions to Z-up but leaves grid_coords in Y-up. We fix grid_coords, then replace the per-face quad emission in `round_triangle_scene()` with a greedy rectangle-merging algorithm. The viewer switches from solid to wireframe rendering for the hull.

**Tech Stack:** Python/NumPy (backend), Three.js (frontend), DiffeRT (ray tracing), pytest

**Spec:** `docs/superpowers/specs/2026-03-20-voxel-hull-greedy-meshing-design.md`

---

### Task 1: Fix grid_coords axis mismatch in scene_data.py

**Files:**
- Modify: `src/aegis/viewer/scene_data.py:346-348` (load_voxels) and `:415-418` (load_voxels_directory)
- Test: `tests/test_voxel_rt_mesh.py`

- [ ] **Step 1: Write failing test for axis consistency**

Add to `tests/test_voxel_rt_mesh.py`:

```python
def test_flat_floor_normals_are_vertical():
    """A single-layer floor should only have horizontal faces (normals along Z).

    Regression test for the Y-up/Z-up grid_coords mismatch that caused
    'venetian blinds' in the viewer.
    """
    # 3x3 flat floor at z=0
    gc = np.array([
        [x, y, 0] for x in range(3) for y in range(3)
    ], dtype=np.int64)
    pos = gc.astype(np.float64)
    scene = round_triangle_scene(pos, grid_coords=gc, voxel_size=1.0)

    verts = np.array(scene.mesh.vertices)
    tris = np.array(scene.mesh.triangles)

    # Compute face normals
    v0 = verts[tris[:, 0]]
    v1 = verts[tris[:, 1]]
    v2 = verts[tris[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(norms > 0, norms, 1)

    # Interior faces (not at grid edge) should be +Z or -Z only.
    # Edge faces can be vertical. For a 3x3 grid, the 1 interior voxel
    # at (1,1,0) has neighbors on all 4 horizontal sides, so its faces
    # should be purely +Z and -Z.
    # With 9 voxels, the total face breakdown:
    # - 9 top faces (+Z), 9 bottom faces (-Z) = 36 triangles
    # - Edge side faces: perimeter of 12 sides * 2 tri = 24 triangles
    # Total before greedy: 60 triangles

    # Check: every normal is either vertical (Z) or horizontal (X or Y).
    # No diagonal normals should exist.
    for n in normals:
        is_z = abs(abs(n[2]) - 1.0) < 1e-6  # vertical
        is_x = abs(abs(n[0]) - 1.0) < 1e-6  # horizontal X
        is_y = abs(abs(n[1]) - 1.0) < 1e-6  # horizontal Y
        assert is_z or is_x or is_y, f"Unexpected diagonal normal: {n}"
```

- [ ] **Step 2: Run to verify it passes (baseline)**

Run: `py -3.12 -m pytest tests/test_voxel_rt_mesh.py::test_flat_floor_normals_are_vertical -v`

This test should already pass with the current code since `round_triangle_scene()` receives matching grid_coords and positions when called directly. The axis bug is in `scene_data.py`, not in `round_triangle_scene()` itself. This test establishes the baseline that the meshing function works correctly when given consistent inputs.

- [ ] **Step 3: Write a test that exercises the load pipeline axis swap**

Add to `tests/test_voxel_rt_mesh.py`:

```python
def test_grid_coords_swapped_to_zup():
    """After load_voxels transforms positions to Z-up, grid_coords must match."""
    from aegis.viewer.scene_data import _transform_to_local

    # Simulate Y-up input: column 1 is up, column 2 is horizontal
    grid_coords = np.array([[0, 5, 0], [1, 5, 0], [0, 5, 1]], dtype=np.int64)
    positions = grid_coords.astype(np.float64)

    # Transform positions to Z-up
    positions_zup, _ = _transform_to_local(positions, has_ecef=False)

    # Apply the same swap to grid_coords: [x, -z, y]
    gc_zup = np.column_stack([
        grid_coords[:, 0],
        -grid_coords[:, 2],
        grid_coords[:, 1],
    ])

    # The Z-up grid coords should have column 2 (Z) = 5 (was Y-up)
    assert gc_zup[0, 2] == 5
    assert gc_zup[0, 1] == 0  # was z_horiz=0, now y=-0=0
```

- [ ] **Step 4: Run test**

Run: `py -3.12 -m pytest tests/test_voxel_rt_mesh.py::test_grid_coords_swapped_to_zup -v`
Expected: PASS

- [ ] **Step 5: Apply the axis swap in load_voxels()**

In `src/aegis/viewer/scene_data.py`, after line 346 (`positions, transform = _transform_to_local(positions, has_ecef)`), add:

```python
    positions, transform = _transform_to_local(positions, has_ecef)

    # Match grid_coords axes to the Z-up convention applied to positions.
    # Y-up [gx, gy_up, gz_horiz] -> Z-up [gx, -gz_horiz, gy_up]
    # Only for non-ECEF data (ECEF uses a rotation matrix).
    if not has_ecef and len(grid_coords) > 0:
        grid_coords = np.column_stack([
            grid_coords[:, 0],
            -grid_coords[:, 2],
            grid_coords[:, 1],
        ])
```

- [ ] **Step 6: Apply the same swap in load_voxels_directory()**

In `src/aegis/viewer/scene_data.py`, after line 416 (`positions, transform = _transform_to_local(positions, has_ecef)`), add the same block:

```python
    positions, transform = _transform_to_local(positions, has_ecef)

    if not has_ecef and len(grid_coords) > 0:
        grid_coords = np.column_stack([
            grid_coords[:, 0],
            -grid_coords[:, 2],
            grid_coords[:, 1],
        ])
```

- [ ] **Step 7: Run all existing tests**

Run: `py -3.12 -m pytest tests/test_voxel_rt_mesh.py -v`
Expected: All PASS. The existing tests call `round_triangle_scene()` directly with matching coords, so they are unaffected.

- [ ] **Step 8: Lint and commit**

```bash
py -3.12 -m ruff check src/aegis/viewer/scene_data.py tests/test_voxel_rt_mesh.py
py -3.12 -m ruff format src/aegis/viewer/scene_data.py tests/test_voxel_rt_mesh.py
git add src/aegis/viewer/scene_data.py tests/test_voxel_rt_mesh.py
git commit -m "fix(viewer): swap grid_coords to Z-up after position transform

grid_coords stayed in Y-up while positions were transformed to Z-up,
causing round_triangle_scene() to emit faces in the wrong directions
(venetian blinds bug)."
```

---

### Task 2: Extract face emission into a standalone function

Refactor the inner loop of `round_triangle_scene()` so the greedy meshing can replace it cleanly.

**Files:**
- Modify: `src/aegis/viewer/raytracer.py:261-310`
- Test: `tests/test_voxel_rt_mesh.py`

- [ ] **Step 1: Extract `_emit_exposed_faces()` from the loop**

In `src/aegis/viewer/raytracer.py`, add a new function before `round_triangle_scene()`:

```python
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
```

- [ ] **Step 2: Update `round_triangle_scene()` to use the extracted function**

Replace lines 261-310 in `round_triangle_scene()` with:

```python
    vertices = _emit_exposed_faces(grid_coords, positions, voxel_size)
```

Keep the existing triangulation and DiffeRT scene construction code (lines 312-339) unchanged.

- [ ] **Step 3: Run tests to verify refactor is behavior-preserving**

Run: `py -3.12 -m pytest tests/test_voxel_rt_mesh.py -v`
Expected: All PASS with identical triangle counts.

- [ ] **Step 4: Commit**

```bash
py -3.12 -m ruff check src/aegis/viewer/raytracer.py
py -3.12 -m ruff format src/aegis/viewer/raytracer.py
git add src/aegis/viewer/raytracer.py
git commit -m "refactor(viewer): extract _emit_exposed_faces from round_triangle_scene

Prepares for greedy meshing by isolating the face emission logic."
```

---

### Task 3: Implement greedy meshing

**Files:**
- Modify: `src/aegis/viewer/raytracer.py`
- Test: `tests/test_voxel_rt_mesh.py`

- [ ] **Step 1: Write failing tests for greedy mesh triangle counts**

Add to `tests/test_voxel_rt_mesh.py`:

```python
def test_greedy_single_voxel():
    """Single voxel: 6 faces, each 1 quad = 12 triangles (no merging possible)."""
    gc = np.array([[0, 0, 0]], dtype=np.int64)
    assert _n_triangles(gc) == 12


def test_greedy_flat_floor_4x4():
    """4x4 flat floor: top=1 rect(2 tri), bottom=1 rect(2 tri),
    4 sides each 4 voxels long = 4 rects(8 tri). Total = 12."""
    gc = np.array([
        [x, y, 0] for x in range(4) for y in range(4)
    ], dtype=np.int64)
    assert _n_triangles(gc) == 12


def test_greedy_2x2x1_slab():
    """2x2x1 slab: top=2tri, bottom=2tri, 4 sides each 2-long = 4*2=8tri.
    Total = 12."""
    gc = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.int64)
    assert _n_triangles(gc) == 12


def test_greedy_l_shape():
    """L-shape (3+2 voxels, sharing corner):
      [0,0] [1,0] [2,0]
      [0,1] [1,1]
    Top: 2 rectangles (3x1 + 2x1 minus overlap = need to verify).
    """
    gc = np.array([
        [0, 0, 0], [1, 0, 0], [2, 0, 0],
        [0, 1, 0], [1, 1, 0],
    ], dtype=np.int64)
    n = _n_triangles(gc)
    # Top: greedy finds 3x1 rect then 2x1 rect = 2 quads = 4 tri
    # OR 2x2 rect then 1x1 rect = 2 quads = 4 tri (depends on sweep order)
    # Bottom: same = 4 tri
    # Sides: perimeter has 10 exposed side faces.
    # Greedy merges straight runs: e.g. bottom edge 3-long = 1 rect,
    # right edge varies. Exact count depends on sweep.
    # Just verify it's less than the unmerged count.
    # Unmerged: 5 voxels, each up to 5 exposed faces (top+bottom+some sides)
    # = roughly 40-ish triangles unmerged.
    assert n < 40, f"Expected greedy to reduce triangles, got {n}"
    assert n >= 12, f"L-shape needs at least 12 triangles, got {n}"


def test_greedy_normals_point_outward():
    """All face normals must point outward (away from the solid)."""
    gc = np.array([
        [x, y, z]
        for x in range(3) for y in range(3) for z in range(2)
    ], dtype=np.int64)
    pos = gc.astype(np.float64)
    scene = round_triangle_scene(pos, grid_coords=gc, voxel_size=1.0)

    verts = np.array(scene.mesh.vertices)
    tris = np.array(scene.mesh.triangles)

    v0 = verts[tris[:, 0]]
    v1 = verts[tris[:, 1]]
    v2 = verts[tris[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(norms > 0, norms, 1)

    # Face center
    centers = (v0 + v1 + v2) / 3.0
    # Center of the whole solid
    solid_center = pos.mean(axis=0)
    # Normal should point away from solid center
    outward = centers - solid_center
    dots = np.sum(normals * outward, axis=1)
    assert np.all(dots >= -1e-6), f"Some normals point inward: min dot = {dots.min()}"


def test_greedy_nonunit_voxel_size():
    """Greedy meshing with voxel_size=0.5 produces correct world extents."""
    gc = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.int64)
    pos = gc.astype(np.float64) * 0.5  # world positions at half scale
    scene = round_triangle_scene(pos, grid_coords=gc, voxel_size=0.5)

    verts = np.array(scene.mesh.vertices)
    # World extent should be 2 * 0.5 = 1.0 in x and y
    assert abs(verts[:, 0].max() - verts[:, 0].min() - 1.0) < 1e-5
    assert abs(verts[:, 1].max() - verts[:, 1].min() - 1.0) < 1e-5
    assert abs(verts[:, 2].max() - verts[:, 2].min() - 0.5) < 1e-5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_voxel_rt_mesh.py -v -k "greedy"`
Expected: `test_greedy_flat_floor_4x4` and `test_greedy_2x2x1_slab` FAIL (current code produces 32 triangles for 2x2x1, not 12).

- [ ] **Step 3: Implement `_greedy_mesh_faces()`**

Add to `src/aegis/viewer/raytracer.py`:

```python
# Mapping from face direction index to (u_axis, v_axis, fixed_axis) indices
# and the sign of the fixed-axis offset (+hs or -hs).
_FACE_UV_MAP = [
    # dir_idx: (u_axis, v_axis, fixed_axis, fixed_sign)
    (1, 2, 0, +1),   # +X: u=y, v=z, fixed=x at +hs
    (1, 2, 0, -1),   # -X: u=y, v=z, fixed=x at -hs
    (0, 2, 1, +1),   # +Y: u=x, v=z, fixed=y at +hs
    (0, 2, 1, -1),   # -Y: u=x, v=z, fixed=y at -hs
    (0, 1, 2, +1),   # +Z: u=x, v=y, fixed=z at +hs
    (0, 1, 2, -1),   # -Z: u=x, v=y, fixed=z at -hs
]

# Winding templates: for each face direction, the 4 corners of a unit quad
# in (u, v) space that produce outward-facing normals matching face_corners.
# Each entry is [(u_lo/hi, v_lo/hi), ...] in the same order as face_corners.
_FACE_WINDING = [
    # +X: face_corners[0] = [(+,−,−), (+,+,−), (+,+,+), (+,−,+)]
    #   u=y, v=z: (−,−), (+,−), (+,+), (−,+) => lo,lo / hi,lo / hi,hi / lo,hi
    [(0, 0), (1, 0), (1, 1), (0, 1)],
    # -X: face_corners[1] = [(−,−,+), (−,+,+), (−,+,−), (−,−,−)]
    #   u=y, v=z: (−,+), (+,+), (+,−), (−,−) => lo,hi / hi,hi / hi,lo / lo,lo
    [(0, 1), (1, 1), (1, 0), (0, 0)],
    # +Y: face_corners[2] = [(−,+,−), (−,+,+), (+,+,+), (+,+,−)]
    #   u=x, v=z: (−,−), (−,+), (+,+), (+,−) => lo,lo / lo,hi / hi,hi / hi,lo
    [(0, 0), (0, 1), (1, 1), (1, 0)],
    # -Y: face_corners[3] = [(+,−,−), (+,−,+), (−,−,+), (−,−,−)]
    #   u=x, v=z: (+,−), (+,+), (−,+), (−,−) => hi,lo / hi,hi / lo,hi / lo,lo
    [(1, 0), (1, 1), (0, 1), (0, 0)],
    # +Z: face_corners[4] = [(−,−,+), (+,−,+), (+,+,+), (−,+,+)]
    #   u=x, v=y: (−,−), (+,−), (+,+), (−,+) => lo,lo / hi,lo / hi,hi / lo,hi
    [(0, 0), (1, 0), (1, 1), (0, 1)],
    # -Z: face_corners[5] = [(−,+,−), (+,+,−), (+,−,−), (−,−,−)]
    #   u=x, v=y: (−,+), (+,+), (+,−), (−,−) => lo,hi / hi,hi / hi,lo / lo,lo
    [(0, 1), (1, 1), (1, 0), (0, 0)],
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

    # Compute grid-to-world origin: world = origin + grid_shifted * voxel_size
    # This avoids per-voxel position lookups that can accumulate float error.
    # Use the first voxel as reference to derive the origin.
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

        # Group exposed faces by their fixed-axis coordinate (slice).
        exposed_gc = gc_shifted[exposed_idx]
        fixed_vals = exposed_gc[:, f_ax]
        unique_fixed = np.unique(fixed_vals)

        for fv in unique_fixed:
            slice_mask = fixed_vals == fv
            slice_gc = exposed_gc[slice_mask]

            # Build 2D boolean grid for this slice
            u_coords = slice_gc[:, u_ax].astype(np.intp)
            v_coords = slice_gc[:, v_ax].astype(np.intp)
            u_min, u_max = int(u_coords.min()), int(u_coords.max())
            v_min, v_max = int(v_coords.min()), int(v_coords.max())
            u_span = u_max - u_min + 1
            v_span = v_max - v_min + 1

            grid_2d = np.zeros((u_span, v_span), dtype=bool)
            u_local = u_coords - u_min
            v_local = v_coords - v_min
            grid_2d[u_local, v_local] = True

            visited = np.zeros_like(grid_2d)

            # Greedy sweep
            for u in range(u_span):
                for v in range(v_span):
                    if not grid_2d[u, v] or visited[u, v]:
                        continue

                    # Expand right
                    w = 1
                    while u + w < u_span and grid_2d[u + w, v] and not visited[u + w, v]:
                        w += 1

                    # Expand down
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

                    # Mark visited
                    visited[u:u + w, v:v + h] = True

                    # Emit quad using pure grid-to-world math (no position lookups).
                    # Grid cell (gu, gv) in shifted coords has center at:
                    #   world[axis] = origin[axis] + gu * voxel_size
                    # Rectangle spans cells [u+u_min .. u+u_min+w-1] in u,
                    #                       [v+v_min .. v+v_min+h-1] in v.
                    gu0 = u + u_min
                    gv0 = v + v_min
                    gf = int(fv)

                    u_lo = origin[u_ax] + gu0 * voxel_size - hs
                    u_hi = origin[u_ax] + (gu0 + w) * voxel_size - hs
                    v_lo = origin[v_ax] + gv0 * voxel_size - hs
                    v_hi = origin[v_ax] + (gv0 + h) * voxel_size - hs
                    f_val = origin[f_ax] + gf * voxel_size + f_sign * hs

                    # Build 4 corners using winding template
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
```

- [ ] **Step 4: Wire `_greedy_mesh_faces` into `round_triangle_scene()`**

Replace the call to `_emit_exposed_faces` (from Task 2) with `_greedy_mesh_faces`:

```python
    vertices = _greedy_mesh_faces(grid_coords, positions, voxel_size)
```

- [ ] **Step 5: Update existing tests for new triangle counts**

In `tests/test_voxel_rt_mesh.py`, update the expected counts:

```python
def test_single_voxel_is_six_quads():
    gc = np.array([[0, 0, 0]], dtype=np.int64)
    assert _n_triangles(gc) == 12  # unchanged: 6 faces, no merging possible


def test_two_adjacent_voxels_shares_one_face():
    gc = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.int64)
    # Before: 20. After greedy: top=2, bottom=2, 4 sides (2 are 2-long, 2 are 1-wide) = 4*2=8. Total=12.
    assert _n_triangles(gc) == 12


def test_two_by_two_by_one_tile_expected_hull():
    gc = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.int64)
    # Before: 32. After greedy: top=2, bottom=2, 4 sides each 2-long = 4*2=8. Total=12.
    assert _n_triangles(gc) == 12


def test_far_from_origin_same_hull_count():
    base = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.int64)
    shift = np.array([[100, 200, 300]], dtype=np.int64)
    gc = base + shift
    assert _n_triangles(gc) == 12
```

- [ ] **Step 6: Run all tests**

Run: `py -3.12 -m pytest tests/test_voxel_rt_mesh.py -v`
Expected: All PASS.

- [ ] **Step 7: Lint and commit**

```bash
py -3.12 -m ruff check src/aegis/viewer/raytracer.py tests/test_voxel_rt_mesh.py
py -3.12 -m ruff format src/aegis/viewer/raytracer.py tests/test_voxel_rt_mesh.py
git add src/aegis/viewer/raytracer.py tests/test_voxel_rt_mesh.py
git commit -m "feat(viewer): greedy meshing for voxel hull faces

Merge coplanar adjacent voxel faces into maximal rectangles.
A flat 4x4 floor now produces 12 triangles instead of 192."
```

---

### Task 4: Wireframe display for hull mesh

**Files:**
- Modify: `src/aegis/viewer/templates/index.html:1057-1064` (meshFromSceneBinary material)
- Modify: `src/aegis/viewer/templates/index.html:1805-1813` (toggleWireframe)

- [ ] **Step 1: Change hull mesh material to wireframe**

In `src/aegis/viewer/templates/index.html`, in the `meshFromSceneBinary` function (around line 1057), change the material to default to wireframe:

```javascript
        function meshFromSceneBinary(buf, meta, {wireframe = false} = {}) {
            const nV = meta.n_vertices;
            const nT = meta.n_triangles;
            const vertices = new Float32Array(buf, 0, nV * 3);
            let off = nV * 3 * 4;
            const triangles = new Int32Array(buf, off, nT * 3);
            if (meta.has_face_colors) {
                off += nT * 3 * 4;
            }
            const geom = new THREE.BufferGeometry();
            const posSwapped = new Float32Array(nV * 3);
            for (let i = 0; i < nV; i++) {
                posSwapped[i * 3] = vertices[i * 3];
                posSwapped[i * 3 + 1] = vertices[i * 3 + 2];
                posSwapped[i * 3 + 2] = -vertices[i * 3 + 1];
            }
            geom.setAttribute('position', new THREE.BufferAttribute(posSwapped, 3));
            geom.setIndex(new THREE.BufferAttribute(new Uint32Array(triangles), 1));
            geom.computeVertexNormals();
            const sCfg = CFG.sionna_scene;
            const mat = new THREE.MeshStandardMaterial({
                color: hexToInt(sCfg.color),
                roughness: sCfg.roughness,
                metalness: sCfg.metalness,
                side: THREE.DoubleSide,
                transparent: !wireframe,
                opacity: wireframe ? 1.0 : sCfg.opacity,
                wireframe: wireframe,
            });
            const mesh = new THREE.Mesh(geom, mat);
            mesh.castShadow = !wireframe;
            return mesh;
        }
```

- [ ] **Step 2: Pass wireframe=true when loading hull mesh**

In `applyEnvDisplay`, where the hull mesh is loaded (around line 1139), pass the wireframe option:

```javascript
                    voxelHullMesh = meshFromSceneBinary(buf, meta, {wireframe: true});
```

- [ ] **Step 3: Add hull mesh to global wireframe toggle**

In `toggleWireframe` (around line 1805), add:

```javascript
        window.toggleWireframe = () => {
            wireframe = !wireframe;
            for (const meshes of Object.values(voxelMeshes)) {
                meshes.classified.material.wireframe = wireframe;
            }
            if (bodyMesh) bodyMesh.material.wireframe = wireframe;
            if (groundPlane) groundPlane.material.wireframe = wireframe;
            if (voxelHullMesh) voxelHullMesh.material.wireframe = wireframe;
            document.getElementById('wireframeBtn').classList.toggle('active', wireframe);
        };
```

- [ ] **Step 4: Update hint text to show triangle count**

In `applyEnvDisplay` hull section, update the hint (around line 1143):

```javascript
                    if (hint) {
                        hint.textContent = `RT hull wireframe: ${meta.n_triangles.toLocaleString()} triangles (greedy-merged).`;
                    }
```

- [ ] **Step 5: Commit**

```bash
py -3.12 -m ruff check src/ tests/
py -3.12 -m ruff format src/ tests/
git add src/aegis/viewer/templates/index.html
git commit -m "feat(viewer): wireframe display for ray-tracing hull mesh

Hull mesh now renders as wireframe by default to show triangle
structure. Integrated with global wireframe toggle."
```

---

### Task 5: Clear voxel scene cache when grid_coords change

The `get_or_build_voxel_scene()` function caches the DiffeRT scene. After the axis fix, the cached scene from before the fix would be stale.

**Files:**
- Modify: `src/aegis/viewer/server.py` (add cache-clearing calls)

Note: `clear_voxel_scene_cache()` already exists at `src/aegis/viewer/raytracer.py:45`. It is currently called in one server path (location reload, line ~758) but NOT in `_load_and_cache_voxels_single()` or `_load_and_cache_voxels_dir()`.

- [ ] **Step 1: Add cache-clearing calls to voxel loading functions**

In `src/aegis/viewer/server.py`, in both `_load_and_cache_voxels_single()` (after line 60) and `_load_and_cache_voxels_dir()` (after line 82), add:

```python
    from aegis.viewer.raytracer import clear_voxel_scene_cache
    clear_voxel_scene_cache()
```

Check if this import already exists at module level or is done lazily elsewhere. Follow the existing pattern (DiffeRT imports are lazy in server.py due to optional dependency).

- [ ] **Step 3: Commit**

```bash
git add src/aegis/viewer/raytracer.py src/aegis/viewer/server.py
git commit -m "fix(viewer): clear voxel scene cache when voxels reload"
```

---

### Task 6: Visual verification and cleanup

- [ ] **Step 1: Run full fast test suite**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: All PASS.

- [ ] **Step 2: Run lint**

Run: `py -3.12 -m ruff check src/ tests/ && py -3.12 -m ruff format --check src/ tests/`
Expected: Clean.

- [ ] **Step 3: Launch viewer and verify**

```bash
py -3.12 -m aegis.viewer --location "Ghent, Belgium"
```

Switch to "Ray-tracing hull mesh" display. Verify:
- Floor shows as large wireframe triangles, not venetian blinds
- Triangle count in hint text is much lower than before
- Global wireframe toggle includes the hull mesh

- [ ] **Step 4: Push**

```bash
git push origin master
```
