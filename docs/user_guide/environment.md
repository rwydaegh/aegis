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

## Detail mode

Passing `detail=True` to `from_osm()` generates per-floor facades with window and door openings cut into the walls. Windows use the GLASS material. Doors use WOOD. The geometry is more expensive to compute but gives the ray tracer realistic surface discontinuities for indoor/outdoor path transitions.

```python
mesh = EnvironmentMesh.from_osm(lat=51.05, lon=3.72, radius_m=200, detail=True)
```

Window dimensions and spacing follow a default `WindowParams` profile derived from typical European residential construction. You can supply a custom profile:

```python
from aegis.environment.style import WindowParams

params = WindowParams(width=1.2, height=1.4, sill_height=0.9, spacing=3.5)
mesh = EnvironmentMesh.from_osm(lat=51.05, lon=3.72, radius_m=200, detail=True, window_params=params)
```

Detail mode is slower (roughly 3-5x) and produces more triangles. For large radii, stay under 150 m or expect seconds-long fetch times.

## Building parts and relations

OSM encodes complex buildings as multipolygon relations with `building:part` members. Common cases include courtyards (the outer ring minus inner holes), towers with different heights from adjacent wings, and mixed-use podium blocks where a low base carries a taller tower.

AEGIS parses these relations automatically. Each `building:part` member gets its own height, roof type, and material. Inner holes in the footprint polygon become courtyards, open to the sky. Parts that share a footprint edge are stitched to avoid gaps.

When `roof:shape` or `height` tags are missing on individual parts, the parent relation's tags are used as fallback.

## GeoJSON import

`build_environment_from_geojson()` accepts a GeoJSON FeatureCollection with Polygon or MultiPolygon building footprints. Each feature can carry `height`, `building:material`, and `roof:shape` properties. The function applies the same roof and material pipeline as the OSM path.

GeoJSON coordinates are `[longitude, latitude]` (GeoJSON spec), not `[lat, lon]`. Pass the wrong order and buildings appear at the wrong location.

```python
from aegis.environment import build_environment_from_geojson
import json

with open("my_buildings.geojson") as f:
    fc = json.load(f)

mesh = build_environment_from_geojson(fc, origin_lat=51.05, origin_lon=3.72)
```

Alternatively, `EnvironmentMesh.from_geojson()` is a thin wrapper that returns an `EnvironmentMesh` directly:

```python
mesh = EnvironmentMesh.from_geojson(fc, origin_lat=51.05, origin_lon=3.72)
```

## Natural features

Forests, parks, and hedges are fetched automatically from the Overpass API alongside buildings.

- Forests and dense woodland produce canopy volumes using VEGETATION_DENSE material. The canopy is a closed mesh at the nominal tree-top height (default 8 m) with a ground base. Ray tracing treats it as a dielectric volume.
- Parks and open green areas produce ground planes at elevation zero using VEGETATION material. These replace bare ground inside the park boundary.
- Hedges produce thin vertical walls at the centerline of the way, approximately 1.5 m tall, using VEGETATION_DENSE material.

Natural features obey the same `buildings_enabled`-style flags. Disable them with `natural_enabled=False` if you only want the built environment.

## Terrain

`TerrainGrid` holds elevation data on a regular latitude-longitude grid. The SRTM HGT format (1 arc-second, ~30 m resolution) is the primary input.

```python
from aegis.environment.terrain import TerrainGrid, generate_terrain_mesh

grid = TerrainGrid.from_hgt("N51E003.hgt")
terrain_mesh = generate_terrain_mesh(grid, lat=51.05, lon=3.72, radius_m=400)
```

`project_z` reprojects building footprints onto the terrain surface so walls start at the correct ground elevation rather than a flat plane:

```python
mesh = EnvironmentMesh.from_osm(lat=51.05, lon=3.72, radius_m=300)
mesh = mesh.project_z(grid)
```

`project_z` raises `ValueError` if the terrain grid does not cover the mesh extent. Use a larger HGT tile or combine adjacent tiles with `TerrainGrid.merge()`.

## Overlay

Satellite imagery tiles follow the XYZ slippy-map scheme. Three functions in `aegis.environment.tiles` handle the math:

- `tile_coords(lat, lon, zoom)` returns the `(x, y, z)` tile coordinates for a geographic point.
- `stitch_bounds(lat, lon, radius_m, zoom)` returns the bounding box in tile coordinates needed to cover a circular region.
- `meters_per_pixel(lat, zoom)` gives the ground resolution at a given latitude and zoom level.

These are used internally by the viewer's satellite overlay fetch. You can use them to download and align imagery for custom visualizations:

```python
from aegis.environment.tiles import tile_coords, meters_per_pixel

tx, ty, tz = tile_coords(51.05, 3.72, zoom=18)
res = meters_per_pixel(51.05, zoom=18)  # ~0.6 m/px at this latitude
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
| Roof tile | 4.5 | 0.02 |
| Soil | 12.0 | 0.03 |
| Vegetation | 1.6 | 0.008 |
| Vegetation (dense) | 2.1 | 0.04 |
| Plaster | 2.9 | 0.015 |

ROOF_TILE applies to tiled ceramic roofs (`roof:material=roof_tiles`). SOIL covers exposed earth surfaces without vegetation. VEGETATION covers parks and grass. VEGETATION_DENSE covers canopy volumes and hedges. PLASTER applies to rendered concrete facades (`building:material=plaster`).

OSM assigns materials from building tags (`building:material=brick`). 3D Tiles classifies vertex colors using HSV heuristics. Unknown materials default to concrete.

## Building styles

`resolve_style()` maps OSM tags to a `BuildingStyle` containing wall material, roof material, and a color palette index. The style controls both the EM assignment and the visual appearance in the viewer.

```python
from aegis.environment.style import resolve_style

style = resolve_style({"building:material": "brick", "roof:material": "roof_tiles"})
# style.wall_material == MaterialType.BRICK
# style.roof_material == MaterialType.ROOF_TILE
```

When no tags are present, `resolve_style()` picks a default palette color deterministically from the building's OSM ID, giving each building a visually distinct shade without storing explicit color data.

## OSM pipeline

`EnvironmentMesh.from_osm()` runs this pipeline:

1. Query the Overpass API for buildings, roads, water, and natural features within a bounding box
2. Parse the XML response and project WGS84 coordinates to local meters via Transverse Mercator
3. Resolve building styles from OSM tags via `resolve_style()`
4. Generate 3D building geometry: vertical walls from the footprint, roof from the `roof:shape` tag
5. Generate natural feature geometry: canopy volumes, vegetation planes, hedge walls
6. Generate road quad strips from centerlines and water polygons at ground level
7. Assign materials from OSM tags and compute per-face normals

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
    natural_enabled=True,
    detail=False,
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
      "water": true,
      "natural": true,
      "detail": false
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
| POST | `/api/environment/geojson` | Import GeoJSON FeatureCollection as mesh |
| POST | `/api/terrain/elevation` | Fetch or upload SRTM terrain and return terrain mesh |

All mesh endpoints return `application/octet-stream` with an `X-Meta` JSON header containing vertex/triangle counts and material list.
