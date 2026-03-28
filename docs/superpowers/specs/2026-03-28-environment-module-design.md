# Environment module design

Integrate blosm (OpenStreetMap + Google 3D Tiles) into AEGIS as a new `src/aegis/environment/` package. All environment sources produce a unified `EnvironmentMesh` dataclass that feeds the existing ray tracing and dosimetry pipeline. Frontend gains 3DTilesRendererJS streaming visualization and a globe camera mode. All legacy code (voxels, GLB tiles, Sionna scenes) remains fully functional.

## Architecture overview

```
User selects source + location
        |
        v
+-------------------+     +-------------------+     +-------------------+
| OSM (Overpass API) |     | Google 3D Tiles   |     | Voxels (legacy)   |
| osm.py + roofs.py  |     | tiles.py          |     | from_voxels()     |
+-------------------+     +-------------------+     +-------------------+
        \                       |                       /
         \                      |                      /
          v                     v                     v
        +-------------------------------------+
        |         EnvironmentMesh             |
        | vertices, triangles, normals,       |
        | materials, origin_lat, origin_lon   |
        +-------------------------------------+
               |                    |
               v                    v
    .to_differt_scene()      .to_binary()
               |                    |
               v                    v
    DiffeRT / Sionna RT      Frontend render
    PropagationPaths         (OSM mesh or
    DosimetryEngine          3DTilesRendererJS)
```

The frontend has two parallel visualization paths:
- **OSM mesh**: backend generates geometry, sends binary to frontend, rendered as `<mesh>`
- **3D Tiles**: `3DTilesRendererJS` streams tiles client-side (visualization only). Server-side `tiles.py` extracts mesh for ray tracing separately.

## Module structure

```
src/aegis/environment/
    __init__.py          EnvironmentMesh dataclass, MaterialType enum
    geo.py               WGS84/ECEF/ENU coordinate transforms (numpy, replaces mathutils)
    osm.py               Overpass API fetch + blosm OSM parser integration
    roofs.py             12+ roof algorithms ported from blosm bmesh to numpy
    tiles.py             3D Tiles traversal + GLB-to-mesh (blosm py3dtiles + adapted manager)
    materials.py         ITU-R P.2040 EM material catalog and classification
    export.py            DiffeRT XML scene export, Sionna XML export, binary serialization
```

## EnvironmentMesh dataclass

```python
from enum import IntEnum

class MaterialType(IntEnum):
    CONCRETE = 0
    BRICK = 1
    GLASS = 2
    METAL = 3
    ASPHALT = 4
    VEGETATION = 5
    WATER = 6
    WOOD = 7
    GROUND = 8
    UNKNOWN = 9

MATERIAL_EM_PROPERTIES = {
    MaterialType.CONCRETE:   {"eps_r": 5.31, "sigma": 0.0326},
    MaterialType.BRICK:      {"eps_r": 3.75, "sigma": 0.038},
    MaterialType.GLASS:      {"eps_r": 6.27, "sigma": 0.0043},
    MaterialType.METAL:      {"eps_r": 1.0,  "sigma": 1e7},
    MaterialType.ASPHALT:    {"eps_r": 3.18, "sigma": 0.0},
    MaterialType.VEGETATION: {"eps_r": 1.0,  "sigma": 0.0},
    MaterialType.WATER:      {"eps_r": 81.0, "sigma": 0.01},
    MaterialType.WOOD:       {"eps_r": 1.99, "sigma": 0.0047},
    MaterialType.GROUND:     {"eps_r": 15.0, "sigma": 0.035},
    MaterialType.UNKNOWN:    {"eps_r": 5.31, "sigma": 0.0326},  # default to concrete
}

@dataclass
class EnvironmentMesh:
    vertices: np.ndarray       # (N, 3) float64, local ENU meters
    triangles: np.ndarray      # (M, 3) uint32, face indices
    normals: np.ndarray        # (M, 3) float64, per-face normals
    materials: np.ndarray      # (M,) uint8, MaterialType per face
    origin_lat: float
    origin_lon: float
    source: str                # "osm", "3dtiles", "voxels", "combined"

    @classmethod
    def from_osm(cls, lat, lon, radius_m, **kwargs) -> "EnvironmentMesh": ...

    @classmethod
    def from_3dtiles(cls, lat, lon, radius_m, geometric_error=30., api_key=None) -> "EnvironmentMesh": ...

    @classmethod
    def from_voxels(cls, positions, materials, voxel_size) -> "EnvironmentMesh": ...

    @classmethod
    def combine(cls, *meshes) -> "EnvironmentMesh":
        """Merge meshes. All inputs must share the same origin (lat/lon). Raises ValueError otherwise."""
        ...

    def to_differt_scene(self): ...                    # returns DiffeRT TriangleScene
    def to_sionna_xml(self, path): ...                 # writes Sionna XML
    def to_binary(self) -> tuple[bytes, dict]: ...     # (binary_data, metadata_dict)
```

## geo.py: coordinate transforms

Replaces all `mathutils.Vector` / `mathutils.Matrix` usage in blosm's `threed_tiles/manager.py` with numpy equivalents.

Functions:
- `wgs84_to_ecef(lat, lon, alt=0)` - geodetic to ECEF using WGS84 ellipsoid (a=6378137, f=1/298.257223563)
- `ecef_to_enu(ecef, origin_ecef, origin_lat, origin_lon)` - ECEF to local East-North-Up
- `enu_to_yup(enu)` - ENU to Three.js Y-up: `[east, up, -north]`
- `rotation_ecef_to_enu(lat, lon)` - 3x3 rotation matrix
- `obb_aabb_intersect(obb_center, obb_half_axes, aabb_min, aabb_max)` - separating axis theorem
- `sphere_aabb_intersect(center, radius, aabb_min, aabb_max)` - Arvo's algorithm
- `box_sphere_intersect(box_center, box_half, sphere_center, sphere_radius)` - from blosm
- `transverse_mercator_forward(lat, lon, origin_lat, origin_lon)` - local projection (adapted from blosm's `util/transverse_mercator.py`)

All pure numpy. No external dependencies.

## osm.py: OpenStreetMap pipeline

1. `fetch_osm(lat, lon, radius_m) -> str` - sends Overpass API query, returns XML string
2. Parse via blosm's `parse.osm.Osm` class (imported from `blosm.parse.osm`)
3. `extract_buildings(osm) -> list[Building]` - closed ways with `building=*`, extract footprint polygon, height/levels/material tags
4. `extract_roads(osm) -> list[Road]` - ways with `highway=*`, extract width from `lanes` tag
5. `extract_water(osm) -> list[Polygon]` - ways/relations with `natural=water` or `waterway=*`
6. For each building: call `roofs.generate_building()` which produces walls + roof geometry
7. For roads: flat quad extrusion at ground level, material ASPHALT
8. For water: flat polygon triangulation at ground level, material WATER
9. Merge all vertices/triangles, compute face normals, return `EnvironmentMesh`

Tags used for material classification:
- `building:material=brick` -> BRICK
- `building:material=stone/concrete` -> CONCRETE
- `building:material=wood` -> WOOD
- `building:material=glass` -> GLASS
- `building:material=metal` -> METAL
- Default (no tag) -> CONCRETE

## roofs.py: roof geometry algorithms

Port all roof types from blosm's `building/roof/` and `action/volume/` to pure numpy output. The core algorithms (vertex placement, ridge lines, profile sweeps) are mathematical, the only Blender dependency is writing into `bmesh`. We replace `bmesh` writes with numpy array accumulation.

### Interface

```python
def generate_building(footprint: np.ndarray, height: float,
                      roof_shape: str, roof_height: float | None = None,
                      roof_angle: float | None = None,
                      material: MaterialType = MaterialType.CONCRETE,
                      roof_material: MaterialType = MaterialType.CONCRETE,
                     ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate complete building geometry (walls + roof).
    Returns (vertices, triangles, face_materials).
    """
```

### Roof types

| Type | Algorithm source | Notes |
|---|---|---|
| flat | `building/roof/flat.py` | Fan triangulation of top polygon |
| gabled | `action/volume/roof_gabled.py` | Ridge along longest axis, two slope planes |
| hipped | `action/volume/roof_hipped.py` | Straight skeleton via bpypolyskel, all edges slope |
| pyramidal | (simple) | Single apex at centroid |
| skillion | `building/roof/skillion.py` | Single slope plane |
| half_hipped | `building/roof/half_hipped.py` | Gabled with hipped ends |
| gambrel | `action/volume/roof_profile.py` | Double-slope barn profile |
| saltbox | (gabled variant) | Asymmetric ridge placement |
| mansard | `action/volume/roof_profile.py` | Four-sided double-slope |
| dome | parametric | Hemisphere mesh (lat/lon subdivision) |
| onion | parametric | Onion curve of revolution |
| round | parametric | Barrel vault along ridge line |

### Shared utilities

- `triangulate_polygon(polygon: np.ndarray) -> np.ndarray` - ear-clipping or fan triangulation for convex/simple polygons
- `extrude_walls(footprint: np.ndarray, base_height: float, top_height: float) -> tuple[np.ndarray, np.ndarray]` - wall quads from footprint edges, triangulated
- Straight skeleton: full numpy rewrite of `blosm/lib/bpypolyskel/bpyeuclid.py` (~150 lines of 2D point/line/ray geometry), then `bpypolyskel.py` adapted to use it

## tiles.py: 3D Tiles server-side pipeline

Adapts blosm's `threed_tiles/manager.py` traversal logic with numpy coordinate math from `geo.py`.

### TileTraverser class

```python
class TileTraverser:
    def __init__(self, root_url: str, api_key: str | None = None,
                 geometric_error: float = 30.0):
        self.session = requests.Session()
        # Google auth headers if api_key provided

    def traverse(self, lat: float, lon: float, radius_m: float) -> EnvironmentMesh:
        """Fetch all tiles within radius at configured LOD, return merged mesh."""
```

Pipeline:
1. Fetch root `tileset.json`
2. Recursive traversal: for each tile, check bounding volume intersection with query region (using `geo.py` SAT/sphere tests)
3. LOD selection: if tile's `geometricError < threshold`, use this tile, don't recurse children
4. Fetch tile content (B3DM or GLB)
5. Parse via `blosm.threed_tiles.py3dtiles` - extract vertices, indices from binary glTF
6. Apply RTC_CENTER offset, transform ECEF to local ENU via `geo.py`
7. Classify materials from vertex colors (heuristic HSV mapping, similar to existing `classify_material` in `scene_data.py`)
8. Merge all tile meshes, return `EnvironmentMesh`

LOD presets in config: preview (200), medium (60), high (30), ultra (7).

## materials.py: EM material properties

Central catalog of material electromagnetic properties per ITU-R P.2040-3.

```python
def get_em_properties(material: MaterialType, freq_hz: float = 28e9,
                      overrides: dict | None = None) -> tuple[float, float]:
    """Return (eps_r, sigma) for a material at given frequency."""
```

The ITU-R P.2040 model provides frequency-dependent properties. At 28 GHz (AEGIS default), the values in `MATERIAL_EM_PROPERTIES` are the right ones. The function supports config-level overrides from the `environment.materials` config section.

Material classification heuristics (for 3D Tiles vertex colors):
- HSV-based rules similar to existing `classify_material` in `scene_data.py`
- Extended with texture analysis for roof/wall distinction

## export.py: scene export and serialization

### DiffeRT export

```python
def to_differt_scene(mesh: EnvironmentMesh) -> "TriangleScene":
    """Convert EnvironmentMesh to DiffeRT TriangleScene for ray tracing."""
```

Reuses the pattern from `raytracer.py`'s `round_triangle_scene()`:
- Vertices in Z-up (DiffeRT convention): ENU `[east, north, up]` maps to `[x, y, z]`
- Per-triangle material colors from `MaterialType`
- Returns `TriangleScene` with empty transmitters/receivers (filled by RT compute)

### Sionna XML export

```python
def to_sionna_xml(mesh: EnvironmentMesh, path: Path) -> Path:
    """Write EnvironmentMesh as Sionna-compatible XML scene."""
```

Generates XML matching Sionna RT's scene format. Each material type becomes a named material with the EM properties.

### Binary serialization

```python
def to_binary(mesh: EnvironmentMesh) -> tuple[bytes, dict]:
    """Serialize for frontend. Returns (binary_data, metadata_dict)."""
```

Wire format:
- `float32 vertices (N*3)` | `uint32 triangles (M*3)` | `float32 normals (M*3)` | `uint8 materials (M)`
- Metadata in X-Meta header: `n_vertices`, `n_triangles`, `materials`, `source`, `origin_lat`, `origin_lon`

## Backend routes: `viewer/routes/environment.py`

New Flask blueprint registered in `server.py` alongside existing route modules.

| Route | Method | Body / Query | Returns |
|---|---|---|---|
| `POST /api/environment/osm` | POST | `{lat, lon, radius, options?}` | Binary EnvironmentMesh + X-Meta |
| `POST /api/environment/3dtiles` | POST | `{lat, lon, radius, geometric_error?}` | Binary EnvironmentMesh + X-Meta |
| `POST /api/environment/from-voxels` | POST | (none, uses cached voxels) | Binary EnvironmentMesh + X-Meta |
| `POST /api/environment/combine` | POST | `{sources: ["osm", "voxels"]}` | Binary EnvironmentMesh + X-Meta |
| `GET /api/environment/mesh` | GET | (none) | Cached binary mesh |
| `POST /api/environment/export-scene` | POST | `{format: "differt"\|"sionna"}` | `{scene_path: "..."}` |
| `GET /api/environment/materials` | GET | (none) | Material catalog JSON |

Cache pattern: generated meshes stored in `_cache["environment_mesh"]`. Export writes to `cache_dir/environment_scene.xml`. The exported scene path is usable by existing RT routes (`/api/compute/rt`, `/api/compute/sionna-rt`).

No existing routes are modified.

## Frontend: new dependencies

```
npm install 3d-tiles-renderer
```

## Frontend: new files

### `src/stores/environment.ts`

```typescript
interface EnvironmentState {
  source: 'none' | 'voxels' | 'osm' | '3dtiles';
  location: { lat: number; lon: number } | null;
  radius: number;
  geometricError: number;
  osmMeshData: { positions: Float32Array; indices: Uint32Array; normals: Float32Array; materials: Uint8Array; meta: Record<string, unknown> } | null;
  loading: boolean;
  error: string | null;
  googleApiKey: string;
  osmOptions: { defaultBuildingHeight: number; levelHeight: number; buildings: boolean; roads: boolean; water: boolean };

  setSource: (s: EnvironmentState['source']) => void;
  setLocation: (lat: number, lon: number) => void;
  setRadius: (r: number) => void;
  setGeometricError: (ge: number) => void;
  fetchOSM: () => Promise<void>;
  fetchTilesForRT: () => Promise<void>;
  exportForRT: (format: 'differt' | 'sionna') => Promise<string>;
  setGoogleApiKey: (key: string) => void;
}
```

### `src/components/scene/Environment3DTiles.tsx`

Renders Google Photorealistic 3D Tiles via `3DTilesRendererJS`:

```tsx
<TilesRenderer>
  <TilesPlugin plugin={GoogleCloudAuthPlugin}
    args={{ apiToken: apiKey, logoUrl: "/google-maps-logo.png" }} />
  <TilesAttributionOverlay style={{ right: 10, bottom: 10, left: "auto" }} />
  <EastNorthUpFrame lat={location.lat} lon={location.lon}>
    {children}  {/* AEGIS scene objects positioned in ENU frame */}
  </EastNorthUpFrame>
</TilesRenderer>
```

Only rendered when `source === '3dtiles'` and `apiKey` is set.

### `src/components/scene/EnvironmentOSM.tsx`

Renders the OSM-generated mesh from backend:

```tsx
<mesh>
  <bufferGeometry>
    <bufferAttribute attach="attributes-position" ... />
    <bufferAttribute attach="index" ... />
    <bufferAttribute attach="attributes-normal" ... />
  </bufferGeometry>
  <meshStandardMaterial vertexColors />
</mesh>
```

Material-based vertex coloring: each triangle gets a color based on its `MaterialType` (concrete=gray, brick=brown, glass=light blue, vegetation=green, water=blue, asphalt=dark gray, etc.).

Only rendered when `source === 'osm'` and `osmMeshData` is loaded.

### `src/components/panels/EnvironmentPanel.tsx`

New sidebar accordion panel:

- **Source selector**: radio group (None / Voxels / OpenStreetMap / Google 3D Tiles)
- **Location input**: lat/lon number inputs + text geocoding field (Nominatim API)
- **Radius slider**: 50-500m, step 10
- **OSM options** (visible when source=osm): default building height, level height, toggles for buildings/roads/water
- **3D Tiles options** (visible when source=3dtiles): LOD preset dropdown, custom geometric error slider, API key input (password field)
- **"Generate for Ray Tracing" button**: calls `exportForRT()`, shows the generated scene path
- **Material mapping**: expandable section showing material name, eps_r, sigma, editable

## Frontend: modified files

### `src/components/scene/SceneRoot.tsx`

Changes:
- Import `Environment3DTiles` and `EnvironmentOSM`
- Conditionally render based on `useEnvironmentStore.source`:
  - `'none'`: render nothing extra
  - `'voxels'`: render existing `<VoxelField />` and `<Environment />` (legacy, unchanged)
  - `'osm'`: render `<EnvironmentOSM />`
  - `'3dtiles'`: wrap scene in `<Environment3DTiles>` which provides `TilesRenderer` context
- Camera mode branching: when `cameraMode === 'globe'`, render `<GlobeControls />` instead of current orbit controls

### `src/components/layout/Toolbar.tsx`

Changes:
- Add globe icon button (lucide-react `Globe` icon) to camera preset row
- Click toggles `useUIStore.cameraMode` between `'orbit'` and `'globe'`
- Active state styling when in globe mode
- Clicking any other camera preset auto-switches back to `'orbit'`

### `src/components/layout/Sidebar.tsx`

Changes:
- Add `<EnvironmentPanel />` as a new accordion section (between Scene and Layers, or as the first section)

### `src/stores/ui.ts`

Changes:
- Add `cameraMode: 'orbit' | 'globe'` state field (default `'orbit'`)
- Add `setCameraMode` action

### `src/stores/scene.ts`

No changes. The existing `envDisplayMode` and `glbTiles` fields remain for legacy voxel/GLB tile support. The new environment store is separate.

## Legacy preservation

| Existing feature | Status | Notes |
|---|---|---|
| `VoxelField.tsx` | Untouched | Renders when `source === 'voxels'` |
| `Environment.tsx` | Untouched | Renders GLB tiles when `source === 'voxels'` and tiles exist |
| `SceneGeometry.tsx` | Untouched | Renders loaded Sionna scenes |
| `/api/voxels` | Untouched | Still serves voxel binary data |
| `/api/tiles`, `/api/tiles/<f>` | Untouched | Still serves GLB tile files |
| `/api/scenes`, `/api/scene/load` | Untouched | Still lists/loads Sionna XML scenes |
| `ScenePanel.tsx` | Untouched | Still has location loader, scene selector, clear button |
| `LayersPanel.tsx` | Untouched | Still has env display mode, layer toggles |
| `RayTracingPanel.tsx` | Untouched | Still has RT backend selector, config |
| `raytracer.py` | Untouched | Voxel mesh generation and DiffeRT path computation unchanged |

The new environment module adds new options alongside existing ones. No existing endpoint, component, or store is removed or has its interface changed.

## Config changes

New `environment` key added to `DEFAULTS` in `config.py`:

```python
"environment": {
    "source": "none",
    "location": {"lat": 51.05, "lon": 3.72},
    "radius": 200,
    "osm": {
        "default_building_height": 10,
        "level_height": 3.0,
        "buildings": True,
        "roads": True,
        "water": True,
    },
    "tiles": {
        "provider": "google",
        "geometric_error": 30,
        "lod_presets": {
            "preview": 200,
            "medium": 60,
            "high": 30,
            "ultra": 7,
        },
    },
    "materials": {
        "concrete": {"eps_r": 5.31, "sigma": 0.0326},
        "brick": {"eps_r": 3.75, "sigma": 0.038},
        "glass": {"eps_r": 6.27, "sigma": 0.0043},
        "metal": {"eps_r": 1.0, "sigma": 1e7},
        "asphalt": {"eps_r": 3.18, "sigma": 0.0},
        "vegetation": {"eps_r": 1.0, "sigma": 0.0},
        "water": {"eps_r": 81.0, "sigma": 0.01},
        "wood": {"eps_r": 1.99, "sigma": 0.0047},
        "ground": {"eps_r": 15.0, "sigma": 0.035},
    },
},
```

Google API key: `GOOGLE_MAPS_API_KEY` environment variable. Never stored in config JSON.

Scenarios can set `environment.*` keys to preconfigure city environments:

```python
"scenarios": {
    "ghent_osm": {
        "description": "Ghent city center via OpenStreetMap",
        "launch": {"voxel_dir": None},
        "environment": {"source": "osm", "location": {"lat": 51.05, "lon": 3.72}, "radius": 200},
    },
}
```

## Testing strategy

### Unit tests

- `tests/test_environment_geo.py` - coordinate transform round-trips (WGS84 -> ECEF -> ENU -> back), known-point validation against pyproj
- `tests/test_environment_roofs.py` - each roof type produces valid mesh (watertight, correct vertex count, normals point outward)
- `tests/test_environment_materials.py` - material enum completeness, EM property lookup, config override
- `tests/test_environment_mesh.py` - EnvironmentMesh creation, combine, binary serialization round-trip
- `tests/test_environment_export.py` - DiffeRT scene export produces valid TriangleScene, Sionna XML is well-formed

### Integration tests (marked @slow)

- `tests/test_environment_osm_integration.py` - live Overpass API fetch for a small area, full pipeline to EnvironmentMesh
- `tests/test_environment_tiles_integration.py` - live Google 3D Tiles fetch (requires API key, skipped if absent)
- `tests/test_environment_rt.py` - EnvironmentMesh -> DiffeRT scene -> compute_paths -> PropagationPaths -> DosimetryEngine

### Frontend tests

- Vitest unit tests for `environment.ts` store
- Playwright E2E for environment panel interaction

## Dependencies

### Python (new)

- `requests` (must be added to `viewer` optional extra in `pyproject.toml`)
- No new compiled dependencies. All numpy/scipy.

### Python (used from blosm, imported)

- `blosm.parse.osm` - OSM XML parser (pure Python)
- `blosm.threed_tiles.py3dtiles` - B3DM/GLB parser (pure Python + numpy)
- `blosm.lib.bpypolyskel` - straight skeleton (pure Python, requires full numpy rewrite of bpyeuclid.py)

### npm (new)

- `3d-tiles-renderer` - 3DTilesRendererJS with R3F components

## Blosm code usage

Blosm source lives at `blosm/` in the repo root (already copy-pasted by user). We reference its pure Python modules as algorithm sources but cannot import the `blosm` package directly.

### Import boundary (critical)

`blosm/__init__.py` imports `bpy`, `bmesh`, `blf` at module load time. Any `from blosm.X import Y` will fail outside Blender. The safe import boundary:

- **Safe to import directly**: `blosm.threed_tiles.py3dtiles.*` (pure Python + numpy, no blosm `__init__` in the import chain since `py3dtiles` has its own `__init__`)
- **NOT safe to import**: anything that traverses `blosm/__init__.py`, including `blosm.parse.osm`, `blosm.threed_tiles.manager`, `blosm.lib.bpypolyskel`

**Solution**: use `importlib` to load specific submodules without triggering the top-level `__init__.py`:

```python
import importlib.util

def _import_blosm_submodule(dotted_path: str, file_path: str):
    """Import a blosm submodule directly from its file, bypassing blosm/__init__.py."""
    spec = importlib.util.spec_from_file_location(dotted_path, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
```

Alternatively, for the OSM parser and py3dtiles, we can add `blosm/parse/` and `blosm/threed_tiles/` to `sys.path` and import directly as `parse.osm` and `py3dtiles`. The implementation will determine the cleanest approach.

Within `blosm/threed_tiles/`, only `py3dtiles/` is safe. `blender.py`, `gltf_patch.py`, and `manager.py` all import `mathutils` or `bpy`. We do NOT import any of these.

### bpypolyskel adaptation scope

The straight skeleton library (`blosm/lib/bpypolyskel/`) has deeper mathutils usage than initially estimated. `bpyeuclid.py` contains 21 `mathutils` references including `mathutils.geometry.intersect_point_line` (a C extension method). We will write a complete numpy replacement for `bpyeuclid.py` (2D point/line/ray geometry, roughly 150 lines), then `bpypolyskel.py` can be used with minimal changes. This is a self-contained geometry module, not a thin adapter.

### BaseManager reimplementation

`blosm.threed_tiles.manager.BaseManager` uses `mathutils.Vector` and `mathutils.Matrix` throughout for ECEF coordinate math and bounding volume intersection. We reimplement the traversal logic in `tiles.py` using numpy, referencing the original algorithm. The key methods to port: `fromGeographic()`, bounding volume intersection (SAT for OBB-AABB, sphere-sphere, box-sphere), tile selection by geometric error.

## Coordinate system conventions

EnvironmentMesh stores vertices in **ENU (East-North-Up)** meters relative to `(origin_lat, origin_lon)`. All coordinate transforms happen at the boundaries:

| Boundary | From | To | Where |
|---|---|---|---|
| OSM input | WGS84 lat/lon | ENU meters | `osm.py` via `geo.py` |
| 3D Tiles input | ECEF | ENU meters | `tiles.py` via `geo.py` |
| DiffeRT export | ENU `[e, n, u]` | Z-up `[e, n, u]` | `export.py` (ENU is already Z-up) |
| Frontend binary | ENU `[e, n, u]` | Y-up `[e, u, -n]` | `export.py` via `geo.enu_to_yup()` |
| 3DTilesRendererJS | ECEF (handled by lib) | Screen | Client-side, no conversion needed |

The existing `scene_data.py` convention: Y-up `[x, y_up, z_horiz]` to Z-up `[x, -z_horiz, y_up]` in `prepare_for_raytracing()`. The environment module follows the same principle but with ENU as the canonical storage format. The swap to Y-up for frontend or Z-up for DiffeRT happens in `export.py`, never in the core dataclass.

## Threading and cache safety

All environment route handlers use `_cache_lock` (the existing `threading.RLock` from `server.py`) for cache mutations. Cache slots:

- `_cache["environment_mesh_osm"]` - last OSM-generated mesh
- `_cache["environment_mesh_tiles"]` - last 3D Tiles-generated mesh
- `_cache["environment_mesh_combined"]` - last combined mesh
- `_cache["environment_scene_path"]` - last exported DiffeRT/Sionna scene path

Long-running operations (Overpass fetch, 3D Tiles traversal) release the lock during network I/O and only hold it for the final cache write. If a second request arrives while the first is in progress, it waits for the lock on cache write, then overwrites.

`POST /api/environment/from-voxels` returns 404 with `{"error": "No voxels loaded"}` if `_cache["voxel_data"]` is absent.

## Overpass API error handling

`osm.py` sets a 60-second timeout on all Overpass requests. On failure:
- HTTP 429 (rate limited): return 503 with `Retry-After` header
- HTTP 504 or timeout: return 504 with message suggesting smaller radius
- Malformed XML: return 422
- Response size capped at 50MB (reject larger responses before parsing)

## `requests` dependency

`requests` must be added to the `viewer` optional extra in `pyproject.toml` (it is not currently in `[project.dependencies]` or the `viewer` extra).

## Frontend: `EastNorthUpFrame` coordinate convention

`EastNorthUpFrame` from `3d-tiles-renderer/r3f` takes lat/lon in **radians**, not degrees. The component must convert:

```tsx
<EastNorthUpFrame
  lat={location.lat * Math.PI / 180}
  lon={location.lon * Math.PI / 180}
>
```

## Frontend: `TilesPlugin` args memoization

The `args` object passed to `<TilesPlugin>` must be wrapped in `useMemo` to prevent plugin recreation on every render:

```tsx
const pluginArgs = useMemo(() => ({
  apiToken: apiKey,
  logoUrl: "/google-maps-logo.png",
}), [apiKey]);

<TilesPlugin plugin={GoogleCloudAuthPlugin} args={pluginArgs} />
```

## Frontend: camera mode interaction with follow mode

The existing camera system has `'orbit'` and `'follow'` modes. Adding `'globe'` creates a three-way branch:

- `'orbit'`: current OrbitControls + WASD physics (default)
- `'follow'`: FollowCamera tracks body (existing)
- `'globe'`: GlobeControls for earth-scale navigation (new)

Globe mode disables both OrbitControls and FollowCamera. Clicking any camera preset (front/side/top/focus/reset) switches back to `'orbit'`. The FollowCamera component already checks `cameraMode === 'follow'` internally, so adding `'globe'` does not require changes to FollowCamera.

## Frontend: Google Maps logo as bundled asset

The Google Maps logo must be bundled as a static asset (not fetched from an external URL) since the viewer may run in air-gapped or firewalled environments. Download the outlined Google Maps logo from Google's Map Tiles API policies page and place it at `aegis-web/public/google-maps-logo.png`. Reference as `logoUrl: "/google-maps-logo.png"`.

This is a **mandatory legal compliance requirement** per Google's Map Tiles API Terms of Service.

## Frontend: environment store hydration from config

On app load, the environment store initializes from `viewerConfig.environment`:

```typescript
// In useConfig.ts or equivalent initialization hook
useEffect(() => {
  if (viewerConfig?.environment) {
    const env = viewerConfig.environment;
    useEnvironmentStore.setState({
      source: env.source,
      location: env.location,
      radius: env.radius,
      geometricError: env.tiles.geometric_error,
      osmOptions: {
        defaultBuildingHeight: env.osm.default_building_height,
        levelHeight: env.osm.level_height,
        buildings: env.osm.buildings,
        roads: env.osm.roads,
        water: env.osm.water,
      },
    });
  }
}, [viewerConfig]);
```

This enables scenarios to preconfigure the environment source and location.

## Binary wire format details

All binary serialization uses **little-endian native byte order** via numpy `.tobytes()`, matching the existing pattern in `scene_data.py` and `raytracer.py`. The frontend reads with `new Float32Array(buffer)` etc. (also native LE on all target platforms).

The `to_binary()` method signature is `-> tuple[bytes, dict]` (binary data + metadata dict), consistent with `body_to_binary()` and `voxels_to_binary()`. The metadata goes in the `X-Meta` response header as JSON. The dataclass method `EnvironmentMesh.to_binary()` delegates to `export.to_binary(self)`.

## Material classification: relationship to existing system

Two material classification systems coexist:

- **Existing** (`scene_data.py`): `classify_material(r, g, b)` maps voxel RGB vertex colors to material names using HSV thresholds from `config.material_classification`. Output: string names ("concrete", "asphalt", etc.)
- **New** (`materials.py`): `MaterialType` enum maps to ITU-R P.2040 EM properties from `config.environment.materials`. Used by the environment module.

These are complementary. The existing system classifies voxel colors into material names. The new system maps material names to EM properties. When converting voxels to `EnvironmentMesh` via `from_voxels()`, the existing classification output feeds into the new `MaterialType` enum (string name lookup).

The HSV thresholds in `config.material_classification` are NOT duplicated. The environment module's `materials.py` only contains the EM property mapping. For 3D Tiles vertex color classification, `materials.py` reuses the same HSV rules by calling the existing `classify_material()` function from `scene_data.py`.
