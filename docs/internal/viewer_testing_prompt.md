# Viewer testing prompt (for Playwright MCP agent)

## How to use

1. Start the AEGIS viewer server
2. Give the prompt in "Test sequence" below to a Claude Code agent that has the Playwright MCP tools loaded
3. Review the screenshots it captures

## Starting the server

```bash
cd "c:\Users\rwydaegh\OneDrive - UGent\rwydaegh\Geometric Dosimetry\aegis"
py -3.12 -m aegis.viewer --no-open --voxel-json "../nodejs-voxelearth/pipeline_output/voxels/044ddce6e59286f561b4c89aeba53e386d3615ee_voxels.json" --max-voxels 30000 --port 5070
```

Wait until "Running on http://127.0.0.1:5070" appears.

## Test sequence

You are testing the AEGIS interactive 3D dosimetry viewer at `http://127.0.0.1:5070`. Use the Playwright MCP tools to navigate, click, interact, and take screenshots. Save every screenshot to the `test_screenshots/` folder.

**Goal**: Click through every feature, verify it works visually, report what you see, and flag any issues (broken UI, errors, missing data, visual glitches).

### T1 - Initial load

1. Navigate to `http://127.0.0.1:5070`
2. Wait 10 seconds for Three.js to load body mesh + voxels
3. Take a screenshot -> `test_screenshots/T1_initial_load.png`
4. Report: Do you see a 3D scene? Is there a human body (orange/skin colored mesh)? Are there colored voxel boxes (buildings, streets)? Is the side panel visible on the left?

### T2 - Side panel inspection

1. Look at the left panel. It should have:
   - A dashboard section with stats (P_abs, Peak S_ab, S_inc, Distance, Illuminated, Compliance) all showing "--"
   - A "Controls" section with Level dropdown (default Level 2), Power input (default 30 dBm), Paths dropdown (default 1)
   - A "Ray tracing" section with an Enable checkbox, Source dropdown, Max order dropdown
   - A "Layers" section with colored toggle buttons for materials (concrete, asphalt, vegetation, etc.) and "body"
   - "Reset camera" and "Wireframe" buttons
   - Hint text at the bottom
2. Take screenshot -> `test_screenshots/T2_panel.png`
3. Report: Which elements are present? Any missing?

### T3 - Place antenna (click on ground/voxels)

1. Click somewhere in the 3D scene area (roughly center of viewport, around coordinates x=700, y=450)
2. Wait 3 seconds for computation
3. Take screenshot -> `test_screenshots/T3_antenna_placed.png`
4. Report: Did an antenna appear (small colored sphere/cone)? Did the dashboard update from "--" to actual numbers? What values show for P_abs, Peak S_ab, Compliance? Did the body mesh change color (heatmap)?

### T4 - Change fidelity level

1. Click/select the Level dropdown (`#levelSelect`) and change to "Level 3 - Fresnel"
2. Wait 2 seconds
3. Take screenshot -> `test_screenshots/T4_level3.png`
4. Report: Did dashboard values change? Any errors?

### T5 - Change TX power

1. Click the power input (`#powerInput`), clear it, type "40", press Enter
2. Wait 2 seconds
3. Take screenshot -> `test_screenshots/T5_power40.png`
4. Report: Did P_abs increase (more power = more absorbed)? What's the compliance status now?

### T6 - Switch to multipath

1. Select "5 (multipath)" from the Paths dropdown (`#pathsSelect`)
2. Wait 2 seconds
3. Take screenshot -> `test_screenshots/T6_multipath.png`
4. Report: Did values change? Any visual difference in the heatmap pattern?

### T7 - Click different antenna position

1. Click a different spot in the 3D scene (e.g., x=500, y=350)
2. Wait 3 seconds
3. Take screenshot -> `test_screenshots/T7_new_position.png`
4. Report: Did antenna move? Did heatmap update? Did dashboard show different distance?

### T8 - Toggle layer visibility

1. Find the layer buttons in the Layers section
2. Click the first material layer button (e.g., "concrete") to hide it
3. Wait 1 second
4. Take screenshot -> `test_screenshots/T8_layer_hidden.png`
5. Report: Did a group of voxels disappear? Did the button change appearance (active->inactive)?
6. Click it again to show them
7. Take screenshot -> `test_screenshots/T8b_layer_restored.png`

### T9 - Toggle body visibility

1. Find and click the "body" layer button
2. Wait 1 second
3. Take screenshot -> `test_screenshots/T9_body_hidden.png`
4. Report: Did the human body disappear, leaving only voxels?
5. Click it again to restore

### T10 - Wireframe mode

1. Click the "Wireframe" button
2. Wait 1 second
3. Take screenshot -> `test_screenshots/T10_wireframe.png`
4. Report: Did the body and/or voxels switch to wireframe rendering?
5. Click again to restore solid rendering

### T11 - Reset camera

1. First, use mouse to orbit/rotate the view (drag on the 3D scene)
2. Take screenshot -> `test_screenshots/T11a_rotated.png`
3. Click "Reset camera" button
4. Wait 1 second
5. Take screenshot -> `test_screenshots/T11b_reset.png`
6. Report: Did the camera return to default position?

### T12 - Enable ray tracing (voxel mode)

1. Check the "Enable ray tracing" checkbox (`#rtEnabled`)
2. Verify the Source dropdown shows "Voxel environment"
3. Click on the 3D scene to place antenna and trigger RT
4. Wait 20 seconds (first voxel RT call builds mesh, is slow)
5. Take screenshot -> `test_screenshots/T12_voxel_rt.png`
6. Report: Did the RT status text update? Do you see colored lines showing ray paths from antenna to body? Did dashboard values change?

### T13 - Change max RT order

1. With RT still enabled, change Max order dropdown to "1" (one reflection)
2. Click the scene again
3. Wait 15 seconds
4. Take screenshot -> `test_screenshots/T13_rt_order1.png`
5. Report: Are there more path lines now (reflected paths)? Did path count change in RT status?

### T14 - Switch to Sionna scene

1. Open the RT Source dropdown (`#rtSourceSelect`)
2. Select one of the Sionna scene options (should see names like "double_reflector (Sionna)")
3. Wait 5 seconds
4. Take screenshot -> `test_screenshots/T14_sionna_scene.png`
5. Report: Did new geometry appear in the scene? Is it visibly different from the voxels?
6. Click the scene to compute RT with the Sionna geometry
7. Wait 10 seconds
8. Take screenshot -> `test_screenshots/T14b_sionna_rt.png`
9. Report: Do you see path lines? What does RT status show?

### T15 - Switch back to voxel environment

1. Change RT Source back to "Voxel environment"
2. Uncheck "Enable ray tracing"
3. Take screenshot -> `test_screenshots/T15_back_to_normal.png`

### T16 - Stress test: rapid clicks

1. Click 5 different positions on the scene rapidly (0.5s apart)
2. Wait 5 seconds for final computation to settle
3. Take screenshot -> `test_screenshots/T16_stress.png`
4. Report: Did it crash? Does the final state look correct?

### T17 - Edge cases

1. Set power to 0 dBm, click scene, wait 2s
2. Take screenshot -> `test_screenshots/T17a_low_power.png`
3. Set power to 60 dBm, click scene, wait 2s
4. Take screenshot -> `test_screenshots/T17b_high_power.png`
5. Report: Does low power show near-zero S_ab? Does high power show higher values? Compliance should flip between PASS and FAIL.

### T18 - Check for console errors

1. Check the browser console for any JavaScript errors
2. Report: List any errors found (ignore favicon warnings)

### T19 - Final overview

1. Set a reasonable config: Level 2, 30 dBm, 1 path, RT disabled
2. Click center of scene
3. Wait 3 seconds
4. Zoom out to show the full scene (scroll wheel or orbit)
5. Take screenshot -> `test_screenshots/T19_final_overview.png`
6. Report: Overall visual impression. Does it look like a real dosimetry tool?

## After testing

Review all screenshots in `test_screenshots/` and compile a bug list:
- UI elements that are missing or broken
- API endpoints that return errors
- Visual glitches (wrong colors, missing geometry, layout issues)
- Performance issues (slow responses, freezing)
- Console JS errors

## Viewer architecture reference

- `src/aegis/viewer/server.py` - Flask API (8 endpoints)
- `src/aegis/viewer/templates/index.html` - Three.js UI (795 lines)
- `src/aegis/viewer/compute.py` - Dosimetry kernel
- `src/aegis/viewer/scene_data.py` - Mesh/voxel loading
- `src/aegis/viewer/raytracer.py` - DiffeRT integration
- `src/aegis/viewer/__main__.py` - CLI entry point
- `.mcp.json` - Playwright + Three.js MCP config

## Known issues

1. Level 0 compute fails (needs `A_ab` and `D_max` params not provided by UI)
2. First voxel RT call is slow (~15s) due to mesh construction, subsequent calls use cache
3. Coordinate system: Three.js is Y-up, AEGIS backend is Z-up (swaps happen in JS)
