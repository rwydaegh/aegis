---
paths: ["src/aegis/viewer/**"]
description: Viewer-specific rules for the Flask + Three.js 3D frontend
---

# Viewer rules

## Coordinate systems

- Python/AEGIS: Z-up
- Three.js/JavaScript: Y-up
- The swap happens in `scene_data.py` during binary serialization
- Never mix conventions. If you touch coordinate transforms, verify both sides.

## Server lifecycle

- Always kill existing processes on the viewer port before launching a new server
- Check with: `netstat -aon | grep ":5070.*LISTENING"`
- Kill with: `taskkill /F /PID <pid>`
- Start server in background, wait 15-20 seconds before opening browser

## Architecture

- Config: `src/aegis/viewer/config.py` (DEFAULTS dict, deep-merge loader)
- Server: `src/aegis/viewer/server.py` (Flask, 13 endpoints incl `/api/viewer-config`)
- Frontend: `src/aegis/viewer/templates/index.html` (Three.js SPA, reads `CFG` global)
- Compute: `src/aegis/viewer/compute.py` (dosimetry wrapper, accepts `config` kwarg)
- Scene data: `src/aegis/viewer/scene_data.py` (binary serialization, uses `set_config()`)
- Ray tracer: `src/aegis/viewer/raytracer.py` (DiffeRT bridge)
- CLI entry: `src/aegis/viewer/__main__.py` (accepts `--config` flag)
- Default config: `configs/default.json` (generated from Python defaults)

## Configuration

- All viewer constants live in `config.py` DEFAULTS. No hardcoded values elsewhere.
- User configs in `configs/` deep-merge over defaults (only override what you need).
- Launch: `py -3.12 -m aegis.viewer --config configs/my_scene.json`
- Frontend gets config as `CFG` global via Jinja2 template injection.
- When adding new values: add to DEFAULTS in config.py, regenerate default.json.
- Never add hardcoded constants to other viewer files. Put them in config.py DEFAULTS.

## Known bugs

- BUG-1: Orbit drag triggers antenna placement (high severity)
- BUG-2: Sionna geometry overlaps voxel environment
- BUG-3: Floating voxels, body at arbitrary elevation
- BUG-4: RT ray paths converge on wrong point (offset from body)
- BUG-5: Stale RT status text after disabling
- BUG-6: Stale ray path lines after disabling RT
- BUG-7: Missing favicon (trivial)

## Testing

Use `npx @playwright/cli` for all browser interaction, NOT the Playwright MCP server. Save screenshots to `test_screenshots/`. Read every screenshot with the Read tool.
