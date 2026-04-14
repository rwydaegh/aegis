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

## Tooling: Playwright CLI (MANDATORY)

Use `npx @playwright/cli` for ALL browser interaction. This is a persistent,
stateful CLI -- you open a browser once and issue commands against it. The
browser session stays alive between commands.

**NEVER write `node -e` scripts.** NEVER launch Chromium manually. NEVER use
the Playwright Node.js API. Only use `npx @playwright/cli` commands.

### Workflow

```bash
# 1. Open browser (persistent session, stays alive)
npx @playwright/cli open https://aegis.waves-ugent.be
npx @playwright/cli resize 1920 1080

# 2. Authenticate
npx @playwright/cli fill 'input[type="password"]' 'WiCa2026#'
npx @playwright/cli click 'button[type="submit"]'
npx @playwright/cli screenshot /tmp/qa_screenshots/step01.png
# Read the screenshot with Read tool, then decide next action

# 3. Interact one command at a time
npx @playwright/cli click 'text=Load'
npx @playwright/cli screenshot /tmp/qa_screenshots/step02.png
# Read screenshot, decide next action...

# 4. Done
npx @playwright/cli close
```

### Key commands

| Command | Example |
|---------|---------|
| Open browser | `npx @playwright/cli open <url>` |
| Screenshot | `npx @playwright/cli screenshot /tmp/qa_screenshots/stepNN.png` |
| Click | `npx @playwright/cli click 'text=Button'` or `npx @playwright/cli click eNN` |
| Type | `npx @playwright/cli fill 'input' 'text'` |
| Evaluate JS | `npx @playwright/cli eval "document.querySelector('canvas')..."` |
| Snapshot (a11y tree) | `npx @playwright/cli snapshot` |
| Press key | `npx @playwright/cli press Shift+b` |
| Key down/up | `npx @playwright/cli keydown w` then `npx @playwright/cli keyup w` |
| Mouse events | `npx @playwright/cli mousedown` / `npx @playwright/cli mouseup` |
| Move mouse | `npx @playwright/cli mousemove 900 650` |
| Console | `npx @playwright/cli console` |
| Close | `npx @playwright/cli close` |

### Why CLI, not scripts?

Each `npx @playwright/cli` command runs against the SAME persistent browser.
No re-launching, no re-authenticating, no sleep-polling. A 15-step test takes
minutes, not hours.

## How to interact with the 3D scene

R3F (React Three Fiber) uses its own raycaster. Standard DOM `click` does NOT
work on the canvas. Use mouse events via `eval` or the CLI mouse commands:

```bash
# Place antenna - move mouse to position, then mousedown + mouseup
npx @playwright/cli mousemove 900 650
npx @playwright/cli mousedown
npx @playwright/cli mouseup
```

Or via eval for PointerEvents (more reliable for R3F):

```bash
npx @playwright/cli eval "document.querySelector('canvas').dispatchEvent(new PointerEvent('pointerdown',{clientX:900,clientY:650,bubbles:true,pointerId:1,pointerType:'mouse',button:0}))"
npx @playwright/cli eval "document.querySelector('canvas').dispatchEvent(new PointerEvent('pointerup',{clientX:900,clientY:650,bubbles:true,pointerId:1,pointerType:'mouse',button:0}))"
```

- Click to the RIGHT of the phantom (clientX=800-1000, clientY=600-700) to place an antenna.
- After placing, wait 3-5 seconds for the debounced compute, then screenshot.

## Keyboard controls

Use the CLI `press`, `keydown`, and `keyup` commands:

```bash
# Press a key (down + up)
npx @playwright/cli press w

# Hold a key (for WASD movement -- physics runs while held)
npx @playwright/cli keydown w
sleep 1
npx @playwright/cli keyup w

# Shift+B for bug reporter
npx @playwright/cli press Shift+b

# Arrow keys to nudge antenna
npx @playwright/cli press ArrowUp
```

| Key | Action |
|-----|--------|
| W/A/S/D | Move phantom |
| Q/E | Rotate phantom |
| Arrow keys | Nudge antenna (1m) |
| Shift+Arrow | Nudge antenna (3m) |
| Shift+B | Open bug reporter |
| ? | Keyboard help |

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

### 8. Bug reporter and help overlays
- Press Shift+B to open the bug reporter modal
- Verify the modal appears with a screenshot preview and annotation canvas
- Draw on the screenshot (freehand red pen), try undo and clear
- Type a description, verify Cmd+Enter hint is visible
- Close without submitting (Escape or Cancel button)
- Press ? to open keyboard help modal, verify shortcuts listed

### 9. Smoke test remaining UI
- Camera presets (Front, Side, Top, Focus, Reset)
- Wireframe toggle
- Sidebar toggle
- Phantom mesh dropdown (switch between Duke, Ella, etc.)
- TX power dBm/W bidirectional sync
- Skin model dropdown
- Computation mode (Bound/Aggregate/Spatial)

## Reading elements

Use `npx @playwright/cli snapshot` to get the accessibility tree with element refs
(eNN). Then click/fill/select by ref: `npx @playwright/cli click e42`.

After actions that change the scene, wait 2-3 seconds before screenshotting.
Always read each screenshot with the Read tool before deciding the next action.

## Console errors

Check browser console periodically:
```bash
npx @playwright/cli console
```

## Cleanup

```bash
npx @playwright/cli close
```

## Report format

Report bugs with severity (High/Medium/Low), what you did, what you expected, and what happened. Note what works correctly too.
