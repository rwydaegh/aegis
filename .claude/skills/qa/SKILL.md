---
name: qa
description: QA test the AEGIS viewer and backend using Playwright CLI screenshots and pytest
user-invocable: true
---

# /qa - QA testing for AEGIS

Test AEGIS features by launching the viewer, taking screenshots with Playwright CLI, running backend tests, and reporting findings.

## Usage

```
/qa                          # full viewer QA (all test groups)
/qa viewer                   # viewer-only QA
/qa backend                  # backend-only (pytest + physics checks)
/qa <specific thing>         # targeted test (e.g., "ray tracing", "WASD movement", "compliance threshold")
```

## Important rules

- Use `npx @playwright/cli` for all browser interaction. NOT the Playwright MCP server.
- Save all screenshots to `test_screenshots/` with descriptive names.
- Read every screenshot you take with the Read tool. You are a multimodal LLM. Look at what is on screen, describe it, and flag anything wrong.
- When testing the viewer, always start the server first and wait for it to be ready.
- When the user asks you to test something non-frontend (backend, physics, a script), skip the browser entirely and use pytest or direct Python execution.
- After each test group, report: what passed, what failed, and what looks off visually.

## Server lifecycle

### Starting the server

```bash
# Kill any stale viewer on the port
netstat -aon | grep ":5070.*LISTENING"
# If a PID shows, kill it: taskkill /F /PID <pid>

# Start the viewer in background
py -3.12 -m aegis.viewer --port 5070 --no-open --voxel-json "../nodejs-voxelearth/pipeline_output/voxels/044ddce6e59286f561b4c89aeba53e386d3615ee_voxels.json" 2>&1 | head -5 &
sleep 20
```

Wait until the server is confirmed listening on port 5070 before opening the browser.

If no voxel data is available, start without it:
```bash
py -3.12 -m aegis.viewer --port 5070 --no-open 2>&1 | head -5 &
sleep 15
```

### Opening the browser

```bash
npx @playwright/cli open http://127.0.0.1:5070 --headed
```

Wait 5-10 seconds after open for Three.js to load body mesh and voxels before taking the first screenshot.

### Closing

```bash
npx @playwright/cli close
```

Then kill the server process on port 5070 when done.

## Playwright CLI reference

These are the commands you have. Use them in this order for each test step.

| Command | What it does |
|---------|-------------|
| `npx @playwright/cli open <url> --headed` | Launch browser to URL |
| `npx @playwright/cli screenshot --filename=test_screenshots/<name>.png` | Capture viewport |
| `npx @playwright/cli snapshot` | Get YAML accessibility snapshot with element refs |
| `npx @playwright/cli click <ref>` | Click an element by ref from snapshot |
| `npx @playwright/cli fill <ref> <value>` | Type into an input field |
| `npx @playwright/cli select <ref> <value>` | Select dropdown option |
| `npx @playwright/cli hover <ref>` | Hover over element |
| `npx @playwright/cli press <key>` | Press a keyboard key (e.g., "w", "ArrowUp", "Space") |
| `npx @playwright/cli console` | Get browser console messages (check for JS errors) |
| `npx @playwright/cli close` | Close browser |

Tips:
- After every action that changes the scene, wait 2-3 seconds, then screenshot.
- Use `snapshot` to find element refs before clicking. The ref format is from the YAML output.
- For WASD movement, use `press` with the key name (e.g., `press w` several times).
- For keyboard shortcuts, hold keys with `press Shift+w` syntax.

## Test groups

### Group 1: Initial load and scene

1. Open viewer URL, wait 10 seconds
2. Screenshot `T_initial_load.png`
3. Check: 3D scene visible? Body mesh rendered? Voxels present? Side panel on left?
4. Snapshot the side panel, verify: dashboard stats ("--"), level dropdown, power input, path selector, RT section, layer buttons, camera buttons

### Group 2: Dosimetry computation

1. Click on the 3D scene to place antenna (use snapshot to find the canvas, click center area)
2. Wait 3s, screenshot `T_antenna_placed.png`
3. Check: antenna marker appeared? Dashboard updated from "--" to real numbers? Body has heatmap colors?
4. Read P_abs, Peak Sab, S_inc, Distance, Illuminated count, Compliance from the panel
5. Change level to Level 3 (Fresnel) via dropdown. Screenshot `T_level3.png`. P_abs should change slightly.
6. Change power to 40 dBm. Screenshot `T_power40.png`. P_abs should be ~10x higher.
7. Change paths to 5. Screenshot `T_multipath.png`. More illuminated triangles expected.

### Group 3: Body movement (WASD)

1. Press "w" key 5 times (body walks forward)
2. Wait 2s for recompute, screenshot `T_wasd_forward.png`
3. Check: body moved in scene? Dashboard distance changed? Heatmap updated?
4. Press "a" key 3 times (strafe left), screenshot `T_wasd_left.png`
5. Press "q" key 3 times (rotate), screenshot `T_rotate.png`
6. Press Space (jump), screenshot immediately `T_jump.png`

### Group 4: Antenna nudge (arrow keys)

1. Press ArrowRight 3 times
2. Wait 2s, screenshot `T_antenna_nudge.png`
3. Check: distance line changed direction? Dashboard distance updated?

### Group 5: Camera controls

1. Click "Front" camera button, screenshot `T_cam_front.png`
2. Click "Side" button, screenshot `T_cam_side.png`
3. Click "Top" button, screenshot `T_cam_top.png`
4. Click "Focus" button, screenshot `T_cam_focus.png`
5. Click "Reset" button, screenshot `T_cam_reset.png`

### Group 6: Layer toggles

1. Click concrete layer button to hide, screenshot `T_layer_concrete_off.png`
2. Click body layer button to hide, screenshot `T_body_hidden.png`
3. Restore both, screenshot `T_layers_restored.png`

### Group 7: Wireframe

1. Click Wireframe button, screenshot `T_wireframe.png`
2. Click again to restore

### Group 8: Ray tracing

1. Enable RT checkbox
2. Verify source is "Voxel environment"
3. Click scene to trigger RT computation
4. Wait 20 seconds (first call is slow, builds mesh)
5. Screenshot `T_voxel_rt.png`
6. Check: RT status shows path count? Ray path lines visible?
7. Change max order to 1, click again, wait 15s, screenshot `T_rt_order1.png`

### Group 9: Sionna scenes

1. Select a Sionna scene from RT source dropdown
2. Wait 5s, screenshot `T_sionna_loaded.png`
3. Click to compute RT, wait 10s, screenshot `T_sionna_rt.png`
4. Check: Sionna geometry visible? Ray paths shown? (Note BUG-2: voxels may overlap)
5. Switch back to voxel, disable RT

### Group 10: Compliance threshold

1. Set power to 0 dBm, click scene, wait 2s, screenshot `T_low_power.png`
2. Check: near-zero Sab, compliance PASS
3. Set power to 60 dBm, click scene, wait 2s, screenshot `T_high_power.png`
4. Check: high Sab, compliance FAIL (red)
5. Restore to 30 dBm

### Group 11: Stress and edge cases

1. Click 5 positions rapidly (0.5s apart), wait 5s, screenshot `T_stress.png`
2. Check: no crash, final state valid
3. Check browser console for JS errors: `npx @playwright/cli console`

### Group 12: Color legend

1. After computation, screenshot right side of viewport `T_legend.png`
2. Check: Inferno gradient visible? Min/max values shown?

## Backend-only tests

When the user asks you to test backend or physics (no browser needed):

```bash
# Fast tests (should take ~5s, all must pass)
py -3.12 -m pytest tests/ -m "not slow" -x -v

# Mie regression (CI canary, the most important single test)
py -3.12 -m pytest tests/test_mie.py -v

# Golden table values (monograph validation)
py -3.12 -m pytest tests/golden/ -v

# Property tests (Hypothesis, physics invariants)
py -3.12 -m pytest tests/test_properties.py -v

# All tests including slow mesh-dependent ones
py -3.12 -m pytest tests/ -v

# Lint and format check
py -3.12 -m ruff check src/ tests/
py -3.12 -m ruff format --check src/ tests/
```

Report: number passed, number failed, any unexpected output. For failures, show the assertion and traceback.

## Targeted testing

When the user asks to test a specific feature (e.g., "test the Fresnel coefficients"):

1. Identify which test file covers it (check `tests/` and `tests/golden/`)
2. Run that specific test with `-v`
3. If it is a viewer feature, start the server and use Playwright to exercise just that feature
4. If it is a computation, write a quick Python snippet to verify (e.g., `py -3.12 -c "from aegis.tissue.fresnel import ...; print(...)"`)

## Reporting format

After running tests, report like this:

```
## QA results

### Passed
- [item]: [one-line description of what was verified]

### Failed
- [item]: [what went wrong, screenshot reference]

### Visual issues
- [item]: [description of what looks off, screenshot reference]

### Console errors
- [list any JS errors found, or "None"]
```

## Known bugs to watch for

These are documented bugs. Note if they are still present or if they have been fixed.

- BUG-1: Orbit drag triggers antenna placement (high severity)
- BUG-2: Sionna geometry overlaps voxel environment
- BUG-3: Floating voxels, body at arbitrary elevation
- BUG-4: RT ray paths converge on wrong point (offset from body)
- BUG-5: Stale RT status text after disabling
- BUG-6: Stale ray path lines after disabling RT
- BUG-7: Missing favicon (trivial)

## Architecture reference (for debugging)

- Server: `src/aegis/viewer/server.py` (Flask, 12 endpoints)
- Frontend: `src/aegis/viewer/templates/index.html` (Three.js SPA, ~1400 lines)
- Compute: `src/aegis/viewer/compute.py` (dosimetry wrapper)
- Scene data: `src/aegis/viewer/scene_data.py` (binary mesh/voxel serialization)
- Ray tracer: `src/aegis/viewer/raytracer.py` (DiffeRT bridge)
- CLI entry: `src/aegis/viewer/__main__.py`
- Coordinate system: Three.js is Y-up, AEGIS backend is Z-up (swaps happen in JS)
