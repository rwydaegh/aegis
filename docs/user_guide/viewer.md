# Interactive 3D viewer

The viewer is a Flask server plus a Three.js single-page app. It shows a body mesh, optional voxel environment, and real-time dosimetry after you place a transmit antenna.

## Requirements

- Python 3.12 with AEGIS installed (`pip install -e ".[dev]"`).
- Body STL under your [data directory](../getting_started.md#loading-real-meshes) (default mesh name `thelonious` unless you override it).
- Optional: `pip install -e ".[rt]"` for DiffeRT (voxel or Sionna ray tracing in the UI).
- Optional: location pipeline and `GOOGLE_API_KEY` for geocoded voxel fetch (see [location loading plan](../internal/plan_location_loading.md)).

## Launch

Default HTTP port is **5000** (from `configs/default.json` or `config.py` defaults).

```bash
py -3.12 -m aegis.viewer
```

Common flags:

| Flag | Purpose |
|------|---------|
| `--config path.json` | Merge JSON over built-in defaults (see `configs/default.json`). |
| `--scenario name` | Apply a named scenario from the config file (overrides `default_scenario`). |
| `--no-open` | Do not open a browser tab. |
| `--voxel-dir`, `--voxel-json` | Load voxel data from disk. |
| `--location "City"` | Fetch voxels via the Node pipeline when configured. |
| `--body name` | STL stem under the data directory. |
| `--bbox meters` | Scene bounding box size (affects voxel loading radius). |

Example:

```bash
py -3.12 -m aegis.viewer --config configs/default.json --scenario open_ground --no-open
```

The console prints the URL (usually `http://127.0.0.1:5000`).

## Configuration and scenarios

Viewer constants are defined in `src/aegis/viewer/config.py` and merged with your JSON. The repo ships `configs/default.json` plus [configs/README.md](../../configs/README.md) for the schema.

**Scenarios** group launch inputs so runs are repeatable:

- `default_scenario` in JSON selects a scenario when you do not pass `--scenario`.
- Each scenario has a `description` and a `launch` object (`voxel_dir`, `voxel_json`, `body`, `bbox`, `data_dir`). CLI arguments override the scenario after merge.

The built-in `open_ground` scenario clears voxel paths so you get the body on the ground plane only (synthetic multipath still works in the API).

The UI shows the active scenario name and description when the server injects `active_scenario` (set automatically from the CLI resolution).

## API overview

The browser calls REST endpoints such as:

- `GET /api/config` – bodies list, whether voxels and DiffeRT are available, Sionna scene list, compliance-related flags.
- `GET /api/body`, `GET /api/voxels` – binary mesh and voxel payloads with metadata headers.
- `POST /api/compute` – synthetic multipath dosimetry (levels 0–6 in the panel).
- `POST /api/compute/voxel-rt`, `POST /api/compute/rt` – ray-traced paths when DiffeRT and data are available.

`voxel_rt_available` in `/api/config` is true only when voxel grid data is loaded **and** DiffeRT is importable, so the UI does not offer voxel ray tracing when it would always fail.

## Coordinates

AEGIS uses **Z-up** in Python; the Three.js client uses **Y-up**. Swaps are applied when serializing body and scene binaries. If you change transforms, verify both the Flask handlers and `index.html` stay consistent.

## QA and known limitations

Manual and automated checks are described in [viewer testing prompt](../internal/viewer_testing_prompt.md) and the [viewer bug report](../internal/viewer_bug_report.md). Treat internal notes as living documents: several older entries have been fixed in code. Prefer the current source for behavior.

## See also

- [Architecture](../developer_guide/architecture.md) – module layout including `src/aegis/viewer/`.
- [Testing](../developer_guide/testing.md) – pytest and marks.
