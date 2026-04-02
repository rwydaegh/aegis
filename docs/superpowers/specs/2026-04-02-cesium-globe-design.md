# Cesium globe design

## Goal

Replace the broken `3d-tiles-renderer` globe with CesiumJS (via Resium) to get a proper Google Earth-quality globe experience. This fixes coordinate mismatch bugs in the coverage overlay, adds labels/roads/terrain, prevents camera clipping through the earth, and handles 800K coverage points natively.

## Architecture: two-canvas overlay

Two rendering layers stacked via CSS z-index inside a shared wrapper div:

```html
<div style="position: relative; width: 100%; height: 100%">
  <!-- Cesium Viewer: full globe, imagery, terrain, labels, coverage points -->
  <div style="position: absolute; inset: 0; z-index: 1">
    <CesiumGlobe />
  </div>
  <!-- R3F Canvas: dosimetry objects, transparent background -->
  <div style="position: absolute; inset: 0; z-index: 2; pointer-events: none">
    <Canvas gl={{ alpha: true }} style={{ background: 'transparent' }}>
      {sceneContent}
    </Canvas>
  </div>
</div>
```

The current `SceneRoot` wraps all scene content inside a single `<Canvas>`, with `Environment3DTiles` as a conditional parent component. The restructure extracts the `<Canvas>` out of its current position and places it as a sibling to the Cesium viewer. The `Environment3DTiles` wrapper (which provided `GlobeControls` and `EastNorthUpFrame` to its children) is removed entirely. Cesium handles globe navigation natively.

Pointer events flow through the transparent R3F canvas to Cesium underneath. When the user interacts with a dosimetry object (drag antenna, click body), the R3F layer captures events. Otherwise they fall through to Cesium.

Camera sync: Cesium is the camera authority. Each frame (via `viewer.clock.onTick`), the system reads the Cesium camera position/heading/pitch and applies it to the R3F camera. R3F OrbitControls are disabled when Cesium is active. When Cesium is not active (e.g. `source: osm` scenarios), OrbitControls work as before and the Cesium div is hidden.

## What changes

### Removed

- `3d-tiles-renderer` npm package
- `aegis-web/src/components/scene/Environment3DTiles.tsx` (replaced by CesiumGlobe)
- `aegis-web/src/components/scene/CoverageGlobe.tsx` (coverage rendering moves into CoverageOverlay3D as Cesium primitives)
- `aegis-web/src/components/scene/CoverageOverlay.tsx` (the existing R3F-based flat texture overlay, also replaced by CoverageOverlay3D)
- `GlobeControls`, `EastNorthUpFrame`, `GoogleCloudAuthPlugin` imports
- Manual ECEF computation in coverage store (`sitePositions`, `siteColors` Float32Arrays)
- Manual 3-tier LOD system (regions/clusters/sites tier switching)

### New files

| File | Responsibility |
|---|---|
| `aegis-web/src/components/scene/CesiumGlobe.tsx` | Cesium Viewer wrapper, base layers, Google 3D tiles, camera sync |
| `aegis-web/src/components/scene/CoverageOverlay3D.tsx` | Coverage points/lines/labels as Cesium primitives |
| `aegis-web/src/lib/cesium-camera-sync.ts` | Camera sync utility: Cesium to R3F each frame |

### Modified files

| File | Change |
|---|---|
| `aegis-web/package.json` | Add `cesium`, `resium`, `vite-plugin-cesium-build`. Remove `3d-tiles-renderer`. |
| `aegis-web/vite.config.ts` | Add cesium plugin |
| `aegis-web/src/main.tsx` | Import cesium widget CSS |
| `aegis-web/src/components/scene/SceneRoot.tsx` | Major restructure: extract the `<Canvas>` into a wrapper div that also contains `<CesiumGlobe>` as a sibling. Remove `Environment3DTiles` import and conditional wrapping. Remove `<CoverageGlobe />` and `<CoverageOverlay />` from scene content. |
| `aegis-web/src/stores/coverage.ts` | Remove ECEF pre-computation. Store raw lat/lon arrays. Remove `sitePositions`, `siteColors`, `activeTier`. |
| `aegis-web/src/components/hud/CoverageHud.tsx` | Read camera state from coverage store (unchanged API) |
| `aegis-web/src/hooks/useScenario.ts` | Coverage globe scenario sets `environment.source = 'cesium'` instead of `'3dtiles'` |
| `aegis-web/src/stores/environment.ts` | Add `'cesium'` to `EnvironmentSource` type |
| `src/aegis/viewer/config.py` | Update coverage_globe scenario webState to `source: "cesium"`, add cesium_ion_token |
| `src/aegis/viewer/routes/data.py` | Add `cesium_ion_token` to `/api/viewer-config` response (where capabilities are built) |

## CesiumGlobe component

This component replaces `Environment3DTiles`. It renders a Cesium `<Viewer>` with terrain and imagery.

### Base layers

- Cesium ion default imagery (Bing aerial with labels, roads, borders). Free tier, no API key needed.
- Cesium World Terrain with lighting. Also free via ion.

### Google Photorealistic 3D tiles (optional)

Loaded via `createGooglePhotorealistic3DTileset()` when `google_api_key` is available in capabilities. Falls back to Bing imagery if no Google key. The globe still works, just without 3D buildings at close zoom.

### Viewer configuration

Disable Cesium's default UI widgets that conflict with the AEGIS HUD:

```javascript
timeline: false
animation: false
baseLayerPicker: false
geocoder: false
homeButton: false
navigationHelpButton: false
sceneModePicker: false
fullscreenButton: false
vrButton: false
selectionIndicator: false
infoBox: false
```

Keep `creditDisplay` for attribution.

### Camera initialization

- Coverage globe scenario: `camera.flyTo()` to 20,000km altitude above lat=20, lon=10 (Europe/Africa view)
- Local scene scenarios: `camera.flyTo()` to the scenario's lat/lon at 800m altitude, pitch looking down

## Coverage overlay

A separate component `CoverageOverlay3D.tsx` adds coverage data as Cesium primitives. No more manual ECEF math or tier switching.

### Site points

`PointPrimitiveCollection` with one point per unique site. Position via `Cartesian3.fromDegrees(lon, lat, 100)` (100m above surface to avoid z-fighting). Color by operator index using the same 16-color palette.

`scaleByDistance` makes points large at close range and shrinks them at distance. `translucencyByDistance` fades points when very far away. Cesium handles LOD automatically.

### Region boundaries

`PolylineCollection` with colored lines per region bbox. Color by completeness (green >80%, amber 40-80%, red <40%). `distanceDisplayCondition` makes them visible only above 200km altitude.

### Region labels

`LabelCollection` with region name and antenna count at bbox center. `distanceDisplayCondition` makes them visible only above 500km altitude. `scaleByDistance` keeps them appropriately sized at all zoom levels.

### Why no more tiers

Cesium's primitive collections handle LOD natively via `scaleByDistance`, `translucencyByDistance`, and `distanceDisplayCondition`. 800K points in a `PointPrimitiveCollection` performs well without manual tier switching. The cluster layer (0.1-degree grid) is no longer needed because individual points are visible at all zoom levels with appropriate scaling.

## Camera sync: Cesium to R3F

File: `aegis-web/src/lib/cesium-camera-sync.ts`

Each frame, read Cesium camera state and convert to the R3F local coordinate system.

The key challenge: Cesium works in ECEF (positions in millions of meters from Earth center), while R3F works in a local ENU (East-North-Up) frame with the scene anchor at the origin and units in meters. A raw axis swap would place the R3F camera millions of meters from the origin.

The sync must:
1. Read Cesium camera position in ECEF (`camera.positionWC`)
2. Define an anchor point (the scene's lat/lon, also in ECEF)
3. Compute the camera's offset from anchor in the local ENU frame (east, north, up directions at the anchor)
4. Map ENU to Three.js Y-up: `threeX = east, threeY = up, threeZ = -north`
5. Apply heading/pitch/roll from Cesium as a quaternion

```typescript
function syncCamera(cesiumViewer, r3fCamera, anchorCartesian, enuTransform) {
  const camPos = cesiumViewer.scene.camera.positionWC
  // offset = camPos - anchor, in ECEF
  // localPos = enuTransform.inverseTransform(offset) -> [east, north, up]
  // r3fCamera.position.set(east, up, -north)
  // r3fCamera.quaternion from heading/pitch/roll
}
```

The ENU transform matrix is computed once when the anchor point (scene lat/lon) is set, using `Cesium.Transforms.eastNorthUpToFixedFrame()`.

This sync only matters when both canvases are active (local dosimetry mode). In globe-only mode (coverage browsing), the R3F canvas is hidden.

### When to sync

- `coverage_globe` scenario: R3F canvas hidden, no sync needed
- Local scene after "Set up scene here": both canvases active, sync every frame
- Other scenarios (`open_ground`, `urban_ghent` with `source: osm`): R3F only, Cesium hidden, no sync needed
- Scenarios with `source: 3dtiles`: Cesium visible + R3F overlay, sync active

## Coverage store changes

Remove ECEF pre-computation. The store becomes simpler.

### Removed fields

- `sitePositions: Float32Array` (ECEF positions, no longer needed)
- `siteColors: Float32Array` (RGB colors, no longer needed)
- `activeTier: 1 | 2 | 3` (Cesium handles LOD)
- `hoveredRegion: string | null` (unused)

### Kept fields

- `enabled`, `loaded`, `loading`
- `regions: RegionSummary[]`
- `clusters: ClusterPoint[]` (kept for potential future use, not rendered)
- `siteCount: number`
- `operatorNames: string[]`, `technologyNames: string[]`
- `cameraLatLon`, `cameraAltitude` (written by CesiumGlobe, read by HUD)

### New fields (replacing sitePositions/siteColors)

- `siteLats: Float32Array | null` - raw decoded latitudes from binary response
- `siteLons: Float32Array | null` - raw decoded longitudes from binary response
- `siteOpIndices: Uint8Array | null` - raw decoded operator indices from binary response

### Modified fetch()

The `fetch()` action decodes the binary sites but no longer converts to ECEF or computes colors. It stores raw lat/lon/opIndex arrays. The `CoverageOverlay3D` component reads these and creates Cesium primitives directly.

## Transition flow

Same UX as the current design, simpler implementation:

1. User clicks "Coverage globe" card on welcome screen.
2. Cesium globe appears at 20,000km altitude. Coverage points, region boundaries, and labels are visible.
3. User zooms in. Cesium handles LOD (points grow, labels fade). Google 3D buildings appear if API key is available.
4. Below 5km altitude, "Set up scene here" button appears in CoverageHud.
5. User clicks the button:
   - Read lat/lon from Cesium camera
   - Cesium stays visible but coverage overlay hides
   - R3F canvas activates with transparent background
   - Load base stations at current location
   - Camera sync starts
6. "Back to globe" button returns to coverage mode:
   - R3F canvas hides
   - Coverage overlay re-enables
   - Camera flies back to regional altitude

## Dependencies

### Add

- `cesium` (~v1.139)
- `resium` (~v1.20)
- `vite-plugin-cesium-build` (latest)

### Remove

- `3d-tiles-renderer` (no longer needed)

### Vite plugin

Verify the correct plugin name before installing. Candidates: `vite-plugin-cesium`, `vite-plugin-cesium-build`, or manual `vite-plugin-static-copy` setup. Check npm for the actively maintained option at implementation time.

### Bundle impact

CesiumJS JS bundle adds ~2.8MB gzipped. Additionally, CesiumJS ships static assets (Web Workers, imagery, CSS) that are copied to the build output, adding ~20-30MB uncompressed to the dist folder. These are loaded on demand, not upfront. The Docker image grows by this amount. Removing `3d-tiles-renderer` offsets about 200KB of the JS bundle.

### Environment source type

The `EnvironmentSource` type in `stores/environment.ts` is currently `'none' | 'voxels' | 'osm' | '3dtiles'`. Add `'cesium'` as a new value. The `coverage_globe` scenario sets `source: 'cesium'`. The old `'3dtiles'` value can remain for backward compatibility but `SceneRoot` should treat `'cesium'` and `'3dtiles'` identically (both render the Cesium globe).

## Environment variables

### Token delivery strategy

The Cesium ion token is delivered at runtime via the `/api/viewer-config` response (same pattern as `google_api_key`). This is the single source of truth. No `VITE_CESIUM_ION_TOKEN` compile-time variable.

The frontend reads `cesium_ion_token` from the viewer config on startup, then sets `Ion.defaultAccessToken` before creating the Cesium Viewer. This works in both dev mode (API proxy to Flask) and production (Flask serves the built frontend).

### Backend (Flask)

- `CESIUM_ION_TOKEN`: Read from environment, included in `/api/viewer-config` response via `routes/data.py`.
- `GOOGLE_API_KEY`: Already exists, optional, enables Google Photorealistic 3D tiles in Cesium.

### Production (Hetzner app.env)

Add `CESIUM_ION_TOKEN=eyJ...` to `/opt/aegis/app.env`.

### CI (GitHub Actions deploy.yml)

Add `CESIUM_ION_TOKEN` as a GitHub secret. Pass to Docker build via `--build-arg` or set in the server's `app.env` during deploy (same as other env vars).

## Error handling

- No Cesium ion token: Globe renders with a basic fallback (OpenStreetMap imagery or error message).
- No Google API key: Globe works with Bing imagery, just no 3D buildings at close zoom.
- Coverage endpoint fails: Globe still renders, just no coverage overlay.
- Camera sync failure: R3F objects may be misaligned. Log error, disable sync, show warning toast.

## Testing

### Backend

Existing `tests/test_coverage_endpoint.py` unchanged (backend is the same).

### Frontend

- TypeScript compilation (`tsc --noEmit`)
- Production build (`npm run build`)
- Visual smoke test: coverage globe loads, zoom works, transition works, other scenarios unaffected
