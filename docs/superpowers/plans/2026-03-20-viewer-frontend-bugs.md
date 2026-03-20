# Viewer frontend bug fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 7 frontend bugs in the AEGIS viewer (error handling, timeouts, memory leaks, stale state, retry, focus hint).

**Architecture:** All changes are in `index.html`. Tasks grouped by theme: error handling + retry (#5/#12/#14), timeout (#6), memory leaks (#10), stale state (#11), focus hint (#15). No server.py changes. **Task 4 depends on Task 3** (uses `disposeLine` helper defined in Task 3). All other tasks are independent.

**Tech Stack:** JavaScript, Three.js, HTML (single-file SPA). Requires `AbortSignal.any()` (Chrome 116+, Firefox 124+, Safari 17.4+).

**Important context:** Another agent is simultaneously refactoring `server.py` and other backend files. Do NOT modify any Python files. Only touch `src/aegis/viewer/templates/index.html`.

---

### Task 1: Wrap `loadScene` in try/catch with retry button (bugs #5, #12, #14)

`loadScene()` (line 775) calls `loadBody()`, `loadVoxels()`, and other fetches with no error handling. If any fetch fails, the `#loading` overlay stays visible forever and the panel never appears. The user must refresh the entire page.

**Files:**
- Modify: `src/aegis/viewer/templates/index.html:775-853` (loadScene function), line 1297 (cancelLocation fetch)
- Test: Manual (kill server during load, verify error + retry button shown)

- [ ] **Step 1: Wrap loadScene body in try/catch with retry button**

Replace the `loadScene` function (lines 775-853) with error handling and a retry button:

```javascript
async function loadScene() {
    try {
        const config = await (await fetch('/api/config')).json();

        if (config.body_meta) {
            await loadBody();
        }

        if (config.has_voxels) {
            await loadVoxels(config.voxel_meta);
        }

        // Load photorealistic GLB tiles if available
        await loadGlbTiles();

        const voxelRt = (config.voxel_rt_available !== false) && config.has_voxels;
        const hasSionna = config.scenes && config.scenes.length > 0;

        if (config.has_differt && (voxelRt || hasSionna)) {
            hasDiffert = true;
            document.getElementById('rt-section').style.display = 'block';
            const rtSourceSelect = document.getElementById('rtSourceSelect');

            if (!voxelRt) {
                const vo = document.getElementById('rtSourceVoxel');
                if (vo) vo.remove();
            }

            if (hasSionna) {
                for (const s of config.scenes) {
                    const opt = document.createElement('option');
                    opt.value = 'sionna:' + s.path;
                    opt.textContent = s.name + ' (Sionna)';
                    rtSourceSelect.appendChild(opt);
                }
            }

            rtSourceSelect.addEventListener('change', onRTSourceChange);
            document.getElementById('rtEnabled').addEventListener('change', (e) => {
                document.getElementById('rt-status').textContent = '';
                for (const line of pathLines) scene.remove(line);
                pathLines = [];
                if (!e.target.checked && antennaPos) drawPaths(antennaPos);
                if (antennaPos) computeDosimetry(antennaPos);
            });
            document.getElementById('maxOrderSelect').addEventListener('change', () => {
                if (antennaPos) computeDosimetry(antennaPos);
            });
        }

        // Show location loader
        const locSection = document.getElementById('location-section');
        locSection.style.display = 'block';
        if (!config.has_api_key) {
            const logDiv = document.getElementById('location-log');
            logDiv.classList.add('visible');
            logDiv.textContent = 'Set GOOGLE_API_KEY env var to enable location loading.\nRestart the viewer after setting it.';
            document.getElementById('loadLocationBtn').disabled = true;
        } else if (!config.has_location_loader) {
            const logDiv = document.getElementById('location-log');
            logDiv.classList.add('visible');
            logDiv.textContent = 'nodejs-voxelearth pipeline not found.\nSet VOXELEARTH_DIR or place it at ../nodejs-voxelearth/';
            document.getElementById('loadLocationBtn').disabled = true;
        }

        buildLayerButtons();
        await setupEnvDisplay(config);

        if (config.body_placement && bodyMesh) {
            const bp = config.body_placement;
            bodyOffset.set(bp[0], bp[2], -bp[1]);
            bodyOffset.y = getGroundY(bodyOffset.x, bodyOffset.z);
            updateBodyTransform();
        }

        centerCamera();
    } catch (err) {
        console.error('Scene load failed:', err);
        const loadingEl = document.getElementById('loading');
        loadingEl.innerHTML = '';
        const msg = document.createElement('div');
        msg.textContent = 'Failed to load scene. Check that the server is running.';
        msg.style.color = '#e74c3c';
        msg.style.marginBottom = '12px';
        loadingEl.appendChild(msg);
        const retryBtn = document.createElement('button');
        retryBtn.textContent = 'Retry';
        retryBtn.className = 'ctrl-btn';
        retryBtn.onclick = () => {
            loadingEl.innerHTML = '<div class="spinner"></div>Loading scene...';
            loadingEl.style.color = '';
            loadScene();
        };
        loadingEl.appendChild(retryBtn);
        return;
    }
    document.getElementById('loading').style.display = 'none';
    document.getElementById('panel').style.display = 'block';
}
```

Key changes:
- Entire body wrapped in `try/catch`
- On error: shows error message + Retry button in loading overlay. Clicking Retry restores the spinner and re-calls `loadScene()`.
- Success path: loading hidden and panel shown AFTER try block (only on success)
- Intentional reorder: body_placement and centerCamera now run while loading overlay is still visible (improvement: user sees final positioned scene when overlay clears)

- [ ] **Step 2: Add error handling to cancelLocation fire-and-forget fetch**

In `window.cancelLocation` (line 1297), the fetch has no catch. Change:

```javascript
fetch('/api/location/cancel', { method: 'POST' }).catch(() => {});
```

This is a fire-and-forget call, so silently swallowing the error is appropriate.

- [ ] **Step 3: Commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "fix(viewer): add error handling and retry button to loadScene"
```

---

### Task 2: Add timeout to compute fetch requests (bug #6)

If the server hangs during a compute request, `isComputing` stays true forever and the computing overlay never disappears. The user cannot trigger any new computations.

**Files:**
- Modify: `src/aegis/viewer/templates/index.html:1549-1698` (computeDosimetry function)
- Test: Manual (simulate server hang, verify timeout fires after 60s)

**Note:** Steps 1-3 must be applied together as one atomic change. `AbortSignal.any()` creates a new combined signal object, which breaks the existing `computeAbortController?.signal === signal` guard in the finally block. The generation counter in Step 1 replaces that guard.

- [ ] **Step 1: Add state variables for timeout and generation counter**

Near line 316 (after `const RECOMPUTE_INTERVAL_MS`), add:

```javascript
const COMPUTE_TIMEOUT_MS = CFG.interaction.compute_timeout_ms || 60000;
```

Near line 313 (with the other state variables, after `let computeAbortController = null;`), add:

```javascript
let computeGeneration = 0;
```

- [ ] **Step 2: Update computeDosimetry to use AbortSignal.any() and generation counter**

In `computeDosimetry`, replace the AbortController setup (lines 1553-1557):

```javascript
// Abort any in-flight compute request
if (computeAbortController) {
    computeAbortController.abort();
}
computeAbortController = new AbortController();
const signal = computeAbortController.signal;
```

with:

```javascript
// Abort any in-flight compute request
if (computeAbortController) {
    computeAbortController.abort();
}
computeAbortController = new AbortController();
const thisGeneration = ++computeGeneration;
const signal = AbortSignal.any([
    computeAbortController.signal,
    AbortSignal.timeout(COMPUTE_TIMEOUT_MS),
]);
```

Update the catch block (line 1682-1688) to handle timeout:

```javascript
} catch (err) {
    if (err.name === 'AbortError') return;  // superseded by newer request
    if (err.name === 'TimeoutError') {
        setComputeError('Compute timed out. Server may be overloaded.');
        return;
    }
    console.error('Dosimetry computation error:', err);
    const errMsg = err instanceof Error ? err.message : String(err);
    setComputeError(errMsg);
    const statusEl = document.getElementById('rt-status');
    if (statusEl) statusEl.textContent = `Error: ${errMsg}`;
}
```

Update the finally block (lines 1689-1697) to use generation counter:

```javascript
} finally {
    if (computeGeneration === thisGeneration) {
        computeAbortController = null;
        isComputing = false;
        clearInterval(computeTimerInterval);
        document.getElementById('computing').style.display = 'none';
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "fix(viewer): add timeout to compute requests to prevent stuck UI"
```

---

### Task 3: Dispose Three.js geometry and materials in drawPaths/drawRTPaths (bug #10)

Every antenna placement or body movement calls `drawPaths()` which creates new geometries, materials, and a CanvasTexture. The old objects are removed from the scene but never `.dispose()`d. VRAM grows indefinitely.

Same issue in `drawRTPaths()` for ray-tracing path visualization.

**Files:**
- Modify: `src/aegis/viewer/templates/index.html:1402-1460` (drawPaths), `1700-1725` (drawRTPaths)
- Test: Manual (place antenna many times, check memory in DevTools)

- [ ] **Step 1: Create a disposeObject3D helper**

Add before `drawPaths` (around line 1400):

```javascript
function disposeLine(obj) {
    obj.geometry?.dispose();
    if (obj.material) {
        if (obj.material.map) obj.material.map.dispose();
        obj.material.dispose();
    }
}
```

This helper works for Lines, Sprites, and any Object3D with a single material. The `?.` on geometry handles Sprites which use shared internal geometry.

- [ ] **Step 2: Dispose old pathLines in drawPaths**

In `drawPaths` (line 1402-1404), change:

```javascript
for (const line of pathLines) scene.remove(line);
pathLines = [];
```

to:

```javascript
for (const line of pathLines) {
    scene.remove(line);
    disposeLine(line);
}
pathLines = [];
```

- [ ] **Step 3: Dispose distanceLine and distanceLabel in drawPaths**

In `drawPaths` (lines 1406-1407), change:

```javascript
if (distanceLine) { scene.remove(distanceLine); distanceLine = null; }
if (distanceLabel) { scene.remove(distanceLabel); distanceLabel = null; }
```

to:

```javascript
if (distanceLine) {
    scene.remove(distanceLine);
    disposeLine(distanceLine);
    distanceLine = null;
}
if (distanceLabel) {
    scene.remove(distanceLabel);
    disposeLine(distanceLabel);
    distanceLabel = null;
}
```

`disposeLine` handles Sprites correctly: `geometry?.dispose()` is a no-op (Sprites have no user geometry), `material.map.dispose()` frees the CanvasTexture, `material.dispose()` frees the SpriteMaterial.

- [ ] **Step 4: Dispose old pathLines in drawRTPaths**

In `drawRTPaths` (lines 1701-1702), change:

```javascript
for (const line of pathLines) scene.remove(line);
pathLines = [];
```

to:

```javascript
for (const line of pathLines) {
    scene.remove(line);
    disposeLine(line);
}
pathLines = [];
```

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "fix(viewer): dispose Three.js geometry and textures to prevent VRAM leaks"
```

---

### Task 4: Clear antenna state on location reload (bug #11)

**Depends on Task 3** (uses `disposeLine` helper).

When loading a new location via `reloadVoxels()`, the old antenna mesh and position persist. The distance line references coordinates from the previous scene, and the antenna floats at the old world position which may be nonsensical in the new scene.

**Files:**
- Modify: `src/aegis/viewer/templates/index.html:1304-1334` (reloadVoxels function)
- Test: Manual (load location, place antenna, load different location, verify antenna gone)

- [ ] **Step 1: Add antenna and visualization cleanup to reloadVoxels**

At the top of `reloadVoxels()` (after line 1304 `async function reloadVoxels() {`), add antenna cleanup before the existing voxel cleanup code:

```javascript
    // Clear antenna state from previous scene
    if (antennaMesh) {
        scene.remove(antennaMesh);
        antennaMesh.traverse((obj) => {
            if (obj.isMesh) {
                obj.geometry?.dispose();
                if (obj.material) {
                    const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
                    for (const m of mats) m.dispose();
                }
            }
        });
        antennaMesh = null;
    }
    antennaPos = null;

    // Clear path visualizations
    for (const line of pathLines) {
        scene.remove(line);
        disposeLine(line);
    }
    pathLines = [];
    if (distanceLine) {
        scene.remove(distanceLine);
        disposeLine(distanceLine);
        distanceLine = null;
    }
    if (distanceLabel) {
        scene.remove(distanceLabel);
        disposeLine(distanceLabel);
        distanceLabel = null;
    }

    // Clear dosimetry display
    document.getElementById('color-legend').style.display = 'none';
    document.getElementById('stat-pabs').textContent = '--';
    document.getElementById('stat-peak').textContent = '--';
    document.getElementById('stat-sinc').textContent = '--';
    document.getElementById('stat-dist').textContent = '--';
    document.getElementById('stat-illum').textContent = '--';
    document.getElementById('stat-compliance').textContent = '--';
    document.getElementById('stat-compliance').className = 'stat-value';
    setComputeError('');
```

The rest of `reloadVoxels` (lines 1305-1334) remains unchanged.

- [ ] **Step 2: Commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "fix(viewer): clear antenna and dosimetry state on location reload"
```

---

### Task 5: Fix focus hint timeout behavior (bug #15)

The focus hint shows when WASD/Space is pressed without canvas focus. Each keydown event (including key repeat) clears and resets the timeout. While `clearTimeout` prevents actual stacking, rapid key repeats keep the hint visible indefinitely and create/destroy timeouts unnecessarily.

**Files:**
- Modify: `src/aegis/viewer/templates/index.html:763-770` (focus hint handler in init)
- Test: Manual (hold W without clicking canvas, verify hint shows once and disappears)

- [ ] **Step 1: Skip re-triggering when hint already visible**

Replace the focus hint keydown handler (lines 763-770) with:

```javascript
window.addEventListener('keydown', (e) => {
    if ('KeyW KeyA KeyS KeyD KeyQ KeyE Space'.includes(e.code) && !canvasHasFocus) {
        const hint = document.getElementById('focus-hint');
        if (hint.style.display === 'block') return;  // already showing
        hint.style.display = 'block';
        focusHintTimer = setTimeout(() => { hint.style.display = 'none'; }, clickCfg.focus_hint_timeout_ms);
    }
});
```

Changes:
- Added early return if hint is already visible
- Removed `clearTimeout(focusHintTimer)` since we return early when visible (the timer always runs to completion)

- [ ] **Step 2: Commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "fix(viewer): prevent focus hint from re-triggering while visible"
```

---

### Final verification

- [ ] **Lint**

```bash
py -3.12 -m ruff check src/aegis/viewer/ tests/
py -3.12 -m ruff format --check src/aegis/viewer/ tests/
```

- [ ] **Run fast tests**

```bash
py -3.12 -m pytest tests/ -m "not slow" -x
```

- [ ] **Push**

```bash
git push origin master
```
