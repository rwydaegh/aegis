# Plan: Location-based voxel loading in the AEGIS viewer

## Context

The viewer currently loads a single voxel JSON file (one Google Earth 3D tile fragment), which appears as a disconnected floating rock. The Voxel Earth Node.js pipeline (`../nodejs-voxelearth/`) can download and voxelize all tiles for a given location and radius, producing multiple JSON files. This plan adds a location input to the viewer that calls the pipeline and loads all resulting tiles into a coherent scene.

## Architecture

```
[UI: location input + radius]
    -> [SSE: /api/location/load]
    -> [Python subprocess: node run_pipeline.js --location "Ghent" --radius 50]
    -> [Progress lines streamed back via SSE]
    -> [load_voxels_directory() merges all output JSONs]
    -> [Frontend reloads voxels via /api/voxels]
```

## Steps

### 1. Multi-file voxel loading (`scene_data.py`)

Add `load_voxels_directory(dir_path, max_voxels=60000)` that:
- Globs `*_voxels.json` in the directory
- Parses each file, extracts `wx/wy/wz` world coords and `r/g/b` colors
- Concatenates into combined arrays
- Applies ECEF-to-ENU conversion on the merged set (existing code path)
- Runs exterior filtering on combined grid coords (offset each tile's grid by worldOffset/unit to get global grid)
- Subsamples if over max_voxels
- Returns same `(positions, colors, materials)` tuple as `load_voxels`

Refactor the ECEF-to-ENU + centering + material classification logic into a shared helper used by both `load_voxels` and `load_voxels_directory`.

### 2. Pipeline runner (`src/aegis/viewer/pipeline.py`, new file)

```python
def find_pipeline() -> Path | None
def run_pipeline(location, radius, api_key, output_dir, resolution=200) -> Generator[str]
def cancel_pipeline() -> bool
```

- Locates `run_pipeline.js` via `VOXELEARTH_DIR` env var or auto-detect (`../../nodejs-voxelearth` relative to repo)
- Runs as `subprocess.Popen` with `stdout=PIPE, stderr=STDOUT, text=True`
- Yields each stdout line for progress streaming
- Module-level `_active_process` for cancellation
- Cache convention: `<cache_dir>/<slug>_r<radius>/voxels/` where slug = sanitized location string

### 3. Server endpoints (`server.py`)

**`GET /api/location/load?location=...&radius=...&force=false`** (SSE)
- Returns `Content-Type: text/event-stream`
- Checks cache first (skip pipeline if cached and not force)
- Streams pipeline progress as `event: progress` SSE messages
- On completion: loads voxels via `load_voxels_directory()`, updates `_cache`
- Sends `event: done` with voxel metadata
- On error: sends `event: error`

**`POST /api/location/cancel`**
- Kills running pipeline subprocess

**Update `/api/config`**
- Add `has_location_loader`, `has_api_key` fields
- Frontend uses these to show/hide the location section

### 4. Frontend UI (`index.html`)

Add a "Location" section to the panel (visible only if pipeline is available):
- Text input for location (placeholder: "e.g. Ghent, Belgium")
- Number input for radius (default 30m, range 10-500)
- "Load" button, "Cancel" button (shown during loading)
- Progress log div (scrollable, shows pipeline output lines)
- "Force re-download" checkbox

JavaScript:
- `loadLocation()`: opens `EventSource` to SSE endpoint, streams progress
- `reloadVoxels()`: removes old voxel meshes from Three.js scene, fetches `/api/voxels`, rebuilds InstancedMesh groups, rebuilds layer buttons
- Cancel button calls `POST /api/location/cancel`

### 5. CLI updates (`__main__.py`)

New args:
- `--voxel-dir` - load all voxel JSONs from a directory (alternative to `--voxel-json`)
- `--pipeline-dir` - path to nodejs-voxelearth (default: auto-detect)
- `--cache-dir` - pipeline output cache (default: `<pipeline-dir>/pipeline_cache`)

### 6. API key handling

- Read from `GOOGLE_API_KEY` environment variable
- If missing: location section is hidden, rest of viewer works normally
- No .env file (to avoid accidental commits)

## Files to modify

| File | Change |
|------|--------|
| `src/aegis/viewer/scene_data.py` | Add `load_voxels_directory()`, refactor shared helpers |
| `src/aegis/viewer/pipeline.py` | **New file**: pipeline runner, cache logic |
| `src/aegis/viewer/server.py` | Add SSE endpoint, cancel endpoint, update config |
| `src/aegis/viewer/templates/index.html` | Location UI, SSE client, voxel reload |
| `src/aegis/viewer/__main__.py` | New CLI args |

## Verification

1. Start viewer without API key: location section should be hidden, rest works
2. Start viewer with `--voxel-dir` pointing to `pipeline_output/voxels/`: should load all 55 tiles into a merged scene
3. Set `GOOGLE_API_KEY`, start viewer: location section visible
4. Type "Eiffel Tower, Paris", radius 30, click Load: progress streams, voxels appear
5. Type a different location: old voxels replaced with new ones
6. Cancel button kills pipeline mid-download
7. Re-loading same location uses cache (fast), "Force re-download" bypasses cache
8. Test with Playwright MCP: navigate, check UI elements, verify dashboard still works after voxel reload
