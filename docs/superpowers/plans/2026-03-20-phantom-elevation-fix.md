# Phantom elevation and collision fix - Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix premature climbing bug, add step-up/collision physics, and a teleport key.

**Architecture:** Replace the neighbor-MAX heightmap lookup with a point lookup, add per-axis collision blocking with a configurable step-up threshold, and add a teleport-to-top escape key. All changes are in the viewer frontend (index.html) and config (config.py, default.json).

**Tech Stack:** JavaScript (Three.js), Python (Flask config), JSON config

**Spec:** `docs/superpowers/specs/2026-03-20-phantom-elevation-fix-design.md`

---

### Task 1: Add config values

**Files:**
- Modify: `src/aegis/viewer/config.py:103` (heightmap_resolution_factor), `src/aegis/viewer/config.py:148-162` (physics)
- Modify: `configs/default.json`

- [ ] **Step 1: Update config.py defaults**

In `config.py`, change `heightmap_resolution_factor` from 2 to 1:

```python
"heightmap_resolution_factor": 1,
```

In the `"physics"` dict (after `"dt_clamp": 0.1`), add:

```python
"max_step_height": 0.5,
"teleport_radius": 2,
```

- [ ] **Step 2: Update default.json**

Sync the same values in `configs/default.json`. Find the `heightmap_resolution_factor` entry and change 2 to 1. Find the physics section and add the two new keys.

- [ ] **Step 3: Add JS constant in index.html**

At line ~299 (after `const GROUND_SNAP = CFG.physics.ground_snap;`), add:

```javascript
const MAX_STEP = CFG.physics.max_step_height;
```

- [ ] **Step 4: Run lint**

Run: `py -3.12 -m ruff check src/ tests/`

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/config.py configs/default.json src/aegis/viewer/templates/index.html
git commit -m "feat(viewer): add max_step_height and teleport_radius config, set heightmap factor to 1"
```

---

### Task 2: Rewrite getGroundY to point lookup

**Files:**
- Modify: `src/aegis/viewer/templates/index.html` - functions `getGroundYFromSionnaMeshes` and `getGroundY`
- Modify: `src/aegis/viewer/templates/index.html` - three callers passing `wide=true` (search for `getGroundY(bodyOffset.x, bodyOffset.z, true)`)

- [ ] **Step 1: Rewrite getGroundYFromSionnaMeshes**

Find `function getGroundYFromSionnaMeshes(x, z, wide)` and replace the entire function with a single-ray version (no `wide` parameter):

```javascript
function getGroundYFromSionnaMeshes(x, z) {
    const sc = CFG.sionna_scene || {};
    const yTop = sc.ground_ray_height ?? 2000;
    const clearance = sc.feet_clearance_m ?? 0.05;
    _sionnaGroundOrigin.set(x, yTop, z);
    raycaster.set(_sionnaGroundOrigin, _sionnaGroundDir);
    const hits = raycaster.intersectObjects(sceneMeshes, false);
    if (hits.length > 0) return hits[0].point.y + clearance;
    return bodyOffset.y;
}
```

- [ ] **Step 2: Rewrite getGroundY**

Find `function getGroundY(x, z, wide)` and replace the entire function with a point lookup (no `wide` parameter):

```javascript
function getGroundY(x, z) {
    if (usingSionnaScene()) {
        return getGroundYFromSionnaMeshes(x, z);
    }
    if (!voxelHeightmap) return bodyOffset.y;
    const hmRes = voxelSize * CFG.voxels.heightmap_resolution_factor;
    const cx = Math.round(x / hmRes);
    const cz = Math.round(z / hmRes);
    const key = cx + ',' + cz;
    return key in voxelHeightmap ? voxelHeightmap[key] + voxelSize * 0.5 : bodyOffset.y;
}
```

- [ ] **Step 3: Update callers that passed wide=true**

Three call sites pass `wide=true`. Search for `getGroundY(bodyOffset.x, bodyOffset.z, true)` and remove the third argument from each, changing to `getGroundY(bodyOffset.x, bodyOffset.z)`.

- [ ] **Step 4: Run lint**

Run: `py -3.12 -m ruff check src/ tests/`

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "fix(viewer): rewrite getGroundY to point lookup, remove neighbor-MAX bug"
```

---

### Task 3: Rewrite updateMovement with collision and cliff detection

**Files:**
- Modify: `src/aegis/viewer/templates/index.html` - the block from `// Vertical dynamics` through the end of the `newGroundY` cliff detection (includes the horizontal position update `bodyOffset.x += ...` lines)

- [ ] **Step 1: Replace the vertical dynamics and position update block**

Find the `// Vertical dynamics` comment in `updateMovement()`. Replace everything from that comment through the closing brace of the `else if (bodyOffset.y <= newGroundY + GROUND_SNAP)` block (the entire vertical dynamics + horizontal position update + cliff detection section) with:

```javascript
            // Vertical dynamics
            const groundY = getGroundY(bodyOffset.x, bodyOffset.z);

            if (onGround) {
                if (wantsJump) {
                    bodyVelocity.y = JUMP_IMPULSE;
                    onGround = false;
                } else {
                    bodyVelocity.y = 0;
                    bodyOffset.y = groundY;
                }
            } else {
                bodyVelocity.y -= GRAVITY * dt;

                if (bodyOffset.y + bodyVelocity.y * dt <= groundY) {
                    bodyOffset.y = groundY;
                    bodyVelocity.y = 0;
                    onGround = true;
                }
            }

            // Horizontal movement with collision
            let nextX = bodyOffset.x + bodyVelocity.x * dt;
            let nextZ = bodyOffset.z + bodyVelocity.z * dt;

            if (onGround) {
                // Test X axis independently (allows wall-sliding)
                const testXGroundY = getGroundY(nextX, bodyOffset.z);
                if (testXGroundY - bodyOffset.y > MAX_STEP) {
                    nextX = bodyOffset.x;
                    bodyVelocity.x = 0;
                }

                // Test Z axis independently (allows wall-sliding)
                const testZGroundY = getGroundY(nextX, nextZ);
                if (testZGroundY - bodyOffset.y > MAX_STEP) {
                    nextZ = bodyOffset.z;
                    bodyVelocity.z = 0;
                }
            }

            bodyOffset.x = nextX;
            bodyOffset.z = nextZ;
            if (!onGround) {
                bodyOffset.y += bodyVelocity.y * dt;
            }

            // Cliff and landing detection
            const newGroundY = getGroundY(bodyOffset.x, bodyOffset.z);
            if (onGround) {
                if (bodyOffset.y - newGroundY > MAX_STEP) {
                    // Walked off a cliff
                    onGround = false;
                } else {
                    bodyOffset.y = newGroundY;
                }
            } else if (bodyOffset.y <= newGroundY + GROUND_SNAP) {
                bodyOffset.y = newGroundY;
                bodyVelocity.y = 0;
                onGround = true;
            }
```

- [ ] **Step 2: Verify the function runs lint-clean**

Run: `py -3.12 -m ruff check src/ tests/`

- [ ] **Step 3: Commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "feat(viewer): add step-up collision and cliff detection to movement physics"
```

---

### Task 4: Add teleport key and HUD

**Files:**
- Modify: `src/aegis/viewer/templates/index.html:736-750` (keydown handler)
- Modify: `src/aegis/viewer/templates/index.html:234-239` (hint div)
- Add function near `getGroundY` (~line 1879)

- [ ] **Step 1: Add teleportToTop function**

After `getGroundY`, add:

```javascript
function teleportToTop() {
    if (usingSionnaScene()) {
        bodyOffset.y = getGroundY(bodyOffset.x, bodyOffset.z);
    } else if (voxelHeightmap) {
        const hmRes = voxelSize * CFG.voxels.heightmap_resolution_factor;
        const cx = Math.round(bodyOffset.x / hmRes);
        const cz = Math.round(bodyOffset.z / hmRes);
        const r = CFG.physics.teleport_radius;
        let bestY = null;
        for (let dx = -r; dx <= r; dx++) {
            for (let dz = -r; dz <= r; dz++) {
                const k = (cx + dx) + ',' + (cz + dz);
                if (k in voxelHeightmap) {
                    const y = voxelHeightmap[k];
                    if (bestY === null || y > bestY) bestY = y;
                }
            }
        }
        if (bestY !== null) bodyOffset.y = bestY + voxelSize * 0.5;
    }
    bodyVelocity.y = 0;
    onGround = true;
    updateBodyTransform();
    debouncedRecompute();
}
```

- [ ] **Step 2: Add KeyT to keydown handler**

In the keydown handler (~line 736), after the Arrow key block and before the WASD preventDefault, add:

```javascript
if (e.code === 'KeyT') {
    teleportToTop();
    e.preventDefault();
}
```

Also update the preventDefault line to include KeyT:

```javascript
if ('KeyW KeyA KeyS KeyD KeyQ KeyE KeyT'.includes(e.code)) e.preventDefault();
```

- [ ] **Step 3: Update HUD hint text**

Change line 237 from:
```html
WASD: walk body | QE: rotate | Space: jump | Shift: sprint<br>
```
to:
```html
WASD: walk | QE: rotate | Space: jump | Shift: sprint | T: teleport<br>
```

- [ ] **Step 4: Run lint**

Run: `py -3.12 -m ruff check src/ tests/`

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/templates/index.html
git commit -m "feat(viewer): add T key to teleport phantom to top of nearby structures"
```

---

### Task 5: Test manually and verify

- [ ] **Step 1: Run linting**

Run: `py -3.12 -m ruff check src/ tests/`
Run: `py -3.12 -m ruff format --check src/ tests/`

- [ ] **Step 2: Run fast tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`

- [ ] **Step 3: Launch viewer and test**

Run: `py -3.12 -m aegis.viewer`

Test checklist:
- Walk toward a building wall: phantom walks flat until blocked, does not climb early
- Walk up a 1-voxel step: phantom steps up instantly
- Walk off a cliff edge: phantom falls with gravity
- Walk into a corner: phantom stops, no jittering
- Walk along a wall at an angle: slides along the wall
- Press T on flat ground: no visible change
- Press T near a tall structure: teleports to roof

- [ ] **Step 4: Final commit if any fixes needed, then push**

```bash
git push origin master
```
