# Phantom elevation and collision fix

## Problem

The phantom walks up buildings and mountains before actually reaching them. Root cause: `getGroundY()` searches a 3x3 neighborhood of heightmap cells and returns the MAX height. Combined with a heightmap resolution factor of 2 (cells are 2x voxel size), the phantom "sees" nearby tall structures and snaps upward ~0.5m before it arrives.

Three compounding issues:

1. Neighbor search always takes the MAX (even non-wide mode uses r=1, a 3x3 grid)
2. Heightmap resolution is 2x the voxel size, losing edge detail
3. No distinction between walkable steps and impassable walls

## Design

### 1. Point lookup instead of neighbor search

Change `getGroundY()` from a 3x3 neighbor MAX search to a single-cell point lookup. The phantom only reads the height of the cell it is standing on.

**File:** `index.html`, function `getGroundY`

```javascript
function getGroundY(x, z) {
    if (usingSionnaScene()) return getGroundYFromSionnaMeshes(x, z);
    if (!voxelHeightmap) return bodyOffset.y;
    const hmRes = voxelSize * CFG.voxels.heightmap_resolution_factor;
    const cx = Math.round(x / hmRes);
    const cz = Math.round(z / hmRes);
    const key = cx + ',' + cz;
    return key in voxelHeightmap ? voxelHeightmap[key] + voxelSize * 0.5 : bodyOffset.y;
}
```

The `wide` parameter is removed. All callers that currently pass `wide=true` (lines ~845, ~1298, ~1496) must be updated to call without it.

The Sionna mesh path (`getGroundYFromSionnaMeshes`) also loses its `wide` parameter. It should cast a single downward ray at `(x, yTop, z)` instead of sampling a 3x3 grid. This keeps behavior consistent across both terrain types.

Missing heightmap cells (no voxels at that column) return `bodyOffset.y`, meaning they are treated as walkable open ground. This is intentional.

### 2. Reduce heightmap resolution factor

Change `heightmap_resolution_factor` from 2 to 1. Each heightmap cell now matches exactly one voxel column. The heightmap is sparse (only stores columns that contain voxels), so the memory increase is negligible.

**File:** `config.py` (line 103), `default.json`

### 3. Step-up threshold with collision blocking

Add a `max_step_height` config (default 0.5m, roughly one stair step). In `updateMovement()`, the collision check gates the position update itself. No position is written until validated.

```javascript
const MAX_STEP = CFG.physics.max_step_height;

// Compute candidate position
let nextX = bodyOffset.x + bodyVelocity.x * dt;
let nextZ = bodyOffset.z + bodyVelocity.z * dt;

if (onGround) {
    // Test X and Z independently to allow wall-sliding
    const testXGroundY = getGroundY(nextX, bodyOffset.z);
    if (testXGroundY - bodyOffset.y > MAX_STEP) {
        nextX = bodyOffset.x;  // blocked in X
        bodyVelocity.x = 0;
    }

    const testZGroundY = getGroundY(nextX, nextZ);
    if (testZGroundY - bodyOffset.y > MAX_STEP) {
        nextZ = bodyOffset.z;  // blocked in Z
        bodyVelocity.z = 0;
    }
}

// Apply validated position
bodyOffset.x = nextX;
bodyOffset.z = nextZ;
```

Step-up for height differences <= `max_step_height` happens instantly (the phantom snaps to the new ground height on the next frame). No interpolation. The existing `ground_snap` (0.05m) continues to apply only for landing detection when airborne (line ~2010), and does not interact with `max_step_height`.

At corners where both X and Z are blocked, both components zero out and the phantom stops completely.

### 4. Cliff/falling detection

When walking off an edge where the ground drops by more than `max_step_height`, the phantom goes airborne. This replaces the current hardcoded 1.0m threshold at line ~2007.

```javascript
const newGroundY = getGroundY(bodyOffset.x, bodyOffset.z);
if (onGround) {
    if (bodyOffset.y - newGroundY > MAX_STEP) {
        // Walked off a cliff, go airborne
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

The check is directional (downward only: `bodyOffset.y - newGroundY`), not bidirectional like the old `Math.abs` check. Upward step-ups are handled by the collision logic in section 3.

### 5. Teleport key (T)

Press `T` to snap the phantom to the top of the highest voxel at its current XZ position. Uses a configurable search radius of 2 heightmap cells (config: `physics.teleport_radius`, default 2) to find the tallest column nearby.

For Sionna scenes, uses a single downward raycast at the current position.

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
                const k = (cx+dx) + ',' + (cz+dz);
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
}
```

Triggered by keydown handler for `KeyT`. Added to the existing keyboard switch.

### 6. HUD indicator

Add `[T] Teleport to top` to the existing controls hint overlay in the bottom-left corner.

## Config changes

| Key | Old | New | Notes |
|-----|-----|-----|-------|
| `voxels.heightmap_resolution_factor` | 2 | 1 | Match voxel grid exactly |
| `physics.max_step_height` | (new) | 0.5 | Max height diff for auto-step (meters) |
| `physics.teleport_radius` | (new) | 2 | Heightmap cells to search for teleport |

## Files changed

1. `src/aegis/viewer/config.py` - add `max_step_height` and `teleport_radius`, change `heightmap_resolution_factor`
2. `src/aegis/viewer/templates/index.html`:
   - Rewrite `getGroundY` (remove `wide`, point lookup)
   - Simplify `getGroundYFromSionnaMeshes` (remove `wide`, single ray)
   - Update all callers that passed `wide=true`
   - Rewrite collision/position update in `updateMovement`
   - Replace cliff detection threshold
   - Add `teleportToTop()` function and `KeyT` handler
   - Update HUD controls text
3. `configs/default.json` - sync defaults

## Testing

- Walk toward a building wall: phantom should walk flat until blocked, not climb early
- Walk up a 1-voxel step: phantom should step up instantly
- Walk off a cliff: phantom should fall with gravity
- Walk into a building corner: phantom stops completely, does not jitter
- Walk along a wall at an angle: should slide, not stick
- Press T on flat ground: no visible change
- Press T next to a tall building: teleport to roof
- Sionna scene: same behaviors as voxel scene
