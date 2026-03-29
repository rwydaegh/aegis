# Interactive 3D viewer

The viewer has two parts: a Flask REST backend that runs dosimetry computations and serves data, and a React + Three.js frontend that renders the scene. The frontend shows a body mesh with absorbed power density heatmap, optional voxel environments, antenna radiation patterns, and real-time dosimetry stats.

The production instance runs at [aegis.waves-ugent.be](https://aegis.waves-ugent.be) (password-protected). See [Deployment](deployment.md) for server details.

## Running locally

Start the Flask backend (port **5000** by default):

```bash
python -m aegis.viewer
python -m aegis.viewer --scenario open_ground
```

Requirements: Python 3.12, `pip install -e ".[dev]"`, body STL in the [data directory](../getting_started.md#loading-real-meshes). Optional: `pip install -e ".[rt]"` for DiffeRT or Sionna ray tracing.

For frontend development with hot reload, run the Vite dev server in a second terminal:

```bash
cd aegis-web
npm install    # first time only
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` calls to Flask on port 5000, so both must be running. Changes to React components reflect instantly without rebuilding.

To build the production frontend (Flask serves it from `static/`):

```bash
cd aegis-web && npm ci && npm run build:copy
```

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

**Camera.** Three modes, toggled from the toolbar:

- Orbit mode (default): left-click drag to rotate, scroll to zoom, middle-click to pan. Camera presets (front, side, top, focus) are available in the toolbar.
- Follow mode: third-person camera that tracks the phantom. Q/E keys or left-click drag to orbit around the body. Mouse wheel to zoom.
- Globe mode: a globe camera from 3DTilesRendererJS that lets you zoom out to see the full Earth when using Google 3D Tiles. Toggle via the globe icon in the toolbar. Clicking any camera preset resets back to orbit mode.

**Phantom.** The sidebar phantom panel lets you switch between body meshes (Duke, Ella, Thelonious, Eartha) and move or rotate the phantom with WASD keys. The dropdown shows IT'IS metadata (age, sex, mass) for each phantom.

**Dosimetry panel.** Choose fidelity level (0-6), tissue preset, transmit power, and frequency. Levels 4-6 add polarization, curvature, and diffraction corrections.

**Stochastic panel.** When ray tracing is off, controls how multipath is modeled. Select a 3GPP TR 38.901 scenario preset and the channel model generates cluster-based multipath paths.

- Presets: UMi, UMa, Indoor, InF, RMa, each in LOS and NLOS variants.
- Overridable per-preset: K-factor, azimuth/elevation spread, number of clusters.
- Mutually exclusive with ray tracing. Enabling one disables the other.

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

## Environment panel

The environment panel (sidebar, first accordion section) controls how 3D city geometry is loaded. Four source modes are available:

- **None** renders the legacy voxel environment and scene geometry. This is the default.
- **Voxels** converts loaded voxel data into a triangle mesh.
- **OpenStreetMap** fetches building footprints from the Overpass API and generates 3D geometry with roofs, roads, and water. Enter latitude/longitude and radius, then click Fetch.
- **Google 3D Tiles** streams photorealistic tiles from Google's Map Tiles API. Requires a Google Maps API key (entered in the panel). Buildings and terrain render client-side via 3DTilesRendererJS.

OSM-specific options: default building height, storey height, and toggles for buildings, roads, and water. The **Detail** checkbox enables per-floor facade generation with window and door openings. This produces more triangles and is slower to fetch; keep the radius below 150 m when detail is on.

3D Tiles options: geometric error (LOD control) and API key.

After fetching, click **Export for Ray Tracing** to convert the environment mesh into a DiffeRT scene for path computation.

### GeoJSON upload

Instead of fetching from OSM, you can upload a `.geojson` file containing building footprints. Click **Upload GeoJSON** in the environment panel, select the file, and confirm. AEGIS reads the FeatureCollection, runs the same roof and material pipeline as OSM, and displays the result in the scene. The origin coordinates set in the latitude/longitude fields are used as the local ENU reference.

GeoJSON coordinates must be `[longitude, latitude]` per the GeoJSON spec. Files with swapped coordinates will place buildings at the wrong location.

### Terrain

The terrain section sits below the source controls in the environment panel. Check **Enable terrain** to activate elevation-based ground geometry. Click **Fetch elevation** to download SRTM data for the current location from the server. The terrain appears as a mesh under the buildings, and building footprints are projected onto the terrain surface.

The server caches the most recent terrain grid. Re-fetching with a different location or radius replaces it.

For the Python API and material properties, see [Environment module](environment.md).

## API overview

The React frontend calls REST endpoints on the Flask backend:

- `GET /api/config` - bodies list, available backends (voxels, DiffeRT, Sionna), scene list, body metadata.
- `GET /api/body?name=X` - binary mesh payload with metadata header. All bodies are preloaded at startup.
- `GET /api/voxels` - binary voxel payload with metadata header.
- `GET /api/levels` - fidelity level catalog.
- `GET /api/health`, `GET /api/system` - server health check and system resource info.
- `POST /api/compute` - dosimetry computation. Accepts `body_name` to select which body to use.
- `POST /api/compute/voxel-rt`, `POST /api/compute/rt` - DiffeRT ray-traced paths.
- `POST /api/compute/sionna-rt` - Sionna RT ray-traced paths.
- `POST /api/auth` - password authentication, returns a signed session cookie.
- `GET /api/location/load` - SSE endpoint for geocoded location loading.
- `POST /api/environment/osm`, `POST /api/environment/3dtiles` - fetch environment meshes.
- `POST /api/environment/geojson` - import a GeoJSON FeatureCollection as an environment mesh.
- `GET /api/environment/mesh` - return cached environment mesh.
- `POST /api/environment/export-scene` - export environment to DiffeRT or Sionna scene.
- `POST /api/terrain/elevation` - fetch or upload SRTM terrain data and return the terrain mesh.

`voxel_rt_available` in `/api/config` is true only when voxel grid data is loaded **and** DiffeRT is importable, so the UI does not offer voxel ray tracing when it would always fail.

## Coordinates

AEGIS uses **Z-up** in Python. The Three.js frontend uses **Y-up**. The Flask backend applies coordinate swaps when serializing body and scene binaries. The frontend applies the inverse when sending positions back (antenna placement, body offset).

## See also

- [Architecture](../developer_guide/architecture.md) - module layout including `src/aegis/viewer/` and `aegis-web/`.
- [Testing](../developer_guide/testing.md) - pytest and marks.
