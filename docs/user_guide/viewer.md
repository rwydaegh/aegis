# Interactive 3D viewer

The viewer has two parts: a Flask REST backend that runs dosimetry computations and serves data, and a React + Three.js frontend that renders the scene. The frontend shows a body mesh with absorbed power density heatmap, optional voxel environments, antenna radiation patterns, and real-time dosimetry stats.

## Requirements

- Python 3.12 with AEGIS installed (`pip install -e ".[dev]"`).
- Node.js 18+ for the React frontend (development only, production builds are static).
- Body STL under your [data directory](../getting_started.md#loading-real-meshes) (default mesh `thelonious` unless you override it).
- Optional: `pip install -e ".[rt]"` for DiffeRT or Sionna ray tracing in the UI.
- Optional: `GOOGLE_API_KEY` for geocoded voxel loading.

## Launch

Start the Flask backend (port **5000** by default):

```bash
py -3.12 -m aegis.viewer
py -3.12 -m aegis.viewer --scenario open_ground
```

For development, run the React frontend separately (port **5173**, hot-reloads):

```bash
cd aegis-web
npm install    # first time only
npm run dev
```

Open `http://localhost:5173` in your browser. The frontend proxies API calls to the Flask backend on port 5000.

**Remote GPU (TensorDock):** If the backend runs on a cloud VM, see [Cloud GPU machine](../developer_guide/cloud_machine.md). Use `python tools/cloud.py status` for the correct URL or SSH tunnel. You usually open **`http://localhost:5000`** (or 5173 with `npm run dev` against a tunneled API) after port forwarding, not the raw instance IP unless TensorDock exposes port 5000.

For production, Flask serves the React app from `src/aegis/viewer/static/` (gitignored). Build and copy in one step from the repo root:

```bash
cd aegis-web && npm ci && npm run build:copy
```

If that folder is missing, Flask falls back to a deprecated single-file HTML viewer (`templates/_legacy_index.html`) and shows a warning banner.

Common backend flags:

| Flag | Purpose |
|------|---------|
| `--config path.json` | Merge JSON over built-in defaults (see `configs/default.json`). |
| `--scenario name` | Apply a named scenario from the config file. |
| `--no-open` | Do not open a browser tab. |
| `--port N` | HTTP port (default 5000). |
| `--host addr` | Bind address (default 127.0.0.1). |
| `--voxel-dir`, `--voxel-json` | Load voxel data from disk. |
| `--location "City"` | Fetch voxels via the geocoding pipeline. |
| `--body name` | STL stem under the data directory. |
| `--level N` | Default fidelity level for compute. |
| `--bbox meters` | Scene bounding box diameter (default 30). |
| `--data-dir path` | Override the data directory for STL meshes. |

## UI controls

**Scene interaction.** Click anywhere on the ground, voxel surfaces, or Sionna scene geometry to place a transmit antenna. The antenna shows a short dipole radiation pattern (sin^2 theta gain deformation) on a pole at the click point. Dosimetry computes automatically after placement.

**Camera.** Two modes, toggled from the toolbar:

- Orbit mode (default): left-click drag to rotate, scroll to zoom, middle-click to pan. Camera presets (front, side, top, focus) are available in the toolbar.
- Follow mode: third-person camera that tracks the phantom. Q/E keys or left-click drag to orbit around the body. Mouse wheel to zoom.

**Phantom.** The sidebar phantom panel lets you switch between body meshes (Duke, Ella, Thelonious, Eartha) and move or rotate the phantom with WASD keys. The dropdown shows IT'IS metadata (age, sex, mass) for each phantom.

**Dosimetry panel.** Choose fidelity level (0-6), tissue preset, transmit power, and frequency. Levels 4-6 add polarization, curvature, and diffraction corrections.

**Stochastic panel.** When ray tracing is off, controls how multipath is modeled. Select a 3GPP TR 38.901 scenario preset (UMi, UMa, Indoor, InF, RMa, in LOS or NLOS variants) and the channel model generates cluster-based multipath with proper K-factor splitting, angular spreads, and sub-path structure. You can override individual parameters (K-factor, azimuth/elevation spread, number of clusters) or reset to the preset defaults. This is mutually exclusive with ray tracing: enabling one disables the other.

**Colormap.** Absorbed power density is rendered as a jet colormap on the body mesh. The legend on the right side supports:

- Linear and dB scale (toggle button). The dB scale maps values logarithmically relative to peak S_ab.
- Adjustable dynamic range floor in dB mode (default auto-detected from the S_ab distribution).
- Lock/unlock button to freeze the colormap maximum for comparing across antenna placements or fidelity levels.

**HUD overlay.** The top-right stats card shows whole-body SAR, total absorbed power, peak S_ab, distance, illuminated triangle count, and ICNIRP compliance status. Server resource usage (CPU, RAM, GPU) appears in the bottom-right corner.

**Layers.** Toggle visibility of wireframe overlay, voxel environment, and Sionna scene geometry from the layers panel.

## Configuration and scenarios

Viewer constants are defined in `src/aegis/viewer/config.py` and merged with your JSON. The repo ships `configs/default.json` plus [configs/README.md](https://github.com/rwydaegh/aegis/blob/master/configs/README.md) for the schema.

**Scenarios** group launch inputs so runs are repeatable:

- `default_scenario` in JSON selects a scenario when you do not pass `--scenario`.
- Each scenario has a `description` and a `launch` object (`voxel_dir`, `voxel_json`, `body`, `bbox`, `data_dir`). CLI arguments override the scenario after merge.

The `open_ground` scenario clears voxel paths so you get the body on a flat surface only.

## API overview

The React frontend calls REST endpoints on the Flask backend:

- `GET /api/config` - bodies list, available backends (voxels, DiffeRT, Sionna), scene list, body metadata.
- `GET /api/body/<name>`, `GET /api/voxels` - binary mesh and voxel payloads with metadata headers.
- `GET /api/levels`, `GET /api/tissues` - fidelity level catalog and tissue presets.
- `GET /api/health`, `GET /api/system` - server health check and system resource info.
- `POST /api/compute` - synthetic multipath dosimetry.
- `POST /api/compute/voxel-rt`, `POST /api/compute/rt` - DiffeRT ray-traced paths.
- `POST /api/compute/sionna-rt` - Sionna RT ray-traced paths.
- `POST /api/body/switch` - switch the active body mesh.
- `GET /api/location/load` - SSE endpoint for geocoded location loading.

`voxel_rt_available` in `/api/config` is true only when voxel grid data is loaded **and** DiffeRT is importable, so the UI does not offer voxel ray tracing when it would always fail.

## Coordinates

AEGIS uses **Z-up** in Python. The Three.js frontend uses **Y-up**. The Flask backend applies coordinate swaps when serializing body and scene binaries. The frontend applies the inverse when sending positions back (antenna placement, body offset).

## See also

- [Architecture](../developer_guide/architecture.md) - module layout including `src/aegis/viewer/` and `aegis-web/`.
- [Testing](../developer_guide/testing.md) - pytest and marks.
