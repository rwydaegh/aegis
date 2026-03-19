# Viewer E2E bug report (2026-03-17)

Tested all 19 tests from `docs/viewer_testing_prompt.md` using Playwright MCP against the AEGIS viewer at `http://127.0.0.1:5070`. Voxel data: `044ddce6e59286f561b4c89aeba53e386d3615ee_voxels.json` (27,852 voxels after filtering). Body: Thelonious (23,826 triangles). Screenshots saved in `test_screenshots/`.

## Critical bugs

### BUG-1: Click-to-place antenna conflicts with orbit controls

**Severity**: High (usability-breaking)
**Observed in**: T3, T7, T11, T16 and user manual testing
**Screenshots**: All screenshots showing antenna repositioned unintentionally

Left-click serves two purposes:
- OrbitControls uses left-click + drag to orbit the camera
- The raycaster uses left-click to place the antenna

Every orbit gesture fires a click event on mouseup, which repositions the antenna. This makes it nearly impossible to orbit the view without also moving the antenna.

**Expected behavior**: Only a stationary click (no mouse movement between mousedown and mouseup) should place the antenna. Orbit drags should not trigger antenna placement.

**Suggested fix**: Track mouse movement delta between mousedown and mouseup. If the cursor moved more than ~3px, treat it as an orbit drag and suppress the antenna placement. Alternatively, require double-click or shift+click for antenna placement.

**Relevant code**: `src/aegis/viewer/templates/index.html` (the click handler on the Three.js canvas that calls the raycaster and `/api/compute` endpoint).

---

### BUG-2: Voxel environment and Sionna scene geometry shown simultaneously

**Severity**: High (visual confusion)
**Observed in**: T14, T14b, T15
**Screenshots**: `test_screenshots/T14_sionna_scene.png`, `test_screenshots/T14b_sionna_rt.png`

When switching the RT source to a Sionna scene (e.g., "double_reflector"), the Sionna geometry (4 triangles) is added to the Three.js scene on top of the existing voxel environment. Both are visible at the same time. The Sionna scene is a completely different coordinate space and scale, so the overlay makes no spatial sense.

**Expected behavior**: When a Sionna scene is selected, the voxel layers should be hidden (or the Sionna geometry should replace them). When switching back to "Voxel environment", voxels should reappear and Sionna geometry should be removed.

**Relevant code**: `src/aegis/viewer/templates/index.html` (the RT source dropdown change handler), `src/aegis/viewer/server.py` (the `/api/rt/scene` endpoint that returns Sionna geometry).

---

### BUG-3: Environment lacks spatial coherence (floating voxels, body at arbitrary position)

**Severity**: High (makes the tool confusing and unprofessional)
**Observed in**: T1, T9 (body hidden reveals environment), T14 (zoomed out), T19
**Screenshots**: `test_screenshots/T9_body_hidden.png` (voxels without body), `test_screenshots/T14_sionna_scene.png` (full voxel environment visible), `test_screenshots/T14b_sionna_rt.png` (body tiny on voxels)

The voxel environment appears as floating Minecraft-like blocks with no ground plane. Vegetation blocks (green) appear to hover in the air. Concrete blocks (gray) form staircase-like structures that don't look like buildings. Thelonious (the body mesh) is placed at what appears to be an arbitrary position and elevation relative to the voxels, sometimes standing on top of voxel blocks, sometimes seemingly floating.

From the default camera angle (T1), the voxels are barely visible. They only become apparent when zoomed out (T14) or when the body is hidden (T9). At the default zoom, it looks like the body is standing in an empty dark void with a faint grid.

This worked better in phase -1 with a different scene/setup. Possible causes:
- The voxel JSON coordinates may use a different datum or elevation reference than the body placement
- The body Z-coordinate (height) may not account for the local terrain elevation from the voxels
- The voxel resolution/size may be too large for this particular tile, making everything look blocky
- The specific voxel tile (`044ddce6...`) may be a poor example (e.g., edge of map, mostly vegetation)

**Relevant code**: `src/aegis/viewer/scene_data.py` (voxel loading, body placement, coordinate transforms), `src/aegis/viewer/templates/index.html` (Three.js scene construction, camera positioning).

---

### BUG-4: Ray tracing paths converge on wrong point (offset from body)

**Severity**: Medium (incorrect physics visualization)
**Observed in**: T14b (Sionna RT with double_reflector)
**Screenshots**: `test_screenshots/T14b_sionna_rt.png`

The RT ray path lines (yellow/orange) converge on a point that does not coincide with the body mesh. The ray target (receiver position sent to DiffeRT) and the body centroid appear to be offset from each other. This means the RT is computing paths to a point that isn't where the body actually is in 3D space.

**Expected behavior**: Ray paths should converge on the body's centroid (or the body's geometric center used as the RX point).

**Possible cause**: The body centroid is computed in AEGIS backend coordinates (Z-up) but the antenna/RX position sent to RT may not go through the same coordinate transform as the body mesh in the Three.js scene (Y-up). Or the body placement offset in `scene_data.py` isn't applied to the RX position used for RT.

**Relevant code**: `src/aegis/viewer/raytracer.py` (RX position), `src/aegis/viewer/compute.py` (body centroid), `src/aegis/viewer/templates/index.html` (ray line visualization, coordinate swaps).

---

## Minor bugs

### BUG-5: Stale RT status text after disabling ray tracing

**Severity**: Low (cosmetic)
**Observed in**: T15
**Screenshots**: `test_screenshots/T15_back_to_normal.png`

After unchecking "Enable ray tracing" and switching back to Voxel environment, the RT status text below the Max reflections dropdown still shows "2 paths (Sionna RT)" from the previous computation. It should be cleared or hidden when RT is disabled.

**Relevant code**: `src/aegis/viewer/templates/index.html` (the RT checkbox change handler should clear the status text element).

---

### BUG-6: Stale ray path visualization lines after disabling RT

**Severity**: Low (cosmetic)
**Observed in**: T15
**Screenshots**: `test_screenshots/T15_back_to_normal.png`

After disabling RT, the ray path lines from the previous Sionna RT computation remain visible as yellow/orange lines in the 3D scene. They should be removed from the Three.js scene when the RT checkbox is unchecked.

**Relevant code**: `src/aegis/viewer/templates/index.html` (the RT checkbox change handler should remove ray line objects from the scene).

---

### BUG-7: Missing favicon

**Severity**: Trivial
**Observed in**: T18 (console errors)

The browser requests `/favicon.ico` and gets a 404. Only console error found.

**Fix**: Add `<link rel="icon" href="data:,">` to the HTML head to suppress the request, or add an actual favicon.

---

## Test results

| Test | Result | Details |
|------|--------|---------|
| T1 - Initial load | PASS | 3D scene loads. Body mesh visible (gray/skin). Voxels barely visible from default angle. Side panel present. |
| T2 - Panel inspection | PASS | All elements present: dashboard (6 stats, all "--"), Parameters (Level 2, 30 dBm, 1 path), Ray tracing section, Layers (concrete 7334, asphalt 11784, vegetation 8721, brick 13, body 23826), Reset camera, Wireframe, hint text. |
| T3 - Place antenna | PASS | Click placed antenna (orange/red line). Dashboard updated: P_abs=0.79 mW, Peak S_ab=0.007 W/m², S_inc=1.24e-2, Distance=2.5 m, Illuminated=10632/23826, Compliance=PASS. Body shows heatmap (purple/green gradient). |
| T4 - Change level | PASS | Level 3 (Fresnel) applied. P_abs changed 0.79 to 0.80 mW (slight increase from Fresnel transmission). No errors. |
| T5 - Change power | PASS | 40 dBm: P_abs=8.01 mW (10x increase from 30 dBm, correct). Peak S_ab=0.067. S_inc=1.24e-1. Compliance still PASS. |
| T6 - Multipath | PASS | 5 paths: P_abs jumped to 18.61 mW. Peak S_ab=0.137. Illuminated increased 10632 to 13668 (more directions = more body coverage). Heatmap shows multiple illumination patches. |
| T7 - New position | PASS | Distance changed 2.5 to 2.9 m. P_abs=15.07 mW (lower, consistent with greater distance). Dashboard updated correctly. |
| T8 - Layer toggle | PASS | Concrete button dimmed when clicked, voxels disappeared. Clicking again restored them. Button appearance toggled correctly. |
| T9 - Body toggle | PASS | Body disappeared, only voxels + antenna line remained. "body" button dimmed. Restoring brought body back. |
| T10 - Wireframe | PASS | Wireframe mode activated. Voxels show wireframe edges. Button highlighted. Toggling back restored solid rendering. |
| T11 - Reset camera | PARTIAL | Programmatic orbit via JS MouseEvent dispatch did not work (Three.js OrbitControls uses PointerEvents, not MouseEvents). Reset camera button itself worked, returning to default view position. |
| T12 - Voxel RT | PASS | RT enabled: "1 paths (voxel RT)". Green ray line visible (LOS). S_inc dropped to 1.18e-6 (weak LOS at this position). Dashboard updated. |
| T13 - RT order 1 | PASS | Max reflections set to 1. Still 1 path (no nearby reflectors at this antenna position). Values unchanged. |
| T14 - Sionna scene | PASS (with BUG-2) | double_reflector loaded ("Loaded: 4 tris"). Camera zoomed out showing full voxel environment. Sionna geometry overlaid on voxels (BUG-2). After clicking: "2 paths (Sionna RT)", yellow ray lines visible. |
| T15 - Back to normal | PASS (with BUG-5, BUG-6) | Switched back to voxel, disabled RT. Stale "2 paths (Sionna RT)" text and stale ray lines remain visible. |
| T16 - Stress test | PASS | 5 rapid clicks in 2.5 seconds. No crash. Final state correct (P_abs=15.37 mW, Distance=2.4 m). |
| T17a - Low power | PASS | 0 dBm: P_abs=0.00 mW, S_inc=1.37e-5. Near-zero as expected. Compliance=PASS. |
| T17b - High power | PASS | 60 dBm: P_abs=1537.45 mW, Peak S_ab=15.038 W/m², S_inc=13.7. Compliance=FAIL (red, >= 10 W/m²). Correct threshold behavior. |
| T18 - Console errors | PASS | Only error: favicon.ico 404. No JS errors. |
| T19 - Final overview | PASS | Default config restored. Scene functional. Body with heatmap, antenna line, voxels visible. Looks like a working dosimetry tool, though environment coherence issues (BUG-3) undermine the visual quality. |

## What works well

- All panel controls respond correctly (level, power, paths dropdowns, RT checkbox)
- Dosimetry physics is correct: 10 dB power increase gives 10x P_abs, multipath increases exposure, Fresnel slightly modifies values, distance affects S_inc via inverse-square
- ICNIRP compliance PASS/FAIL toggles correctly at the 10 W/m² threshold
- Layer visibility toggle works for all material types and body
- Wireframe rendering mode works
- Reset camera returns to default position
- Ray tracing (voxel and Sionna) produces paths and updates dashboard
- Heatmap visualization on body updates with each computation
- Stress test (rapid clicks) handled gracefully with no crashes or JS errors
- App is responsive, computations return in under 1 second (except first voxel RT which caches)
