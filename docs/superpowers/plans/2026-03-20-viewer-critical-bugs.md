# Viewer Critical Bugs Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the four critical concurrency and state management bugs in the AEGIS viewer.

**Architecture:** Bug #1 is backend (add threading.Lock around `_cache`). Bugs #2-4 are frontend (fix listener cleanup, add AbortController, guard EventSource). All changes are isolated and independent.

**Tech Stack:** Python/Flask (server.py), JavaScript/Three.js (index.html)

---

### Task 1: Add threading lock to `_cache` in server.py

The module-level `_cache` dict is mutated by Flask request handlers running in concurrent threads (`app.run(threaded=True)`). A location load writing voxel data while a compute reads it causes corrupted state.

**Files:**
- Modify: `src/aegis/viewer/server.py:24` (add lock), all `_cache` write sites
- Test: `tests/test_viewer_server_lock.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_viewer_server_lock.py`:

```python
"""Test that _cache access is thread-safe."""

from __future__ import annotations

import threading

from aegis.viewer.server import _cache, _cache_lock


def test_cache_lock_exists():
    """The module exposes a threading.Lock for cache synchronization."""
    assert isinstance(_cache_lock, threading.Lock)


def test_cache_lock_is_reentrant_safe():
    """Lock can be acquired and released without deadlock."""
    _cache_lock.acquire()
    try:
        _cache["_test"] = True
        assert _cache["_test"] is True
    finally:
        _cache_lock.release()
        _cache.pop("_test", None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_viewer_server_lock.py -v`
Expected: FAIL with `ImportError: cannot import name '_cache_lock'`

- [ ] **Step 3: Add the lock to server.py**

In `src/aegis/viewer/server.py`, at line 24, change:

```python
# Module-level cache
_cache: dict = {}
```

to:

```python
import threading

# Module-level cache
_cache: dict = {}
_cache_lock = threading.Lock()
```

(Move the `import threading` to the top imports section.)

- [ ] **Step 4: Wrap `_cache` writes in `_load_and_cache_voxels_single` and `_load_and_cache_voxels_dir`**

Wrap the body of `_load_and_cache_voxels_single` (lines 42-58) with `with _cache_lock:`.
Wrap the body of `_load_and_cache_voxels_dir` (lines 63-79) with `with _cache_lock:`.

- [ ] **Step 5: Wrap `_cache` writes in `create_app` initialization**

Wrap the body data loading block (lines 115-159) with `with _cache_lock:`.

- [ ] **Step 6: Wrap `_cache` reads in route handlers that read multiple cache keys**

Add `with _cache_lock:` around the multi-key reads in:
- `api_compute` (lines 290-291, reading `body`)
- `api_voxels_hull_mesh` (lines 365-376, reading `voxel_grid_coords`, `voxel_positions`, `voxel_meta`)
- `api_compute_voxel_rt` (lines 513-560, reading `body`, `voxel_grid_coords`, `voxel_positions`, `voxel_meta`)
- `api_location_load`'s `generate()` inner function (line 742, calling `_load_and_cache_voxels_dir` which already locks internally, but also lines 748-751 writing `tiles_dir`)

For single-key reads (`api_body`, `api_voxels`), the GIL makes dict reads atomic, so no lock needed there.

- [ ] **Step 7: Run test to verify it passes**

Run: `py -3.12 -m pytest tests/test_viewer_server_lock.py -v`
Expected: PASS

- [ ] **Step 8: Run all fast tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: All pass

- [ ] **Step 9: Lint and commit**

```bash
py -3.12 -m ruff check src/aegis/viewer/server.py tests/test_viewer_server_lock.py
py -3.12 -m ruff format src/aegis/viewer/server.py tests/test_viewer_server_lock.py
git add src/aegis/viewer/server.py tests/test_viewer_server_lock.py
git commit -m "fix(viewer): add threading lock to _cache for concurrent request safety"
```

---

### Task 2: Fix event listener accumulation in `buildLayerButtons()`

`buildLayerButtons()` is called on initial load (line 836) and again after `reloadVoxels()` (line 1291). Each call creates new buttons with `addEventListener('click', ...)`. While `container.innerHTML = ''` removes old DOM nodes (which does garbage-collect their listeners), the real issue is that `buildLayerButtons` also adds a body toggle button, and if `bodyMesh` persists across reloads, multiple body buttons accumulate visually OR the old closure references stale mesh state.

After review: `container.innerHTML = ''` at line 1187 properly clears all child elements and their listeners. The buttons are fresh each time. This is actually NOT a real bug in the current code since the DOM removal clears listeners. However, the pattern is fragile. The safer fix is to use event delegation on the container instead.

**Files:**
- Modify: `src/aegis/viewer/templates/index.html:1185-1215`
- Test: Manual (DOM behavior, no Python test possible)

- [ ] **Step 1: Refactor to event delegation**

Replace the `buildLayerButtons` function (lines 1185-1215) with:

```javascript
function buildLayerButtons() {
    const container = document.getElementById('layers');
    container.innerHTML = '';

    for (const [mat, meshes] of Object.entries(voxelMeshes)) {
        const mc = MATERIAL_COLORS[mat] || [200, 200, 200];
        const count = meshes.classified.count;
        const btn = document.createElement('button');
        btn.className = 'layer-btn active';
        btn.dataset.layer = mat;
        btn.dataset.type = 'voxel';
        btn.style.borderLeft = `4px solid rgb(${mc[0]},${mc[1]},${mc[2]})`;
        btn.textContent = `${mat} (${count.toLocaleString()})`;
        container.appendChild(btn);
    }

    if (bodyMesh) {
        const bc = CFG.body.layer_button_color;
        const btn = document.createElement('button');
        btn.className = 'layer-btn active';
        btn.dataset.layer = 'body';
        btn.dataset.type = 'body';
        btn.style.borderLeft = `4px solid rgb(${bc[0]},${bc[1]},${bc[2]})`;
        btn.textContent = `body (${bodyMeta ? bodyMeta.n_triangles.toLocaleString() + ' tri' : ''})`;
        container.appendChild(btn);
    }
}
```

- [ ] **Step 2: Add one-time event delegation listener**

Add this once during `init()` or at module scope (after DOM is ready), NOT inside `buildLayerButtons`:

```javascript
// One-time event delegation for layer buttons
document.getElementById('layers').addEventListener('click', (e) => {
    const btn = e.target.closest('.layer-btn');
    if (!btn) return;

    const active = btn.classList.toggle('active');
    btn.classList.toggle('inactive', !active);

    if (btn.dataset.type === 'body') {
        if (bodyMesh) bodyMesh.visible = active;
    } else {
        const matName = btn.dataset.layer;
        if (voxelMeshes[matName]) {
            voxelMeshes[matName].classified.visible = active;
        }
    }
});
```

- [ ] **Step 3: Remove old `toggleLayer` function**

Delete the `toggleLayer` function (lines 1217-1223) since delegation handles it.

- [ ] **Step 4: Commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "fix(viewer): use event delegation for layer buttons to prevent listener accumulation"
```

---

### Task 3: Add AbortController to `computeDosimetry()`

When the user rapidly clicks to place the antenna, multiple concurrent fetch requests are sent. Old responses can arrive after new ones, overwriting correct results with stale data. Fix: abort previous request when a new one starts.

**Files:**
- Modify: `src/aegis/viewer/templates/index.html:309-310` (add controller variable), `1520-1654` (use it in computeDosimetry)
- Test: Manual (network behavior)

- [ ] **Step 1: Add AbortController state variable**

Near line 310 (after `let isComputing = false;`), add:

```javascript
let computeAbortController = null;
```

- [ ] **Step 2: Abort previous request at start of `computeDosimetry`**

At the top of `computeDosimetry` (after line 1521 `if (!bodyMesh) return;`), add:

```javascript
// Abort any in-flight compute request
if (computeAbortController) {
    computeAbortController.abort();
}
computeAbortController = new AbortController();
const signal = computeAbortController.signal;
```

- [ ] **Step 3: Pass `signal` to all three fetch calls**

Add `signal` to the fetch options in all three branches:

Voxel RT (line 1554):
```javascript
resp = await fetch('/api/compute/voxel-rt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ... }),
    signal,
});
```

Sionna RT (line 1587):
```javascript
resp = await fetch('/api/compute/rt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ... }),
    signal,
});
```

Plain compute (line 1615):
```javascript
resp = await fetch('/api/compute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ... }),
    signal,
});
```

- [ ] **Step 4: Handle AbortError in the catch block**

Modify the catch block (line 1643) to silently ignore aborted requests:

```javascript
} catch (err) {
    if (err.name === 'AbortError') return;  // superseded by newer request
    console.error('Dosimetry computation error:', err);
    const errMsg = err instanceof Error ? err.message : String(err);
    setComputeError(errMsg);
    const statusEl = document.getElementById('rt-status');
    if (statusEl) statusEl.textContent = `Error: ${errMsg}`;
}
```

- [ ] **Step 5: Guard the finally block against superseded requests**

The `finally` block must only clean up state if this invocation is still the "current" one. If a newer request superseded us (aborted our controller), that newer request owns `isComputing` and the UI overlay. Compare the signal to avoid clobbering the newer request's state:

```javascript
} finally {
    // Only clean up if we are still the active request
    if (computeAbortController?.signal === signal) {
        computeAbortController = null;
        isComputing = false;
        clearInterval(computeTimerInterval);
        document.getElementById('computing').style.display = 'none';
    }
}
```

- [ ] **Step 6: Lint and commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "fix(viewer): abort stale compute requests when new antenna placement occurs"
```

---

### Task 4: Guard EventSource against double-registration in `loadLocation`

Clicking "Load Location" twice creates two overlapping SSE streams. The second stream's events fire while the first is still open. Fix: close any existing EventSource before creating a new one.

**Files:**
- Modify: `src/aegis/viewer/templates/index.html:1227-1265` (loadLocation function)
- Test: Manual (SSE behavior)

- [ ] **Step 1: Add module-level EventSource variable**

Near line 310 (with the other state variables), add:

```javascript
let activeLocationES = null;
```

- [ ] **Step 2: Close existing EventSource at start of `loadLocation`**

At the top of `window.loadLocation` (after `if (!location) return;` on line 1232), add:

```javascript
// Close any existing location stream
if (activeLocationES) {
    activeLocationES.close();
    activeLocationES = null;
}
```

- [ ] **Step 3: Store the EventSource reference**

Change line 1241 from:

```javascript
const es = new EventSource('/api/location/load?' + params);
```

to:

```javascript
const es = new EventSource('/api/location/load?' + params);
activeLocationES = es;
```

- [ ] **Step 4: Clear reference on completion**

In the `done` handler (line 1248), after `es.close()`, add:

```javascript
activeLocationES = null;
```

In the `error` handler (line 1257), after `es.close()`, add:

```javascript
activeLocationES = null;
```

- [ ] **Step 5: Also close in `cancelLocation`**

In `window.cancelLocation` (line 1267), add at the top:

```javascript
if (activeLocationES) {
    activeLocationES.close();
    activeLocationES = null;
}
```

- [ ] **Step 6: Lint and commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "fix(viewer): prevent double EventSource registration on location load"
```

---

### Final verification

- [ ] **Run all fast tests**

```bash
py -3.12 -m pytest tests/ -m "not slow" -x
```

- [ ] **Lint entire viewer**

```bash
py -3.12 -m ruff check src/aegis/viewer/ tests/test_viewer_server_lock.py
py -3.12 -m ruff format --check src/aegis/viewer/ tests/test_viewer_server_lock.py
```

- [ ] **Push to origin**

```bash
git push origin master
```
