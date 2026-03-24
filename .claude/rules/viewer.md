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

- Always kill existing processes on the viewer port before launching a new server (default **5000** from config; `__main__.py` can kill stale listeners on Windows).
- Check with: `netstat -aon` (Windows) or `ss -lntp` (Linux) for the configured port.
- Start the server, then open the URL printed in the console.

## Architecture

- Config: `src/aegis/viewer/config.py` (DEFAULTS dict, deep-merge loader)
- Server: `src/aegis/viewer/server.py` (Flask, 13 endpoints incl `/api/viewer-config`)
- Frontend: `src/aegis/viewer/templates/index.html` (Three.js SPA, reads `CFG` global)
- Compute: `src/aegis/viewer/compute.py` (dosimetry wrapper, accepts `config` kwarg)
- Scene data: `src/aegis/viewer/scene_data.py` (binary serialization, uses `set_config()`)
- Ray tracer: `src/aegis/viewer/raytracer.py` (DiffeRT bridge)
- CLI entry: `src/aegis/viewer/__main__.py` (`--config`, `--scenario`, voxel/location flags)
- Default config: `configs/default.json` merged over `config.py` defaults; scenarios in `configs/README.md`

## Configuration

- All viewer constants live in `config.py` DEFAULTS. No hardcoded values elsewhere.
- User configs in `configs/` deep-merge over defaults (only override what you need).
- Launch: `python -m aegis.viewer --config configs/my_scene.json`
- Frontend gets config as `CFG` global via Jinja2 template injection.
- When adding new values: add to DEFAULTS in config.py, regenerate default.json.
- Never add hardcoded constants to other viewer files. Put them in config.py DEFAULTS.

## Known issues and QA

Track viewer behavior against `docs/internal/viewer_bug_report.md` and `docs/internal/features.md`. Several older UI items there have been fixed (drag threshold, Sionna voxel hiding, RT teardown, favicon). Prefer exercising current `index.html` and server routes before copying bug text into new issues.

## Testing

Use `npx @playwright/cli` for all browser interaction, NOT the Playwright MCP server. Save screenshots to `test_screenshots/`. Read every screenshot with the Read tool.
