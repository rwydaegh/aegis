# Material-aware greedy meshing implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the greedy meshing algorithm preserve per-voxel material boundaries, so the RT hull mesh has correct per-material reflection properties and per-material coloring in the viewer.

**Architecture:** The greedy merge function `_greedy_mesh_faces()` gains a `material_ids` parameter and only merges adjacent faces with matching material. The Flask endpoints pipe `voxel_materials` from cache through to the meshing. The frontend reads per-face colors from the binary payload.

**Tech Stack:** Python/NumPy (backend), JAX/DiffeRT (scene construction), Three.js (frontend), pytest (tests)

**Spec:** `docs/superpowers/specs/2026-03-20-material-aware-greedy-meshing-design.md`

---

### Task 1: Material-aware `_greedy_mesh_faces()` -- tests

**Files:**
- Modify: `tests/test_voxel_rt_mesh.py`

- [ ] **Step 1: Write failing test for material boundary preservation**

Add to `tests/test_voxel_rt_mesh.py`:

```python
def test_material_boundary_prevents_merge():
    """Adjacent voxels with different materials must not merge across boundary."""
    # 4x1 strip: left two = material 0, right two = material 1
    gc = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]], dtype=np.int64)
    pos = gc.astype(np.float64)
    materials = ["concrete", "concrete", "brick", "brick"]

    scene = round_triangle_scene(pos, grid_coords=gc, voxel_size=1.0, materials=materials)
    mesh = scene.mesh
    face_mats = np.array(mesh.face_materials)

    # Must have both material IDs present
    unique_mats = set(face_mats.tolist())
    assert len(unique_mats) == 2, f"Expected 2 materials, got {unique_mats}"

    # Material names must include both
    assert "brick" in mesh.material_names
    assert "concrete" in mesh.material_names
```

- [ ] **Step 2: Write failing test for single-material backward compatibility**

```python
def test_no_materials_defaults_to_concrete():
    """When materials=None, all faces get material 0 ('concrete')."""
    gc = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.int64)
    pos = gc.astype(np.float64)
    scene = round_triangle_scene(pos, grid_coords=gc, voxel_size=1.0)
    mesh = scene.mesh
    face_mats = np.array(mesh.face_materials)
    assert set(face_mats.tolist()) == {0}
    assert mesh.material_names == ("concrete",)
```

- [ ] **Step 3: Write failing test for face_colors population**

```python
def test_face_colors_match_material():
    """face_colors should be set based on material_colors config."""
    gc = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.int64)
    pos = gc.astype(np.float64)
    materials = ["concrete", "brick"]
    material_colors = {"concrete": [180, 180, 180], "brick": [200, 80, 50]}

    scene = round_triangle_scene(
        pos, grid_coords=gc, voxel_size=1.0,
        materials=materials, material_colors=material_colors,
    )
    colors = np.array(scene.mesh.face_colors)
    # Colors should be normalized to [0, 1]
    assert colors.max() <= 1.0
    assert colors.min() >= 0.0
    # Not all zeros (the current broken behavior)
    assert colors.sum() > 0
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_voxel_rt_mesh.py -v -x`

Expected: The new tests fail (material_boundary test fails because all face_materials are 0, face_colors test fails because colors are all zeros).

- [ ] **Step 5: Commit test scaffolding**

```bash
git add tests/test_voxel_rt_mesh.py
git commit -m "Add failing tests for material-aware greedy meshing"
git push origin master
```

---

### Task 2: Material-aware `_greedy_mesh_faces()` -- implementation

**Files:**
- Modify: `src/aegis/viewer/raytracer.py:305-414` (`_greedy_mesh_faces`)
- Modify: `src/aegis/viewer/raytracer.py:417-488` (`round_triangle_scene`)

- [ ] **Step 1: Update `_greedy_mesh_faces` signature and add material grid**

In `src/aegis/viewer/raytracer.py`, change the function signature and internal logic:

```python
def _greedy_mesh_faces(
    grid_coords: np.ndarray,
    positions: np.ndarray,
    voxel_size: float,
    material_ids: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Emit greedy-merged quad vertices for all exposed voxel faces.

    Returns (vertices, quad_material_ids) where vertices is (M, 3) float32
    (every 4 consecutive vertices form one quad) and quad_material_ids is (M//4,)
    int32 with the material index for each quad.
    """
```

Key changes inside the function:

1. Build a 3D material grid alongside the occupancy grid:
```python
# After building occ (bool occupancy grid):
mat_grid_3d = np.full(pad_shape, -1, dtype=np.int32)
mat_grid_3d[ix, iy, iz] = material_ids
```

2. In the per-direction loop, get per-face material IDs:
```python
exposed_mat = mat_grid_3d[ix[exposed_idx], iy[exposed_idx], iz[exposed_idx]]
```

3. In the per-slice 2D grid, store material IDs instead of booleans:
```python
# Replace:
#   grid_2d = np.zeros((u_span, v_span), dtype=bool)
#   grid_2d[u_coords - u_min, v_coords - v_min] = True
# With:
mat_grid = np.full((u_span, v_span), -1, dtype=np.int32)
slice_mat = exposed_mat[slice_mask]
mat_grid[u_coords - u_min, v_coords - v_min] = slice_mat
```

4. Change merge conditions:
```python
# Replace:
#   if not grid_2d[u, v] or visited[u, v]:
# With:
cur_mat = int(mat_grid[u, v])
if cur_mat < 0 or visited[u, v]:
    continue

# Replace width extension:
#   while u + w < u_span and grid_2d[u + w, v] and not visited[u + w, v]:
# With:
while u + w < u_span and mat_grid[u + w, v] == cur_mat and not visited[u + w, v]:

# Replace height extension inner check:
#   if not grid_2d[u + du, v + h] or visited[u + du, v + h]:
# With:
if mat_grid[u + du, v + h] != cur_mat or visited[u + du, v + h]:
```

5. Track material per quad:
```python
all_face_mats: list[int] = []
# ... inside the loop, after appending quad verts:
all_face_mats.append(cur_mat)
```

6. Return both arrays:
```python
return (
    np.concatenate(all_face_verts, axis=0).astype(np.float32),
    np.array(all_face_mats, dtype=np.int32),
)
```

- [ ] **Step 2: Update `round_triangle_scene` to wire up materials**

In the same file, update `round_triangle_scene`:

```python
# After grid_coords handling, before calling _greedy_mesh_faces:
if materials is not None and len(materials) > 0:
    unique_materials = sorted(set(materials))
    mat_name_to_id = {name: i for i, name in enumerate(unique_materials)}
    mat_ids = np.array([mat_name_to_id[m] for m in materials], dtype=np.int32)
else:
    unique_materials = ["concrete"]
    mat_ids = np.zeros(len(positions), dtype=np.int32)

vertices, quad_mat_ids = _greedy_mesh_faces(grid_coords, positions, voxel_size, mat_ids)
```

Build face_materials (2 triangles per quad, same material):
```python
face_materials = np.repeat(quad_mat_ids, 2)
```

Build face_colors from material_colors config:
```python
default_colors = {"concrete": [180, 180, 180], "asphalt": [80, 80, 80],
                  "vegetation": [40, 160, 40], "brick": [200, 80, 50]}
if material_colors is None:
    material_colors = default_colors
color_array = np.zeros((len(face_materials), 3), dtype=np.float32)
for i, mat_name in enumerate(unique_materials):
    rgb = material_colors.get(mat_name, [200, 200, 200])
    mask = face_materials == i
    color_array[mask] = [c / 255.0 for c in rgb]
```

Update the TriangleMesh construction:
```python
mesh = TriangleMesh(
    vertices=jnp.array(vertices),
    triangles=jnp.array(triangles),
    face_colors=jnp.array(color_array),
    face_materials=jnp.array(face_materials),
    material_names=tuple(unique_materials),
    object_bounds=jnp.array([[0, len(triangles)]], dtype=jnp.int32),
)
```

- [ ] **Step 3: Run tests**

Run: `py -3.12 -m pytest tests/test_voxel_rt_mesh.py -v`

Expected: All tests pass, including the three new material tests and all existing regression tests.

- [ ] **Step 4: Run linter**

Run: `py -3.12 -m ruff check src/aegis/viewer/raytracer.py tests/test_voxel_rt_mesh.py`
Run: `py -3.12 -m ruff format src/aegis/viewer/raytracer.py tests/test_voxel_rt_mesh.py`

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/raytracer.py tests/test_voxel_rt_mesh.py
git commit -m "Make greedy meshing material-aware

Only merge adjacent voxel faces that share the same material.
Populate face_materials and face_colors on the DiffeRT TriangleMesh."
git push origin master
```

---

### Task 3: Pass materials through Flask endpoints

**Files:**
- Modify: `src/aegis/viewer/routes/compute.py:164-206` (`api_voxels_hull_mesh`)
- Modify: `src/aegis/viewer/routes/compute.py:288-360` (`api_compute_voxel_rt`)

- [ ] **Step 1: Update `api_voxels_hull_mesh` to pass materials**

In `src/aegis/viewer/routes/compute.py`, inside `api_voxels_hull_mesh()`, after reading from cache, also read `voxel_materials`:

```python
with cache_lock:
    voxel_positions = cache.get("voxel_positions")
    voxel_sizes = cache.get("voxel_sizes")
    voxel_materials = cache.get("voxel_materials")
    cfg = cache.get("config", {})
```

After computing `ext_mask`, filter materials:
```python
ext_materials = None
if voxel_materials is not None:
    ext_materials = [voxel_materials[i] for i in np.where(ext_mask)[0]]

material_colors = cfg.get("voxels", {}).get("material_colors")
```

Pass to `get_or_build_voxel_scene`:
```python
scene = get_or_build_voxel_scene(
    ext_pos, ext_grid, voxel_size=vs,
    materials=ext_materials, material_colors=material_colors,
)
```

Also populate face_colors in `scene_data` (after Task 2, `face_colors` is always populated on the mesh, never None):
```python
scene_data = {
    "vertices": vertices,
    "triangles": triangles,
    "face_colors": np.array(mesh.face_colors),
    "n_vertices": int(len(vertices)),
    "n_triangles": int(len(triangles)),
    "material_names": mnames,
}
```

- [ ] **Step 2: Update `api_compute_voxel_rt` to pass materials**

Same pattern. After reading `voxel_positions` and `voxel_sizes` from cache, also read `voxel_materials`. After `ext_mask`, filter. Pass to `get_or_build_voxel_scene`.

```python
with cache_lock:
    body = cache.get("body")
    voxel_positions = cache.get("voxel_positions")
    voxel_sizes = cache.get("voxel_sizes")
    voxel_materials = cache.get("voxel_materials")
    cfg = cache["config"]
```

After `ext_mask`:
```python
ext_materials = None
if voxel_materials is not None:
    ext_materials = [voxel_materials[i] for i in np.where(ext_mask)[0]]

material_colors = cfg.get("voxels", {}).get("material_colors")

scene = get_or_build_voxel_scene(
    ext_pos, ext_grid, voxel_size=vs,
    materials=ext_materials, material_colors=material_colors,
)
```

- [ ] **Step 3: Run full test suite**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`

Expected: All fast tests pass.

- [ ] **Step 4: Lint and format**

Run: `py -3.12 -m ruff check src/aegis/viewer/routes/compute.py && py -3.12 -m ruff format src/aegis/viewer/routes/compute.py`

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/routes/compute.py
git commit -m "Pass voxel materials through hull-mesh and voxel-rt endpoints"
git push origin master
```

---

### Task 4: Frontend per-material colors on hull wireframe

**Files:**
- Modify: `src/aegis/viewer/templates/index.html:1148-1179` (`meshFromSceneBinary`)

- [ ] **Step 1: Update `meshFromSceneBinary` to read face_colors and apply as vertex colors**

In `src/aegis/viewer/templates/index.html`, update the `meshFromSceneBinary` function.

Note: The current code has a bug where `off` only advances past triangles inside the `if (has_face_colors)` block. The replacement fixes this by always advancing `off` past triangles before reading face_colors.

Note: The function gains an `opts` parameter. The existing caller at line ~1251 already passes `{wireframe: true}` as a third arg (currently ignored). This change makes it actually used.

```javascript
function meshFromSceneBinary(buf, meta, opts) {
    const wireframe = opts && opts.wireframe;
    const nV = meta.n_vertices;
    const nT = meta.n_triangles;
    const vertices = new Float32Array(buf, 0, nV * 3);
    let off = nV * 3 * 4;
    const triangles = new Int32Array(buf, off, nT * 3);
    off += nT * 3 * 4;

    // Read per-face colors if available
    let faceColors = null;
    if (meta.has_face_colors) {
        faceColors = new Float32Array(buf, off, nT * 3);
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

    // Apply per-face colors as vertex colors (3 vertices per triangle)
    let useVertexColors = false;
    if (faceColors && faceColors.length > 0) {
        // Convert per-face colors to per-vertex colors via indexed geometry
        // We need to un-index the geometry to have per-face vertex colors
        const nonIndexed = geom.toNonIndexed();
        const vertCount = nonIndexed.getAttribute('position').count;
        const colorAttr = new Float32Array(vertCount * 3);
        for (let t = 0; t < nT; t++) {
            const r = faceColors[t * 3];
            const g = faceColors[t * 3 + 1];
            const b = faceColors[t * 3 + 2];
            colorAttr[t * 9]     = r;
            colorAttr[t * 9 + 1] = g;
            colorAttr[t * 9 + 2] = b;
            colorAttr[t * 9 + 3] = r;
            colorAttr[t * 9 + 4] = g;
            colorAttr[t * 9 + 5] = b;
            colorAttr[t * 9 + 6] = r;
            colorAttr[t * 9 + 7] = g;
            colorAttr[t * 9 + 8] = b;
        }
        nonIndexed.setAttribute('color', new THREE.BufferAttribute(colorAttr, 3));
        useVertexColors = true;

        const sCfg = CFG.sionna_scene;
        const mat = new THREE.MeshStandardMaterial({
            vertexColors: true,
            roughness: sCfg.roughness,
            metalness: sCfg.metalness,
            side: THREE.DoubleSide,
            transparent: !wireframe,
            opacity: wireframe ? 1.0 : sCfg.opacity,
            wireframe: wireframe,
        });
        const mesh = new THREE.Mesh(nonIndexed, mat);
        mesh.castShadow = !wireframe;
        return mesh;
    }

    // Fallback: no face colors, use uniform color
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

- [ ] **Step 2: Update the hull mesh hint text to show material count**

In the `applyEnvDisplay` function where `mode === 'hull'`, update the hint:

```javascript
if (hint) {
    const matCount = (meta.material_names || []).length;
    const matText = matCount > 1 ? ` (${matCount} materials)` : '';
    hint.textContent = `RT hull wireframe: ${meta.n_triangles.toLocaleString()} triangles${matText}.`;
}
```

- [ ] **Step 3: Test visually**

Launch the viewer with a voxel scene that has multiple materials:
```bash
py -3.12 -m aegis.viewer --config configs/default.json
```

Open browser to the viewer URL. Switch to "Ray-tracing hull mesh" mode. Verify:
- Hull wireframe shows different colors for different materials
- The material colors match the config `material_colors` settings

- [ ] **Step 4: Lint**

Run: `py -3.12 -m ruff check src/aegis/viewer/templates/ 2>/dev/null; echo "HTML not linted by ruff, manual check only"`

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "Show per-material colors on hull wireframe"
git push origin master
```

---

### Task 5: Final integration test and cleanup

**Files:**
- Modify: `tests/test_voxel_rt_mesh.py` (add round-trip serialization test)

- [ ] **Step 1: Write round-trip serialization test**

```python
def test_hull_binary_round_trip_with_colors():
    """Build hull, serialize to binary, verify face_colors present."""
    from aegis.viewer.raytracer import scene_geometry_to_binary

    gc = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.int64)
    pos = gc.astype(np.float64)
    materials = ["concrete", "brick"]
    material_colors = {"concrete": [180, 180, 180], "brick": [200, 80, 50]}

    scene = round_triangle_scene(
        pos, grid_coords=gc, voxel_size=1.0,
        materials=materials, material_colors=material_colors,
    )
    mesh = scene.mesh
    vertices = np.array(mesh.vertices)
    triangles = np.array(mesh.triangles)
    colors = np.array(mesh.face_colors)

    scene_data = {
        "vertices": vertices,
        "triangles": triangles,
        "face_colors": colors,
        "n_vertices": len(vertices),
        "n_triangles": len(triangles),
        "material_names": list(mesh.material_names),
    }
    data, meta = scene_geometry_to_binary(scene_data)

    assert meta["has_face_colors"] is True
    assert len(meta["material_names"]) == 2

    # Parse binary back
    nv = meta["n_vertices"]
    nt = meta["n_triangles"]
    v_end = nv * 3 * 4
    t_end = v_end + nt * 3 * 4
    c_end = t_end + nt * 3 * 4
    assert len(data) == c_end

    parsed_colors = np.frombuffer(data[t_end:c_end], dtype=np.float32).reshape(nt, 3)
    assert parsed_colors.sum() > 0, "Face colors should not be all zeros"
```

- [ ] **Step 2: Run full test suite**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x -v`

Expected: All tests pass.

- [ ] **Step 3: Lint and format everything**

```bash
py -3.12 -m ruff check src/ tests/
py -3.12 -m ruff format src/ tests/
```

- [ ] **Step 4: Commit and push**

```bash
git add tests/test_voxel_rt_mesh.py
git commit -m "Add round-trip serialization test for material-colored hull mesh"
git push origin master
```
