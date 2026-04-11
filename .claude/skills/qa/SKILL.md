---
name: qa
description: Open the AEGIS viewer and investigate it for bugs
user-invocable: true
---

# /qa - QA the AEGIS viewer

Exercise the AEGIS viewer end-to-end with Playwright CLI. The goal is to test the actual dosimetry pipeline (place antenna, compute, move phantom, load scenes, enable RT), not just click through UI controls.

## Setup

### Local
1. Kill stale processes on the viewer port (default 5000).
2. Start the viewer: `.venv/bin/python -m aegis.viewer` in background.
3. Wait for "Running on http://127.0.0.1:5000" in output.
4. Save screenshots to `test_screenshots/`. Read every screenshot with the Read tool.

### Production
- **URL**: `https://aegis.waves-ugent.be`
- **Auth**: POST `{"password":"WiCa2026#"}` to `/api/auth` first, then use the session cookie for all subsequent requests.
- For Playwright scripts, authenticate by navigating to the URL, filling the password gate, then proceeding with tests.
- For curl, use `-c cookies.txt` to save and `-b cookies.txt` to send cookies.

## Tooling

Work **interactively, step by step**. Do NOT write multi-step .mjs/.js scripts that try to automate an entire flow. Instead, launch a persistent browser and issue one command at a time, reading each screenshot before deciding the next action. This is critical for Three.js/WebGL apps where rendering is async and state-dependent.

### Step-by-step workflow

1. **Launch a persistent browser** with a small inline script that keeps the page open:

```bash
node -e "
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await (await b.newContext({ viewport: { width: 1920, height: 1080 } })).newPage();
  await p.goto('http://127.0.0.1:5000', { waitUntil: 'networkidle' });
  await p.screenshot({ path: 'test_screenshots/step0.png' });
  // Expose page for REPL-style usage via global
  global.page = p; global.browser = b;
  console.log('READY - page open');
  // Keep alive
  await new Promise(() => {});
})();
" &
```

2. **Then issue one action at a time** using separate small `node -e` scripts, each doing ONE thing:

```bash
# Take a screenshot
node -e "... await page.screenshot({ path: 'test_screenshots/step1.png' }) ..."

# Click a button
node -e "... await page.click('text=Load') ..."

# Evaluate JS in browser
node -e "... await page.evaluate(() => { ... }) ..."
```

3. **Read every screenshot** with the Read tool before deciding the next step.

### Alternative approaches

- **Static screenshots**: `npx playwright screenshot --wait-for-timeout 5000 --viewport-size "1920,1080" URL output.png`
- **API checks**: `curl -s http://127.0.0.1:5000/api/endpoint`

### Why not scripts?

Pre-written scripts are fragile: they guess at selectors and timings, cannot react to what actually renders, and fail silently when the UI changes. Interactive step-by-step usage lets you adapt in real time, just like a human tester would.

## How to interact with the 3D scene

R3F (React Three Fiber) uses its own raycaster. Synthetic DOM `click` events do NOT work. You must dispatch paired `PointerEvent`s on the canvas:

```js
// Place antenna - dispatch pointerdown then pointerup at same coords (no drag)
document.querySelector('canvas').dispatchEvent(new PointerEvent('pointerdown',{clientX:X,clientY:Y,bubbles:true,pointerId:1,pointerType:'mouse',button:0}))
document.querySelector('canvas').dispatchEvent(new PointerEvent('pointerup',{clientX:X,clientY:Y,bubbles:true,pointerId:1,pointerType:'mouse',button:0}))
```

- The invisible ClickPlane at y=0 catches clicks even without a loaded scene.
- Click to the RIGHT of the phantom (around clientX=800-1000, clientY=600-700 at 1920x1080) to place an antenna a few meters away.
- After placing, wait 3-5 seconds for the debounced compute to finish.

## Keyboard controls

Dispatch on `document`, not on canvas. Use `eval` via Playwright CLI:

| Key | Action | Code example |
|-----|--------|-------------|
| W/A/S/D | Move phantom | `document.dispatchEvent(new KeyboardEvent('keydown',{key:'w',code:'KeyW',bubbles:true}))` |
| Q/E | Rotate phantom | Same pattern with `key:'q'` or `key:'e'` |
| Space | Jump | `key:' ',code:'Space'` |
| Arrow keys | Nudge antenna (1m steps) | `key:'ArrowUp',code:'ArrowUp'` |
| Shift+Arrow | Nudge antenna (3m steps) | Add `shiftKey:true` |

Always dispatch both `keydown` and `keyup` with a short sleep between. For WASD movement, the physics loop runs while the key is held.

**Antenna must be placed first** before arrow keys do anything.

## What to test (priority order)

### 1. Place antenna and verify dosimetry computes
- Dispatch pointer events on canvas to place antenna
- Verify the phantom shows a heatmap (jet colormap)
- Check the Dosimetry HUD panel shows real values (not `--`)
- Verify compliance status appears (PASS/FAIL badge in header)
- Check the colorbar/legend appears

### 2. Move the phantom with WASD
- Use W/S to move forward/back, A/D to strafe
- Use Q/E to rotate
- Verify dosimetry recomputes (distance changes, heatmap updates)
- Check that the phantom stays on the ground (gravity works)
- Try Focus body button after moving far

### 3. Load a scene and test with environment
- Select a Sionna scene (e.g., "Box") from the dropdown
- Click "Load scene" button
- Verify scene geometry appears
- Place antenna inside the scene
- Check the Layers panel shows "Scene geometry" toggle

### 4. Enable ray tracing
- Expand "Ray Tracing" panel
- Check "Enable ray tracing"
- After loading a scene, verify RT paths appear
- Check that dosimetry values change from non-RT baseline
- Look for RT status info

### 5. Enable stochastic propagation
- Change "Stochastic propagation" dropdown to "5 (light scatter)" or higher
- Verify compute still works
- Check if values change compared to "1 (LOS only)"

### 6. Load voxels via location
- Type a location in the Location field (e.g., "Ghent, Belgium")
- Click "Load"
- Watch for streaming progress
- Verify voxels render as colored cubes
- Test layer toggle buttons per material
- Place antenna and verify dosimetry with voxel environment
- **Requires GOOGLE_API_KEY env var** - skip if not set

### 7. Test quantities and display modes
- Toggle between S_ab (4cm2), S_ab (1cm2) at >30 GHz, S_inc local
- Check SAR_wb checkbox (scalar, no mesh display)
- Switch frequency bands and verify S_ab(1cm2) enables above 30 GHz
- Toggle Occupational vs General Public exposure scenario

### 8. Smoke test remaining UI
- Camera presets (Front, Side, Top, Focus, Reset)
- Wireframe toggle
- Sidebar toggle
- Phantom mesh dropdown (switch between Duke, Ella, etc.)
- TX power dBm/W bidirectional sync
- Skin model dropdown
- Computation mode (Bound/Aggregate/Spatial)

## Reading elements

Use Playwright locators: `page.locator('text=Button')`, `page.locator('select')`, `page.locator('canvas')`. Use `page.evaluate()` for JS execution in the browser context.

After actions that change the scene, wait 2-3 seconds before screenshotting. Always read the screenshot with the Read tool before proceeding.

## Console errors

Register error listeners early: `page.on('console', msg => ...)` and `page.on('pageerror', ...)`. Report all errors found.

## Cleanup

Kill the server process when done: `kill $(lsof -t -i:5000) 2>/dev/null`

## Report format

Report bugs with severity (High/Medium/Low), what you did, what you expected, and what happened. Note what works correctly too.
