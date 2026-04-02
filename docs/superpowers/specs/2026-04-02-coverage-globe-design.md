# Coverage globe design

## Goal

Add a global coverage map to the AEGIS viewer that lets users browse all ~800K base station antennas across up to 13 regions on a 3D globe, then transition into the local dosimetry workflow at any location of interest.

## Context

AEGIS currently has ~800K antennas across 11 regions with merged Parquet files (2 more regions defined in `regions.yaml` but lacking data). The frontend is a local-scale dosimetry tool: users load a location, fetch nearby antennas, render detailed 3D panel antennas, and compute exposure. There is no global overview of dataset coverage.

The frontend already has an `Environment3DTiles` component that renders Google 3D Photorealistic Tiles on a globe with `GlobeControls`. This component wraps the entire scene in an ECEF coordinate frame. It currently requires a `location` (lat/lon) to render. The scenario system is configuration-driven: scenarios are defined in `config.py`, served as JSON, and rendered as cards on the welcome overlay.

An existing `CoverageOverlay.tsx` component in `aegis-web/src/components/scene/` renders a CloudRF coverage texture plane. This is unrelated to the global coverage map and remains unchanged. The new component is named `CoverageGlobe.tsx` to avoid confusion.

## Architecture

The feature has four parts:

1. A new `coverage_globe` scenario entry that activates the globe and coverage overlay
2. A backend endpoint that pre-computes coverage data at three granularity tiers
3. A frontend component that renders the appropriate tier based on camera altitude
4. A transition flow that takes the user from globe browsing into the local dosimetry scene

No changes to existing base station loading, rendering, or dosimetry workflows.

## Entry point: scenario integration

A new scenario `coverage_globe` is added to `config.py` DEFAULTS:

```python
"coverage_globe": {
    "label": "Coverage globe",
    "description": "Browse base station coverage worldwide",
    "icon": "globe",
    "instant": True,
    "autoCompute": False,
    "webState": {
        "antennaPos": None,
        "environment": {
            "source": "3dtiles",
            "lat": 0,
            "lon": 0,
        },
    },
}
```

The `webState` sets `lat: 0, lon: 0` as a default location. This satisfies the `Environment3DTiles` guard (`if (!location || !apiKey) return <>{children}</>` at line 96) so the globe renders. Note: `GlobeCameraInit` defaults to 800m altitude, which is street-level. The `CoverageGlobe` component must override the camera position on mount to a high altitude (e.g., `latLonToECEF(0, 0, 20_000_000)`) for the full-Earth view.

This appears as a 4th card on the welcome overlay. When clicked, `loadScenario("coverage_globe")` sets environment source to `3dtiles`, camera mode to `globe`, and enables the coverage overlay. No antenna, body, or dosimetry state is set.

The `WelcomeOverlay` component needs a 4th icon added to `ICON_MAP`: `"globe"` mapping to the `Globe` icon from lucide-react. The grid layout changes from `sm:grid-cols-3` to `sm:grid-cols-2 lg:grid-cols-4`.

The `useScenario` hook gets a hardcoded check: `if (name === 'coverage_globe') { useCoverageStore.getState().setEnabled(true); useCoverageStore.getState().fetch(); }`. On any other scenario load, it calls `useCoverageStore.getState().setEnabled(false)`. The welcome overlay is dismissed by the existing `setWelcomeDismissed(true)` call in `loadScenario`, and the `?scenario=coverage_globe` URL param persists across refreshes.

## Backend: coverage data endpoint

A new endpoint `GET /api/basestations/coverage` reads all merged Parquet files and returns pre-computed data at three tiers. The response is JSON with an embedded base64-encoded binary payload for tier 3.

### Tier 1: regions

For each region in `regions.yaml` that has a corresponding merged Parquet file in `data/basestations/merged/`, a summary object with: name, bbox (format: `[min_lon, max_lon, min_lat, max_lat]`, matching `regions.yaml`), total antenna count, and a completeness score (fraction of non-null values across key columns: Power, Azimuth, CenterHeight, Frequency, Gain).

Regions without a merged Parquet file (e.g., `canada`, `new_zealand`) are omitted silently.

Bboxes are read from `region.sources[0].bbox` in `regions.yaml` (the bbox field is nested inside each source entry, not at the region level). Regions whose sources lack a bbox field (e.g., `brussels`, `flanders`) have their bbox computed from the min/max latitude and longitude in the Parquet data, with 0.01-degree padding.

```json
{
  "regions": [
    {
      "name": "brussels",
      "label": "Brussels",
      "bbox": [4.25, 4.45, 50.78, 50.92],
      "count": 19873,
      "completeness": 1.0
    }
  ]
}
```

### Tier 2: clusters

All antenna positions spatially binned into a grid of 0.1-degree cells. Binning algorithm: `cell_lat = floor(lat / 0.1) * 0.1`, `cell_lon = floor(lon / 0.1) * 0.1`. Cell center is `cell + 0.05`. Each cell has: center lat/lon, antenna count, dominant operator name (mode), dominant technology name (mode). A few thousand items.

```json
{
  "clusters": [
    {
      "lat": 50.85,
      "lon": 4.35,
      "count": 342,
      "operator": "Proximus",
      "technology": "LTE"
    }
  ]
}
```

### Tier 3: sites

All unique site positions, deduplicated by `SiteCode` (taking the first occurrence). Each site has lat, lon, and indices into lookup tables for operator and technology.

Binary format encoded as base64 in the JSON response under `sites_b64`. Metadata in the `sites_meta` field.

```json
{
  "sites_meta": {
    "count": 45000,
    "operators": ["Proximus", "Orange", "Telenet", "Play", "T-Mobile"],
    "technologies": ["LTE", "5G", "GSM", "UMTS"]
  },
  "sites_b64": "<base64 string>"
}
```

The decoded binary is `count` records of 10 bytes each:
- `float32 latitude` (4 bytes, little-endian)
- `float32 longitude` (4 bytes, little-endian)
- `uint8 operator_index` (1 byte, index into operators array)
- `uint8 technology_index` (1 byte, index into technologies array)

Estimated ~45K unique sites = ~450 KB uncompressed, ~150 KB after base64 + gzip.

### Error handling

- If no merged Parquet files exist: return 200 with empty arrays (`regions: [], clusters: [], sites_meta.count: 0, sites_b64: ""`).
- If `regions.yaml` is missing: return 500 with `{"error": "regions.yaml not found"}`.
- If a Parquet file is corrupt: log warning, skip that region, continue with others.

### Caching

The endpoint caches its response after first computation. Parquet files do not change at runtime. The cache is built lazily on first request.

### Implementation location

New route file: `src/aegis/viewer/routes/coverage.py`, following the existing `register(app, cache, lock)` pattern used by other route files (not Flask Blueprints). Reads parquet files using the same `data/basestations/merged/` directory and `regions.yaml` config that the existing build pipeline uses.

## Frontend: coverage store

A new Zustand store `aegis-web/src/stores/coverage.ts`, separate from the existing `basestations.ts` store.

```typescript
interface RegionSummary {
  name: string
  label: string
  bbox: [number, number, number, number]  // [min_lon, max_lon, min_lat, max_lat]
  count: number
  completeness: number
}

interface ClusterPoint {
  lat: number
  lon: number
  count: number
  operator: string
  technology: string
}

interface CoverageState {
  enabled: boolean
  loaded: boolean
  loading: boolean
  regions: RegionSummary[]
  clusters: ClusterPoint[]
  sitePositions: Float32Array | null   // ECEF [x, y, z, x, y, z, ...] after conversion
  siteColors: Float32Array | null      // RGB [r, g, b, r, g, b, ...] derived from operator
  siteCount: number
  operatorNames: string[]
  technologyNames: string[]
  activeTier: 1 | 2 | 3
  hoveredRegion: string | null

  fetch: () => Promise<void>
  setEnabled: (v: boolean) => void
  setActiveTier: (t: 1 | 2 | 3) => void
  setHoveredRegion: (r: string | null) => void
}
```

The `fetch()` method calls `GET /api/basestations/coverage`, parses the JSON response, decodes the base64 site buffer, converts all lat/lon pairs to ECEF coordinates (one-time cost), and maps operator indices to RGB colors. The `latLonToECEF` function currently lives in `Environment3DTiles.tsx` as a module-private function. It should be extracted to a shared utility file `aegis-web/src/lib/geo.ts` and imported by both `Environment3DTiles.tsx` and the coverage store. Populates `sitePositions` and `siteColors` as pre-built `Float32Array`s ready for `BufferAttribute`. Subsequent enables just toggle `enabled` without refetching.

The `basestations.ts` store remains untouched. It manages the local scene's working antenna set for dosimetry. The two stores have zero coupling except during the transition to local scene (see "Transition to local scene" section).

## Frontend: CoverageGlobe component

A new component `aegis-web/src/components/scene/CoverageGlobe.tsx` renders inside the `Environment3DTiles` wrapper when `coverageStore.enabled` is true.

### Camera altitude detection

Each frame (via `useFrame`), the component reads the camera's distance to the Earth surface: `altitude = camera.position.length() - WGS84_A` (where `WGS84_A = 6378137.0`). This determines `activeTier`:

| Altitude | Tier | Constant name |
|---|---|---|
| > 2,000 km | 1 (regions) | `TIER1_ALTITUDE_M = 2_000_000` |
| 200 km - 2,000 km | 2 (clusters) | `TIER2_ALTITUDE_M = 200_000` |
| 5 km - 200 km | 3 (sites) | `TIER3_ALTITUDE_M = 200_000` (same threshold, tier 3 starts here) |
| < 5 km | 3 + transition button | `TRANSITION_ALTITUDE_M = 5_000` |

The tier is set via `coverageStore.setActiveTier()`. Thresholds are module-level constants.

### Tier 1 rendering: region boundaries and labels

For each region in `coverageStore.regions`:

- A `<Line>` component (from `@react-three/drei`) draws the bbox as a rectangle on the globe surface, with vertices offset ~500m above the surface to avoid z-fighting. The 5 vertices (4 corners + close) are computed from bbox `[min_lon, max_lon, min_lat, max_lat]` converted to ECEF.
- Color encodes completeness: green (`#22c55e`, completeness > 0.8), amber (`#f59e0b`, 0.4-0.8), red (`#ef4444`, < 0.4).
- A `<Html>` component (from `@react-three/drei`) renders a floating label at the bbox center with region name and count (e.g., "Brussels: 19,873").

Total: ~13 line loops + 13 HTML labels. Trivial render cost.

### Tier 2 rendering: cluster markers

A single `InstancedMesh` with a `CircleGeometry(1, 16)` base. Each instance is positioned at its cluster's ECEF coordinates (500m above surface), oriented tangent to the globe surface (normal pointing away from Earth center), scaled proportionally to `log2(count) * scaleFactor`, and colored by operator using a lookup table.

The instance matrices and colors are set once when data loads, stored as typed arrays. On tier switch, the mesh visibility toggles. No per-frame updates.

Region boundary outlines remain visible (from tier 1) as context.

Estimated instance count: 2,000-5,000. Well within instanced rendering limits.

### Tier 3 rendering: site dots

A single `<points>` element with a `BufferGeometry`:

- `BufferAttribute('position', coverageStore.sitePositions, 3)` for ECEF positions (pre-computed in store)
- `BufferAttribute('color', coverageStore.siteColors, 3)` for per-site RGB colors (pre-computed in store)

On tier switch, the points visibility toggles.

Estimated point count: ~45,000 unique sites. Single draw call, single vertex buffer.

Point size attenuates with camera distance using `sizeAttenuation: true` on the `PointsMaterial`, so dots appear larger as the user zooms in.

### Tier transitions

Switching tiers is toggling `visible` on three pre-built geometries. No geometry rebuilds, no data fetches. The transition is instantaneous.

## Transition to local scene

When the user is zoomed in below `TRANSITION_ALTITUDE_M` (5 km) and clicks "Set up scene here" in the HUD:

1. The current camera center lat/lon is captured by reverse-projecting the camera look-at point to WGS84.
2. `coverageStore.setEnabled(false)` hides the coverage overlay.
3. The environment store location is updated: `useEnvironmentStore.getState().setLocation(lat, lon)` (the `setLocation` function takes two separate number arguments, not an object).
4. The base stations are loaded explicitly by calling the `loadBasestations` API function with `{ location: { lat, lon }, radius_m: 500 }`. The `BaseStationsPanel` has its own local location state and does not auto-load from the environment store, so an explicit API call is needed. The sidebar panel is opened programmatically via `useUIStore.getState().setSidebarOpen(true)`.
5. The `BaseStationMarkers` component renders detailed 3D antennas.
6. The environment remains `3dtiles`, so the user sees Google tiles as context. They can switch to OSM or voxels for ray tracing via the environment panel.

Returning to the globe: click "Coverage Globe" in the scenario dropdown (toolbar), or a "Back to globe" button in the HUD. This re-enables the coverage overlay, clears the local base station data, and resets the camera.

## HUD additions

A new component `aegis-web/src/components/hud/CoverageHud.tsx`. A floating panel in the bottom-left corner. The component renders when `coverageStore.enabled` is true OR when the active scenario is `coverage_globe` (to handle the "returned to local scene" state).

- Region legend showing the 3 completeness colors (green/amber/red) with labels. Visible when `coverageStore.enabled` is true.
- "Set up scene here" button. Visible when `coverageStore.enabled` is true and camera altitude < `TRANSITION_ALTITUDE_M`.
- "Back to globe" button. Visible when `coverageStore.enabled` is false and the active scenario is `coverage_globe` (i.e., user has transitioned to local scene and can return).

This is an HTML `div` overlay positioned absolutely, similar to the existing `TilesAttributionOverlay` pattern. Not a Three.js element.

## Files to create or modify

### New files

| File | Purpose |
|---|---|
| `src/aegis/viewer/routes/coverage.py` | Backend coverage endpoint, 3-tier pre-computation |
| `aegis-web/src/stores/coverage.ts` | Coverage Zustand store |
| `aegis-web/src/components/scene/CoverageGlobe.tsx` | Main LOD overlay component (tier 1/2/3 rendering) |
| `aegis-web/src/components/hud/CoverageHud.tsx` | Floating HUD panel with legend and transition buttons |
| `aegis-web/src/api/coverage.ts` | API client for coverage endpoint |
| `aegis-web/src/lib/geo.ts` | Shared `latLonToECEF` and WGS84 constants, extracted from `Environment3DTiles.tsx` |

### Modified files

| File | Change |
|---|---|
| `src/aegis/viewer/config.py` | Add `coverage_globe` scenario to DEFAULTS |
| `src/aegis/viewer/server.py` | Register coverage routes via `register(app, cache, lock)` |
| `aegis-web/src/components/hud/WelcomeOverlay.tsx` | Add Globe icon to `ICON_MAP`, adjust grid to 4 columns |
| `aegis-web/src/hooks/useScenario.ts` | Add `if (name === 'coverage_globe')` block to call `coverageStore.setEnabled(true)` and `coverageStore.fetch()`. Add `else coverageStore.setEnabled(false)` for other scenarios. |
| `aegis-web/src/components/scene/SceneRoot.tsx` | Add `<CoverageGlobe />` render alongside existing scene content (always mounted, self-hides when `enabled` is false) |
| `aegis-web/src/api/types.ts` | Add `RegionSummary`, `ClusterPoint`, `CoverageResponse` TypeScript interfaces |
| `aegis-web/src/components/scene/Environment3DTiles.tsx` | Import `latLonToECEF` from `@/lib/geo` instead of defining locally |

### Unchanged

- `aegis-web/src/stores/basestations.ts` - no coupling with coverage store
- `aegis-web/src/components/scene/BaseStationMarkers.tsx` - used as-is for local scene (tier 4)
- `aegis-web/src/components/scene/PanelAntenna.tsx` - used as-is for local scene (tier 4)
- `aegis-web/src/components/scene/CoverageOverlay.tsx` - existing CloudRF overlay, unrelated
- All dosimetry, MIMO, and computation code - untouched

## Testing approach

### Backend

- Unit test for tier computation: load a test parquet with known data, verify region summaries, cluster bins, and site deduplication.
- Test binary serialization round-trip: write sites as binary, decode base64, verify lat/lon precision and index correctness.
- Test caching: second call returns same data without recomputation.
- Test missing data: no parquet files returns empty response, corrupt file skipped with warning.
- Test bbox computation: region without bbox in yaml gets bbox derived from data.

### Frontend

- Verify coverage store populates correctly from mock API response.
- Verify tier switching based on camera altitude thresholds.
- Visual smoke test: load coverage globe scenario, zoom through all tiers, verify no crashes or visual glitches.
- Verify transition: click "Set up scene here", confirm base station panel opens with correct lat/lon.

### Performance

- Measure frame rate with ~45K site dots rendered as Points geometry (target: 60 fps).
- Measure initial load time for coverage endpoint (target: < 2s including gzip transfer).
- Measure memory usage of coverage store with full dataset.

## Out of scope

- Filtering by operator/technology on the globe (v2 feature)
- Animated transitions between tiers (cross-fade, morphing)
- Live data updates (parquet files are static at runtime)
- Mobile-specific layout adjustments
- Search/geocoding within the globe view (users zoom manually)
- Rendering actual antenna patterns or element grids on the globe (that is tier 4, handled by existing components after transition)
