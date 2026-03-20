# Voxel pipeline simplification implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the voxel loading pipeline to trust VoxelEarth's upstream world positions instead of grid-snapping, eliminating visual gaps/overlaps.

**Architecture:** Remove coordinate round-trips and grid recomputation from the rendering path. Positions stay Y-up (native from VoxelEarth, matching Three.js). Z-up conversion happens on-demand only for ray tracing. Per-voxel sizes replace the single global voxel_size.

**Tech Stack:** Python (NumPy, SciPy KD-tree), JavaScript (Three.js InstancedMesh), Flask

**Spec:** `docs/superpowers/specs/2026-03-20-voxel-pipeline-simplification-design.md`

---

## File structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/aegis/viewer/scene_data.py` | Major rewrite | Voxel loading, parsing metadata, spatial dedup, body placement |
| `src/aegis/viewer/server.py` | Modify | Cache new return types (per-voxel sizes, no transform, no grid_coords) |
| `src/aegis/viewer/routes/data.py` | Modify | Remove tile transform block |
| `src/aegis/viewer/routes/compute.py` | Modify | Call `prepare_for_raytracing()` before exterior filter / scene build |
| `src/aegis/viewer/config.py` | Modify | Remove ECEF config, rename `ground_center_z_offset` |
| `src/aegis/viewer/templates/index.html` | Modify | Remove Z-to-Y swap, support multi-resolution instanced meshes |
| `src/aegis/viewer/raytracer.py` | Minor modify | Accept adapter output |
| `tests/test_voxel_pipeline.py` | Create | Position accuracy, dedup, backward compat tests |
| `tests/test_voxel_rt_mesh.py` | Modify | Update for new API |
| `tests/fixtures/viewer_env_test/voxels_with_metadata.json` | Create | Test fixture with tile metadata |

---

### Task 1: Add test fixture with VoxelEarth metadata format

**Files:**
- Create: `tests/fixtures/viewer_env_test/voxels_with_metadata.json`

- [ ] **Step 1: Create fixture file**

Create a small voxel JSON with the full VoxelEarth metadata format (unit, bbox, worldOffset, gridSize) plus `wx/wy/wz` world positions. Use a simple 2x2x1 floor at known positions.

```json
{
  "file": "test_tile_001",
  "resolution": 200,
  "gridSize": {"x": 2, "y": 1, "z": 2},
  "bbox": {"min": {"x": -0.5, "y": -0.25, "z": -0.5}, "max": {"x": 0.5, "y": 0.25, "z": 0.5}},
  "worldOffset": {"x": 10.0, "y": 0.0, "z": 5.0},
  "unit": {"x": 0.5, "y": 0.5, "z": 0.5},
  "voxelCount": 4,
  "voxels": [
    {"x": 0, "y": 0, "z": 0, "wx": 9.75, "wy": 0.0, "wz": 4.75, "r": 80, "g": 80, "b": 80, "a": 255},
    {"x": 1, "y": 0, "z": 0, "wx": 10.25, "wy": 0.0, "wz": 4.75, "r": 80, "g": 80, "b": 80, "a": 255},
    {"x": 0, "y": 0, "z": 1, "wx": 9.75, "wy": 0.0, "wz": 5.25, "r": 40, "g": 160, "b": 40, "a": 255},
    {"x": 1, "y": 0, "z": 1, "wx": 10.25, "wy": 0.0, "wz": 5.25, "r": 40, "g": 160, "b": 40, "a": 255}
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add tests/fixtures/viewer_env_test/voxels_with_metadata.json
git commit -m "test: add voxel fixture with VoxelEarth metadata format"
```

---

### Task 2: Write failing tests for the new pipeline behavior

**Files:**
- Create: `tests/test_voxel_pipeline.py`

- [ ] **Step 1: Write test for metadata-based voxel size**

```python
"""Tests for simplified voxel loading pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "viewer_env_test"


def test_parse_reads_unit_from_metadata():
    """Voxel size should come from JSON metadata, not be recomputed."""
    from aegis.viewer.scene_data import _parse_voxel_json

    path = FIXTURES / "voxels_with_metadata.json"
    result = _parse_voxel_json(path)
    # New return value includes tile_unit
    assert len(result) == 5  # grid_coords, positions, colors, materials, tile_unit
    _, _, _, _, tile_unit = result
    assert tile_unit == pytest.approx(0.5)
```

- [ ] **Step 2: Write test for position pass-through (no transform)**

```python
def test_positions_are_passthrough_yup():
    """World positions from JSON must not be transformed. They stay Y-up."""
    from aegis.viewer.scene_data import load_voxels

    path = FIXTURES / "voxels_with_metadata.json"
    positions, colors, materials, voxel_sizes = load_voxels(
        path, bbox_radius=100, exterior_only=False
    )
    # wx=9.75 should appear unchanged in output
    assert positions[0, 0] == pytest.approx(9.75)
    # wy=0.0 stays at index 1 (Y-up, no axis swap)
    assert positions[0, 1] == pytest.approx(0.0)
    # wz=4.75 stays at index 2
    assert positions[0, 2] == pytest.approx(4.75)
```

- [ ] **Step 3: Write test for per-voxel sizes returned**

```python
def test_returns_per_voxel_sizes():
    """load_voxels returns a per-voxel size array, not a single float."""
    from aegis.viewer.scene_data import load_voxels

    path = FIXTURES / "voxels_with_metadata.json"
    positions, colors, materials, voxel_sizes = load_voxels(
        path, bbox_radius=100, exterior_only=False
    )
    assert isinstance(voxel_sizes, np.ndarray)
    assert voxel_sizes.dtype == np.float32
    assert len(voxel_sizes) == len(positions)
    assert all(voxel_sizes == pytest.approx(0.5))
```

- [ ] **Step 4: Write test for backward compat (old format, no metadata)**

```python
def test_old_format_without_metadata_still_loads():
    """Bare array voxel JSON (no unit/bbox) should still work with fallback."""
    from aegis.viewer.scene_data import load_voxels

    path = FIXTURES / "voxels.json"
    positions, colors, materials, voxel_sizes = load_voxels(
        path, bbox_radius=100, exterior_only=False
    )
    assert len(positions) == 4
    # Fallback: voxel size computed from adjacent grid cells
    assert all(voxel_sizes > 0)
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_voxel_pipeline.py -v`
Expected: FAIL (return types don't match current API)

- [ ] **Step 6: Commit**

```bash
git add tests/test_voxel_pipeline.py
git commit -m "test: add failing tests for simplified voxel pipeline"
```

---

### Task 3: Rewrite `_parse_voxel_json` to return tile metadata

**Files:**
- Modify: `src/aegis/viewer/scene_data.py:190-218`

- [ ] **Step 1: Update `_parse_voxel_json` to return tile_unit**

The function currently returns `(grid_coords, positions, colors, materials)`. Add a 5th return value `tile_unit: float | None`. Read `unit.x` from the top-level JSON object if present, otherwise return `None`.

```python
def _parse_voxel_json(
    path: str | Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str], float | None]:
    """Parse a voxel JSON file. Returns (grid_coords, positions, colors, materials, tile_unit).

    tile_unit is the voxel size from metadata (unit.x), or None if not present.
    """
    path = Path(path)
    with open(path) as f:
        data = json.load(f)

    # Extract tile metadata if present
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
```

- [ ] **Step 2: Run the metadata test**

Run: `py -3.12 -m pytest tests/test_voxel_pipeline.py::test_parse_reads_unit_from_metadata -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/aegis/viewer/scene_data.py
git commit -m "feat: parse tile_unit from voxel JSON metadata"
```

---

### Task 4: Rewrite `load_voxels` with new return type (no transforms)

**Files:**
- Modify: `src/aegis/viewer/scene_data.py:394-440`

- [ ] **Step 1: Rewrite `load_voxels` to return (positions, colors, materials, voxel_sizes)**

Remove the coordinate transforms (`_transform_to_local`, grid coord axis swap). Positions stay Y-up. Return per-voxel sizes instead of single float. No transform matrix returned.

First, update `_crop_to_bbox` and `_apply_filters` to accept and return `voxel_sizes` as an additional array. Add `voxel_sizes: np.ndarray | None = None` parameter to both functions. Apply the same boolean mask to `voxel_sizes` wherever `positions` is masked. Update `_deduplicate` similarly.

Then rewrite `load_voxels`:

```python
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

    # Determine voxel size: metadata or fallback heuristic
    if tile_unit is not None:
        vs = tile_unit
    else:
        vs = compute_voxel_size(grid_coords, positions)

    voxel_sizes = np.full(len(positions), vs, dtype=np.float32)

    # Crop to bbox around center (Y-up: horizontal = axes 0 and 2)
    center = positions.mean(axis=0)
    grid_coords, positions, colors, materials, voxel_sizes = _crop_to_bbox(
        grid_coords, positions, colors, materials, center, bbox_radius,
        voxel_sizes=voxel_sizes,
    )

    grid_coords, positions, colors, materials, voxel_sizes = _apply_filters(
        grid_coords, positions, colors, materials, exterior_only,
        voxel_sizes=voxel_sizes,
    )

    return positions, colors, materials, voxel_sizes
```

- [ ] **Step 2: Update `_crop_to_bbox` and `_apply_filters` signatures**

Add `voxel_sizes: np.ndarray | None = None` parameter. Apply the same boolean mask. Return the filtered `voxel_sizes` as an additional element in the tuple. Update `_deduplicate` similarly.

- [ ] **Step 3: Run the position and size tests**

Run: `py -3.12 -m pytest tests/test_voxel_pipeline.py::test_positions_are_passthrough_yup tests/test_voxel_pipeline.py::test_returns_per_voxel_sizes tests/test_voxel_pipeline.py::test_old_format_without_metadata_still_loads -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/aegis/viewer/scene_data.py
git commit -m "feat: load_voxels returns Y-up positions and per-voxel sizes"
```

---

### Task 5: Rewrite `load_voxels_directory` for multi-tile

**Files:**
- Modify: `src/aegis/viewer/scene_data.py:443-530`

- [ ] **Step 1: Rewrite multi-tile loading**

Remove the grid-coord recomputation (`np.round(positions / voxel_size)`). Each tile keeps its own `tile_unit`. Build per-voxel `voxel_sizes` array from per-tile units.

```python
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

    # Crop, spatial dedup, optional exterior filter
    center = positions.mean(axis=0)
    # ... crop, dedup, filter (same pattern as load_voxels but with spatial dedup)

    return positions, colors, all_materials, voxel_sizes
```

- [ ] **Step 2: Implement spatial dedup**

Replace grid-based `_deduplicate` with spatial proximity dedup using `scipy.spatial.cKDTree`. For each cluster of voxels within `min(unit_a, unit_b) * 0.5`, keep the highest-resolution one (smallest `voxel_sizes` value).

```python
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
    # Use max voxel size as query radius to find all potential overlaps,
    # then check per-pair distance against min(unit_a, unit_b) * 0.5
    max_size = float(np.max(voxel_sizes))
    candidate_pairs = tree.query_pairs(max_size * 0.5)

    keep = np.ones(n, dtype=bool)
    for i, j in candidate_pairs:
        if not keep[i] or not keep[j]:
            continue
        # Per-pair threshold: half the smaller voxel size
        threshold = min(voxel_sizes[i], voxel_sizes[j]) * 0.5
        dist = np.linalg.norm(positions[i] - positions[j])
        if dist > threshold:
            continue
        # Keep the higher-resolution (smaller size) voxel
        if voxel_sizes[i] <= voxel_sizes[j]:
            keep[j] = False
        else:
            keep[i] = False

    n_removed = n - keep.sum()
    if n_removed > 0:
        print(f"  Spatial dedup: {n:,} -> {keep.sum():,} ({n_removed:,} removed, {n_removed/n*100:.1f}%)")

    return (
        positions[keep],
        colors[keep],
        [m for m, k in zip(materials, keep, strict=True) if k],
        voxel_sizes[keep],
    )
```

- [ ] **Step 3: Run existing fast tests to check nothing broke**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: Some failures in tests that import old signatures (expected, will fix in Task 7)

- [ ] **Step 4: Commit**

```bash
git add src/aegis/viewer/scene_data.py
git commit -m "feat: multi-tile loading with per-voxel sizes and spatial dedup"
```

---

### Task 6: Add `prepare_for_raytracing` adapter

**Files:**
- Modify: `src/aegis/viewer/scene_data.py` (add new function)

- [ ] **Step 1: Write failing test**

```python
# In tests/test_voxel_pipeline.py
def test_prepare_for_raytracing_converts_to_zup():
    """Adapter should swap Y-up to Z-up and produce integer grid coords."""
    from aegis.viewer.scene_data import prepare_for_raytracing

    # Y-up: (x, y_up, z_horiz)
    positions = np.array([[1.0, 2.0, 3.0], [1.5, 2.0, 3.0]], dtype=np.float64)
    voxel_sizes = np.array([0.5, 0.5], dtype=np.float32)

    z_up_pos, grid_coords, dominant_size = prepare_for_raytracing(positions, voxel_sizes)

    # Z-up: (x, -z_horiz, y_up) -> (1.0, -3.0, 2.0)
    assert z_up_pos[0, 0] == pytest.approx(1.0)
    assert z_up_pos[0, 1] == pytest.approx(-3.0)
    assert z_up_pos[0, 2] == pytest.approx(2.0)
    assert dominant_size == pytest.approx(0.5)
    assert grid_coords.dtype == np.int64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_voxel_pipeline.py::test_prepare_for_raytracing_converts_to_zup -v`
Expected: FAIL (function doesn't exist)

- [ ] **Step 3: Implement `prepare_for_raytracing`**

```python
def prepare_for_raytracing(
    positions: np.ndarray,
    voxel_sizes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Convert Y-up positions to Z-up and compute grid coords for greedy meshing.

    Y-up [x, y_up, z_horiz] -> Z-up [x, -z_horiz, y_up].

    Returns (z_up_positions, grid_coords, dominant_voxel_size).
    """
    dominant_size = float(np.median(voxel_sizes))

    z_up = np.column_stack([
        positions[:, 0],
        -positions[:, 2],
        positions[:, 1],
    ])

    # Center before gridding to avoid large-coordinate rounding issues
    center = z_up.mean(axis=0)
    centered = z_up - center
    grid_coords = np.round(centered / dominant_size).astype(np.int64)

    return z_up, grid_coords, dominant_size
```

- [ ] **Step 4: Run test**

Run: `py -3.12 -m pytest tests/test_voxel_pipeline.py::test_prepare_for_raytracing_converts_to_zup -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/scene_data.py tests/test_voxel_pipeline.py
git commit -m "feat: add prepare_for_raytracing Y-up to Z-up adapter"
```

---

### Task 7: Update `find_body_placement` for Y-up

**Files:**
- Modify: `src/aegis/viewer/scene_data.py:599-631`
- Modify: `src/aegis/viewer/config.py` (rename config key)

- [ ] **Step 1: Write failing test**

```python
# In tests/test_voxel_pipeline.py
def test_body_placement_uses_yup_vertical():
    """Body placement should use axis 1 (Y) as vertical in Y-up coordinates."""
    from aegis.viewer.scene_data import find_body_placement

    # 4 asphalt voxels at y=0 (ground level in Y-up), spread on x and z
    positions = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 1.0],
    ])
    materials = ["asphalt"] * 4
    result = find_body_placement(positions, materials)
    # Vertical (Y) should be near 0 + offset, not placed at Z
    assert result[1] == pytest.approx(0.0, abs=1.0)  # Y is vertical
```

- [ ] **Step 2: Update `find_body_placement` to use axis 1 as vertical**

Change all `[:, 2]` to `[:, 1]` and `center[2]` to `center[1]`. The function docstring should say "Y-up coordinates (y = vertical)".

- [ ] **Step 3: Rename config key**

In `config.py`, rename `ground_center_z_offset` to `ground_center_vertical_offset`. Update the reference in `find_body_placement`.

- [ ] **Step 4: Run test**

Run: `py -3.12 -m pytest tests/test_voxel_pipeline.py::test_body_placement_uses_yup_vertical -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/scene_data.py src/aegis/viewer/config.py
git commit -m "fix: body placement uses Y-up vertical axis"
```

---

### Task 8: Update `voxels_to_binary` and frontend for per-voxel sizes

**Files:**
- Modify: `src/aegis/viewer/scene_data.py:569-596`
- Modify: `src/aegis/viewer/templates/index.html:951-1010`

- [ ] **Step 1: Update `voxels_to_binary` to include per-voxel sizes**

New binary layout: positions (n*3 float32) + sizes (n float32) + colors (n*3 uint8) + material_indices (n uint8).

```python
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
```

- [ ] **Step 2: Update frontend `loadVoxels` to parse new binary format**

In `index.html`, update the buffer parsing to read per-voxel sizes. Group voxels by (material, rounded size) for multi-resolution instanced meshes. Remove the Z-to-Y swap (`positions[i*3+2], -positions[i*3+1]` becomes `positions[i*3+1], positions[i*3+2]`).

```javascript
async function loadVoxels(voxelMeta) {
    const resp = await fetch('/api/voxels');
    const meta = JSON.parse(resp.headers.get('X-Meta'));
    const buf = await resp.arrayBuffer();

    const n = meta.n_voxels;
    const materials = meta.materials;

    // New layout: positions(n*3*4) + sizes(n*4) + colors(n*3) + matIndices(n)
    let offset = 0;
    const positions = new Float32Array(buf, offset, n * 3); offset += n * 3 * 4;
    const sizes = new Float32Array(buf, offset, n); offset += n * 4;
    const colors = new Uint8Array(buf, offset, n * 3); offset += n * 3;
    const matIndices = new Uint8Array(buf, offset, n);

    const defaultVs = meta.voxel_size || CFG.voxels.default_size_fallback;
    voxelSize = defaultVs;

    // Group by (material, rounded size) for multi-resolution instanced meshes
    const groups = {};
    for (let i = 0; i < n; i++) {
        const matName = materials[matIndices[i]];
        const vs = sizes[i] || defaultVs;
        const sizeKey = vs.toFixed(4);
        const groupKey = matName + '|' + sizeKey;
        if (!groups[groupKey]) groups[groupKey] = { matName, vs, indices: [] };
        groups[groupKey].indices.push(i);
    }

    const voxMatCfg = CFG.voxels.material;
    const dummy = new THREE.Object3D();

    for (const [groupKey, group] of Object.entries(groups)) {
        const { matName, vs, indices } = group;
        const count = indices.length;
        const cubeSize = vs * CFG.voxels.size_scale;
        const geometry = new THREE.BoxGeometry(cubeSize, cubeSize, cubeSize);
        const mc = MATERIAL_COLORS[matName] || [200, 200, 200];

        const matClass = new THREE.MeshStandardMaterial({
            color: new THREE.Color(mc[0]/255, mc[1]/255, mc[2]/255),
            roughness: voxMatCfg.roughness,
            metalness: voxMatCfg.metalness,
            flatShading: voxMatCfg.flat_shading,
        });
        const meshClass = new THREE.InstancedMesh(geometry, matClass, count);
        meshClass.castShadow = true;
        meshClass.receiveShadow = true;

        for (let j = 0; j < count; j++) {
            const i = indices[j];
            // Y-up passthrough: no axis swap needed
            dummy.position.set(positions[i*3], positions[i*3+1], positions[i*3+2]);
            dummy.updateMatrix();
            meshClass.setMatrixAt(j, dummy.matrix);
        }
        meshClass.instanceMatrix.needsUpdate = true;
        scene.add(meshClass);

        // Track by material name for layer toggling (array for multi-resolution)
        if (!voxelMeshes[matName]) voxelMeshes[matName] = { classified: [] };
        if (Array.isArray(voxelMeshes[matName].classified)) {
            voxelMeshes[matName].classified.push(meshClass);
        } else {
            voxelMeshes[matName].classified = [meshClass];
        }
    }

    // NOTE: Layer toggling code that reads voxelMeshes[matName].classified
    // must be updated to handle arrays (iterate and toggle each mesh).
    // Search for "voxelMeshes" references in index.html and update accordingly.

    // Heightmap: Y is now vertical (index 1), XZ is horizontal
    const hmRes = defaultVs * CFG.voxels.heightmap_resolution_factor;
    voxelHeightmap = {};
    for (let i = 0; i < n; i++) {
        const tx = positions[i*3];
        const ty = positions[i*3+1];  // vertical
        const tz = positions[i*3+2];
        const vs = sizes[i] || defaultVs;
        const key = Math.round(tx / hmRes) + ',' + Math.round(tz / hmRes);
        const top = ty + vs * 0.5;
        if (!(key in voxelHeightmap)) {
            voxelHeightmap[key] = [top];
        } else {
            voxelHeightmap[key].push(top);
        }
    }
    // Sort each column descending for gravity stepping
    for (const key of Object.keys(voxelHeightmap)) {
        voxelHeightmap[key].sort((a, b) => b - a);
    }
}
```

- [ ] **Step 3: Update the hull mesh rendering in `loadHullMesh` to remove Z-to-Y swap**

The hull mesh vertex swap at line ~917 also needs updating. The hull mesh comes from `prepare_for_raytracing` which outputs Z-up, so the hull mesh endpoint needs its own handling. Check if the hull mesh endpoint already returns Z-up vertices (it does, from greedy meshing). The frontend swap for hull mesh vertices should stay as-is since the hull mesh is in Z-up from the ray tracer.

- [ ] **Step 4: Commit**

```bash
git add src/aegis/viewer/scene_data.py src/aegis/viewer/templates/index.html
git commit -m "feat: per-voxel sizes in binary format, Y-up rendering in frontend"
```

---

### Task 9: Update server.py cache and loading functions

**Files:**
- Modify: `src/aegis/viewer/server.py:111-164`

- [ ] **Step 1: Update `_load_and_cache_voxels_single`**

Match the new `load_voxels` return type. Remove `voxel_transform` and `voxel_grid_coords` from cache. Add `voxel_sizes`.

```python
def _load_and_cache_voxels_single(voxel_json: str, bbox_radius: float) -> None:
    positions, colors, materials, voxel_sizes = load_voxels(
        voxel_json, bbox_radius=bbox_radius,
    )
    with _cache_lock:
        _cache["voxel_positions"] = positions
        _cache["voxel_materials"] = materials
        _cache["voxel_sizes"] = voxel_sizes
        _cache["voxel_binary"], _cache["voxel_meta"] = voxels_to_binary(
            positions, colors, materials, voxel_sizes=voxel_sizes,
        )
        _cache["body_placement"] = find_body_placement(positions, materials)
    try:
        from aegis.viewer.raytracer import clear_voxel_scene_cache
        clear_voxel_scene_cache()
    except ImportError:
        pass
    vs = float(np.median(voxel_sizes)) if len(voxel_sizes) > 0 else 0
    print(f"  Voxels: {len(positions):,} loaded, median_size={vs:.4f}")
```

- [ ] **Step 2: Update `_load_and_cache_voxels_dir` similarly**

- [ ] **Step 3: Update all cache reset paths**

Remove `_cache["voxel_grid_coords"]` and `_cache["voxel_transform"]` references. Add `_cache["voxel_sizes"] = None`.

- [ ] **Step 4: Delete the `_load_grid_coords` function** (lines ~100-108 of server.py)

This function is only called from `_load_and_cache_voxels_single` as a fallback when `grid_coords` is empty. Since the cache no longer stores `voxel_grid_coords`, the function is dead code. Delete it entirely.

Note: `routes/location.py` has been verified to NOT reference any removed cache keys (`voxel_transform`, `voxel_grid_coords`). It calls `_load_and_cache_voxels_dir` indirectly which will use the new signatures. No changes needed there.

- [ ] **Step 5: Run fast tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`

- [ ] **Step 6: Commit**

```bash
git add src/aegis/viewer/server.py
git commit -m "refactor: server cache uses per-voxel sizes, removes transform and grid_coords"
```

---

### Task 10: Update routes (compute.py, data.py)

**Files:**
- Modify: `src/aegis/viewer/routes/compute.py:164-207, 290-360`
- Modify: `src/aegis/viewer/routes/data.py:60-73`

- [ ] **Step 1: Update hull mesh endpoint**

Replace direct grid_coords access with `prepare_for_raytracing()` call.

```python
# In api_voxels_hull_mesh:
with cache_lock:
    voxel_positions = cache.get("voxel_positions")
    voxel_sizes = cache.get("voxel_sizes")
    voxel_meta = cache.get("voxel_meta")
if voxel_positions is None or len(voxel_positions) == 0:
    return jsonify({"error": "No voxel data"}), 400

from aegis.viewer.scene_data import prepare_for_raytracing, extract_exterior

z_up_pos, grid_coords, vs = prepare_for_raytracing(voxel_positions, voxel_sizes)
ext_mask = extract_exterior(grid_coords)
ext_grid = grid_coords[ext_mask]
ext_pos = z_up_pos[ext_mask]

scene = get_or_build_voxel_scene(ext_pos, ext_grid, voxel_size=vs)
```

- [ ] **Step 2: Update voxel RT endpoint similarly**

Same pattern: read `voxel_positions` and `voxel_sizes` from cache, call `prepare_for_raytracing()`.

- [ ] **Step 3: Remove tile transform block in data.py**

Replace the Z-to-Y swap logic with `transform_list = None`.

```python
# In api_tiles:
# No transform needed: voxelearth outputs Y-up, Three.js is Y-up
return jsonify({"tiles": tile_names, "transform": None})
```

- [ ] **Step 4: Run fast tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/routes/compute.py src/aegis/viewer/routes/data.py
git commit -m "refactor: routes use prepare_for_raytracing, remove tile transform"
```

---

### Task 11: Clean up dead code

**Files:**
- Modify: `src/aegis/viewer/scene_data.py`
- Modify: `src/aegis/viewer/config.py`

- [ ] **Step 1: Remove dead functions from scene_data.py**

Delete: `_ecef_to_local()`, `_yup_to_zup()`, `_transform_to_local()`, `compute_voxel_size()` (keep only as private fallback called from `_parse_voxel_json` path when `tile_unit is None`). Remove the ECEF-related imports if any.

Actually, keep `compute_voxel_size()` since it is the fallback for old-format JSON without metadata. Just remove the other three transform functions.

- [ ] **Step 2: Remove ECEF config from config.py**

Delete the `ecef` section from `DEFAULTS` (detection_threshold, etc).

- [ ] **Step 3: Remove old `_deduplicate` function**

It has been replaced by `_spatial_deduplicate`.

- [ ] **Step 4: Run lint and tests**

```bash
py -3.12 -m ruff check src/ tests/
py -3.12 -m ruff format src/ tests/
py -3.12 -m pytest tests/ -m "not slow" -x
```

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/scene_data.py src/aegis/viewer/config.py
git commit -m "refactor: remove dead ECEF, transform, and grid-dedup code"
```

---

### Task 12: Update existing tests

**Files:**
- Modify: `tests/test_voxel_rt_mesh.py`

- [ ] **Step 1: Check which existing tests break**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x -v 2>&1 | head -60`

The `test_voxel_rt_mesh.py` tests call `round_triangle_scene` directly with grid_coords. These should still work since `round_triangle_scene` accepts grid_coords directly. But check if any other tests import the old `load_voxels` signature.

- [ ] **Step 2: Fix any broken tests**

Update imports and call signatures to match the new API. The `test_voxel_rt_mesh.py` tests that create grid_coords directly should still work since `round_triangle_scene` hasn't changed.

- [ ] **Step 3: Run all fast tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: update tests for new voxel pipeline API"
```

---

### Task 13: Visual validation

**Files:** None (manual testing)

- [ ] **Step 1: Launch viewer with Ghent dataset**

```bash
py -3.12 -m aegis.viewer --voxel-dir "../nodejs-voxelearth/pipeline_cache/ghent_belgium_r30/voxels" --bbox 30
```

- [ ] **Step 2: Screenshot and verify no visible gaps between voxels**

Use Playwright to screenshot the scene. Compare with the current (broken) rendering. Voxels should form a clean surface without visible gaps or overlaps within a single tile.

- [ ] **Step 3: Test location loading**

Type a location in the viewer search box and verify the full pipeline works end-to-end.

- [ ] **Step 4: Commit any fixes needed**

---

### Task 14: Final cleanup and push

- [ ] **Step 1: Run full test suite**

```bash
py -3.12 -m ruff check src/ tests/
py -3.12 -m ruff format --check src/ tests/
py -3.12 -m pytest tests/ -m "not slow" -x
```

- [ ] **Step 2: Push**

```bash
git push origin master
```
