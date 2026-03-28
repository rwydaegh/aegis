# Environment module

AEGIS can load 3D city environments from OpenStreetMap or Google Photorealistic 3D Tiles. Environment meshes feed directly into the ray tracing pipeline (DiffeRT or Sionna), giving you site-specific propagation paths instead of stochastic channel models.

Three sources are available:

- **OpenStreetMap** generates geometry from OSM building footprints with 12 roof types, roads, and water bodies. All processing happens server-side via the Overpass API.
- **Google 3D Tiles** streams photorealistic meshes from Google's Map Tiles API. The frontend renders tiles client-side for visualization. Server-side, the mesh is extracted for ray tracing.
- **Voxels** converts the existing voxel grid into a triangle mesh. This is the legacy path, useful when you already have voxel data loaded.

All three produce an `EnvironmentMesh` that the ray tracer accepts directly.

## Quick example

From the viewer sidebar, select OpenStreetMap as the source, enter coordinates, and click Fetch. Buildings appear in the 3D scene within seconds.

From Python:

```python
from aegis.environment import EnvironmentMesh

mesh = EnvironmentMesh.from_osm(lat=51.05, lon=3.72, radius_m=200)
print(f"{len(mesh.triangles)} triangles, {len(set(mesh.materials.tolist()))} materials")

scene = mesh.to_differt_scene()
```

For Google 3D Tiles (requires `GOOGLE_MAPS_API_KEY` environment variable):

```python
mesh = EnvironmentMesh.from_3dtiles(lat=51.05, lon=3.72, radius_m=200)
```

## Materials

Each triangle in an `EnvironmentMesh` carries a `MaterialType` with EM properties from ITU-R P.2040 at 28 GHz:

| Material | $\varepsilon_r$ | $\sigma$ (S/m) |
|----------|-----------------|----------------|
| Concrete | 5.31 | 0.0326 |
| Brick | 3.75 | 0.038 |
| Glass | 6.27 | 0.0043 |
| Metal | 1.0 | 10^7 |
| Asphalt | 3.18 | 0.0 |
| Wood | 1.99 | 0.0047 |
| Water | 81.0 | 0.01 |
| Ground | 15.0 | 0.035 |

OSM assigns materials from building tags (`building:material=brick`). 3D Tiles classifies vertex colors using HSV heuristics. Unknown materials default to concrete.

## OSM pipeline

`EnvironmentMesh.from_osm()` runs this pipeline:

1. Query the Overpass API for buildings, roads, and water within a bounding box
2. Parse the XML response and project WGS84 coordinates to local meters via Transverse Mercator
3. Generate 3D building geometry: vertical walls from the footprint, roof from the `roof:shape` tag
4. Generate road quad strips from centerlines and water polygons at ground level
5. Assign materials from OSM tags and compute per-face normals

Twelve roof types are supported: flat, gabled, hipped, pyramidal, skillion, half-hipped, gambrel, saltbox, mansard, dome, onion, and round (barrel vault). Hipped roofs use a straight skeleton algorithm ported from bpypolyskel. When `roof:shape` is absent, buildings get flat roofs.

### Controlling the fetch

```python
mesh = EnvironmentMesh.from_osm(
    lat=51.05, lon=3.72, radius_m=300,
    default_building_height=12,   # meters, when OSM has no height tag
    level_height=3.0,             # per-storey height for building:levels
    buildings_enabled=True,
    roads_enabled=True,
    water_enabled=True,
)
```

The Overpass API has rate limits. If you hit a 429 response, wait 60 seconds and retry. Requests that exceed 50 MB are rejected.

## 3D Tiles pipeline

Google Photorealistic 3D Tiles provide real-world geometry with vertex colors. The server-side pipeline fetches the tileset, traverses the tile tree within a query radius, extracts triangle meshes from GLB/B3DM payloads, and transforms from ECEF to local ENU coordinates.

```python
mesh = EnvironmentMesh.from_3dtiles(
    lat=51.05, lon=3.72, radius_m=200,
    geometric_error=30.0,   # lower = more detail, more tiles fetched
    api_key="your-key",     # or set GOOGLE_MAPS_API_KEY env var
)
```

The `geometric_error` threshold controls level of detail. Values below 10 fetch very detailed meshes (slow). 30 is a reasonable default for dosimetry scenes.

!!! note
    Google's Map Tiles API requires a valid API key with the Map Tiles API enabled. See [Google's documentation](https://developers.google.com/maps/documentation/tile/cloud-setup) for setup.

## Exporting for ray tracing

`EnvironmentMesh` converts to DiffeRT or Sionna scenes:

```python
# DiffeRT (JAX arrays, Z-up ENU coordinates)
scene = mesh.to_differt_scene()

# Sionna (Mitsuba XML + PLY files)
scene_path = mesh.to_sionna_xml("output/scene.xml")
```

The DiffeRT export maps each `MaterialType` to a named material with a display color and the correct EM properties. Vertices stay in ENU (Z-up), which matches DiffeRT's coordinate convention.

## Combining sources

You can merge meshes from different sources as long as they share the same geographic origin:

```python
osm_mesh = EnvironmentMesh.from_osm(lat=51.05, lon=3.72, radius_m=200)
voxel_mesh = EnvironmentMesh.from_voxels(positions, materials, voxel_size=1.0)

# This raises ValueError if origins differ
combined = EnvironmentMesh.combine(osm_mesh, voxel_mesh)
```

## Coordinate systems

All `EnvironmentMesh` data is stored in local ENU (East-North-Up) meters relative to `origin_lat`, `origin_lon`. The coordinate transforms:

| Frame | Convention | Used by |
|-------|-----------|---------|
| WGS84 | Latitude, longitude, altitude (degrees) | OSM nodes, user input |
| ECEF | Earth-centered Cartesian (meters) | 3D Tiles bounding volumes |
| ENU | East-North-Up local (meters, Z-up) | EnvironmentMesh storage, DiffeRT |
| Y-up | East-Up-South (meters, Y-up) | Three.js frontend |

The backend handles all conversions. `to_binary()` swaps ENU to Y-up for the frontend. `to_differt_scene()` keeps ENU as-is.

## Viewer integration

The environment module is accessible from the **Environment** panel in the sidebar. See [Interactive viewer](viewer.md#environment-panel) for the UI controls.

## Configuration

Set environment defaults in your config JSON under the `environment` key:

```json
{
  "environment": {
    "source": "osm",
    "location": {"lat": 51.05, "lon": 3.72},
    "radius": 200,
    "osm": {
      "default_building_height": 10,
      "level_height": 3.0,
      "buildings": true,
      "roads": true,
      "water": true
    },
    "tiles": {
      "geometric_error": 30.0
    }
  }
}
```

The Google Maps API key is read from the `GOOGLE_MAPS_API_KEY` environment variable only. It is never stored in config files.

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/environment/osm` | Fetch OSM data and return binary mesh |
| POST | `/api/environment/3dtiles` | Fetch 3D Tiles and return binary mesh |
| POST | `/api/environment/from-voxels` | Convert cached voxels to mesh |
| POST | `/api/environment/combine` | Combine cached meshes |
| GET | `/api/environment/mesh` | Return most recent mesh |
| POST | `/api/environment/export-scene` | Export to DiffeRT or Sionna |
| GET | `/api/environment/materials` | Material catalog with EM properties |

All mesh endpoints return `application/octet-stream` with an `X-Meta` JSON header containing vertex/triangle counts and material list.
