# Coverage map redesign implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the CesiumJS 3-tier LOD globe with Google Maps + deck.gl for a beautiful, performant coverage map showing 422K antenna sites as a GPU-accelerated density heatmap.

**Architecture:** Google Maps as base map (photorealistic 3D tiles, labels, borders). deck.gl GoogleMapsOverlay with HeatmapLayer (density at low zoom) and ScatterplotLayer (individual sites at high zoom). All 422K sites loaded as a single binary blob (~2MB gzipped). No tiles, no LOD tiers, no server-side aggregation.

**Tech Stack:** React 19, @vis.gl/react-google-maps, @deck.gl/core + layers + aggregation-layers + google-maps, Zustand, Flask backend (unchanged pattern)

**Spec:** `docs/superpowers/specs/2026-04-11-coverage-map-redesign.md`

---

## File structure

### New files
- `aegis-web/src/components/scene/CoverageMap.tsx` -- Google Maps + deck.gl overlay (replaces CesiumGlobe.tsx)
- `aegis-web/src/components/scene/coverageLayers.ts` -- deck.gl layer factory functions (HeatmapLayer, ScatterplotLayer, GeoJsonLayer)
- `aegis-web/src/components/hud/CoverageTooltip.tsx` -- Hover tooltip for sites and regions
- `aegis-web/src/data/regionBoundaries.json` -- Simplified Natural Earth GeoJSON for the 15 regions with data

### Modified files
- `aegis-web/package.json` -- Add deck.gl and Google Maps React dependencies
- `aegis-web/src/components/scene/SceneRoot.tsx` -- Swap CesiumGlobe for CoverageMap
- `aegis-web/src/stores/coverage.ts` -- Remove clusters, add zoom/hover/colorMode state
- `aegis-web/src/api/coverage.ts` -- Update binary decoder for extended format (12 bytes per site)
- `aegis-web/src/api/types.ts` -- Update CoverageResponse types (remove ClusterPoint, extend SitesMeta)
- `aegis-web/src/components/hud/CoverageHud.tsx` -- Adapt for Google Maps zoom levels, add color mode toggle
- `aegis-web/src/hooks/useScenario.ts` -- Change env source from 'cesium' to 'coverage' for coverage_globe
- `aegis-web/src/stores/environment.ts` -- Add 'coverage' to EnvironmentSource union, update geocodeAndFetch guard
- `src/aegis/viewer/routes/coverage.py` -- Remove cluster computation, extend binary format
- `src/aegis/viewer/config.py` -- Change coverage_globe scenario source from 'cesium' to 'coverage'
- `aegis-web/vite.config.ts` -- Remove vite-plugin-cesium import and plugin call
- `aegis-web/src/main.tsx` -- Remove cesium CSS import

### Removed files
- `aegis-web/src/components/scene/CoverageOverlay3D.ts` -- The 3-tier LOD system (replaced by deck.gl layers)

### Deferred removal (after verifying nothing else uses them)
- `cesium` and `resium` npm packages
- `aegis-web/src/components/scene/CesiumGlobe.tsx`

---

## Task 1: Install dependencies and verify Google Maps renders

**Files:**
- Modify: `aegis-web/package.json`

- [ ] **Step 1: Install npm packages**

```bash
cd aegis-web
npm install @vis.gl/react-google-maps @deck.gl/core @deck.gl/layers @deck.gl/aggregation-layers @deck.gl/google-maps
```

- [ ] **Step 2: Create a minimal CoverageMap smoke test**

Create `aegis-web/src/components/scene/CoverageMap.tsx` with just a Google Map rendering using the API key from capabilities:

```tsx
import { APIProvider, Map } from '@vis.gl/react-google-maps'
import { useSceneStore } from '@/stores/scene'

export function CoverageMap() {
  const googleApiKey = useSceneStore(s => s.capabilities?.google_api_key) ?? ''

  if (!googleApiKey) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-zinc-950 text-zinc-400 text-sm">
        Google API key not configured. Set GOOGLE_API_KEY on the server.
      </div>
    )
  }

  return (
    <APIProvider apiKey={googleApiKey}>
      <Map
        style={{ width: '100%', height: '100%' }}
        defaultCenter={{ lat: 48.8, lng: 2.3 }}
        defaultZoom={4}
        mapId="DEMO_MAP_ID"
        mapTypeId="hybrid"
        disableDefaultUI
      />
    </APIProvider>
  )
}
```

- [ ] **Step 3: Wire into SceneRoot temporarily for visual verification**

In `SceneRoot.tsx`, add a temporary import and render `<CoverageMap />` alongside the CesiumGlobe div to verify Google Maps loads. Check the browser console for errors. Verify you see a Google Maps satellite view.

- [ ] **Step 4: Verify photorealistic 3D tiles appear when zooming in**

Zoom into a major city (Paris, London). Verify that 3D photorealistic buildings appear at street level. This should happen automatically with Google Maps when using a vector map (`mapId` required). If buildings don't appear, try removing the `mapId` or using `mapTypeId: 'satellite'`.

- [ ] **Step 5: Revert the temporary SceneRoot change, commit**

```bash
git add aegis-web/package.json aegis-web/package-lock.json aegis-web/src/components/scene/CoverageMap.tsx
git commit -m "Add Google Maps + deck.gl dependencies and CoverageMap skeleton"
```

---

## Task 2: Update backend to extended binary format

**Files:**
- Modify: `src/aegis/viewer/routes/coverage.py`

- [ ] **Step 1: Extend binary format to 12 bytes per site**

In `_compute_coverage()`, add `region_index` and `antenna_count` to the binary packing. Remove the cluster computation entirely:

```python
# After deduplication, compute per-site antenna counts
if "SiteCode" in combined.columns:
    site_counts = combined.groupby("SiteCode").size()
    sites = combined.drop_duplicates(subset="SiteCode", keep="first")
    antenna_counts = sites["SiteCode"].map(site_counts).clip(upper=255).to_numpy(dtype=np.uint8)
else:
    sites = combined.drop_duplicates(subset=["Latitude", "Longitude"], keep="first")
    antenna_counts = np.ones(len(sites), dtype=np.uint8)

# Build region index: which region does each site come from
# (Track region assignment during the concat loop above)
```

Update the struct to pack 12 bytes: `lat(f32) + lon(f32) + op(u1) + tech(u1) + region(u1) + antenna_count(u1)`.

Remove all cluster computation code (the `grouped = combined.groupby(["_cell_lat", "_cell_lon"])` block and everything that builds the `clusters` list).

Remove `clusters` from the response dict. Add `regions` list to `sites_meta`.

- [ ] **Step 2: Run lint and verify endpoint still works**

```bash
python -m ruff check src/aegis/viewer/routes/coverage.py
python -m ruff format src/aegis/viewer/routes/coverage.py
```

Start the Flask server and curl the endpoint to verify the response shape:

```bash
curl -s http://localhost:5000/api/basestations/coverage | python3 -c "import sys, json; d = json.load(sys.stdin); print('regions:', len(d['regions'])); print('sites:', d['sites_meta']['count']); print('b64 len:', len(d['sites_b64'])); print('keys:', list(d.keys()))"
```

Expected: regions count, ~422K sites, no `clusters` key.

- [ ] **Step 3: Commit**

```bash
git add src/aegis/viewer/routes/coverage.py
git commit -m "Extend coverage binary to 12 bytes/site, remove cluster computation"
```

---

## Task 3: Update frontend types and binary decoder

**Files:**
- Modify: `aegis-web/src/api/types.ts`
- Modify: `aegis-web/src/api/coverage.ts`
- Modify: `aegis-web/src/stores/coverage.ts`

- [ ] **Step 1: Update types**

In `aegis-web/src/api/types.ts`:
- Remove the `ClusterPoint` interface entirely
- Add `region_names: string[]` to `CoverageSitesMeta`
- Remove `clusters` from `CoverageResponse`

```typescript
export interface CoverageSitesMeta {
  count: number
  operators: string[]
  technologies: string[]
  region_names: string[]
}

export interface CoverageResponse {
  regions: RegionSummary[]
  sites_meta: CoverageSitesMeta
  sites_b64: string
}
```

- [ ] **Step 2: Update binary decoder**

In `aegis-web/src/api/coverage.ts`, update `decodeSitesBinary` to decode 12 bytes per site:

```typescript
export function decodeSitesBinary(
  b64: string,
  count: number,
): {
  latitudes: Float32Array
  longitudes: Float32Array
  opIndices: Uint8Array
  techIndices: Uint8Array
  regionIndices: Uint8Array
  antennaCounts: Uint8Array
} {
  const raw = Uint8Array.from(atob(b64), c => c.charCodeAt(0))
  const latitudes = new Float32Array(count)
  const longitudes = new Float32Array(count)
  const opIndices = new Uint8Array(count)
  const techIndices = new Uint8Array(count)
  const regionIndices = new Uint8Array(count)
  const antennaCounts = new Uint8Array(count)

  const view = new DataView(raw.buffer)
  for (let i = 0; i < count; i++) {
    const offset = i * 12
    latitudes[i] = view.getFloat32(offset, true)
    longitudes[i] = view.getFloat32(offset + 4, true)
    opIndices[i] = raw[offset + 8]
    techIndices[i] = raw[offset + 9]
    regionIndices[i] = raw[offset + 10]
    antennaCounts[i] = raw[offset + 11]
  }

  return { latitudes, longitudes, opIndices, techIndices, regionIndices, antennaCounts }
}
```

- [ ] **Step 3: Update coverage store**

In `aegis-web/src/stores/coverage.ts`:
- Remove `clusters: ClusterPoint[]` from state and initial values
- Add `siteRegionIndices: Uint8Array | null`, `siteAntennaCounts: Uint8Array | null`
- Add `regionNames: string[]`
- Add `zoom: number` (default 3), `hoveredSiteIndex: number | null`, `selectedSiteIndex: number | null`
- Add `colorMode: 'density' | 'operator' | 'technology' | 'region'` (default 'density')
- Add setters: `setZoom`, `setHoveredSiteIndex`, `setSelectedSiteIndex`, `setColorMode`
- Update `fetch()` to decode the new fields and remove cluster handling
- Remove `setCameraAltitude` and `setCameraLatLon` (replaced by zoom)

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd aegis-web && npx tsc --noEmit 2>&1 | head -30
```

Fix any type errors. The main breakages will be in `CoverageOverlay3D.ts` (which imports ClusterPoint) and `CesiumGlobe.tsx` (which reads clusters from store). These files are being replaced, so either fix temporarily or delete them now.

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/api/types.ts aegis-web/src/api/coverage.ts aegis-web/src/stores/coverage.ts
git commit -m "Update coverage types and decoder for 12-byte binary format"
```

---

## Task 4: Build the deck.gl layer factory

**Files:**
- Create: `aegis-web/src/components/scene/coverageLayers.ts`

- [ ] **Step 1: Create the layer factory module**

This module exports a function that takes coverage store state and zoom level, and returns an array of deck.gl layers. Keeping layer construction separate from the React component makes it testable and keeps CoverageMap.tsx focused on the Google Maps integration.

```typescript
import { HeatmapLayer } from '@deck.gl/aggregation-layers'
import { ScatterplotLayer, GeoJsonLayer } from '@deck.gl/layers'

// Operator color palette (same as existing CoverageOverlay3D.ts, converted to RGBA arrays)
const OP_COLORS: [number, number, number, number][] = [
  [59, 130, 245, 255],
  [245, 130, 28, 255],
  [46, 194, 125, 255],
  // ... (carry over all 16 colors from CoverageOverlay3D.ts)
]

// Plasma-inspired color ramp for heatmap (6 stops)
const HEATMAP_COLOR_RANGE: [number, number, number][] = [
  [13, 8, 135],     // deep purple
  [126, 3, 168],    // purple
  [204, 71, 120],   // magenta
  [248, 149, 64],   // orange
  [252, 225, 56],   // yellow
  [240, 249, 33],   // bright yellow
]

interface CoverageLayerParams {
  siteLats: Float32Array
  siteLons: Float32Array
  siteOpIndices: Uint8Array
  siteTechIndices: Uint8Array
  siteRegionIndices: Uint8Array
  siteAntennaCounts: Uint8Array
  siteCount: number
  zoom: number
  colorMode: 'density' | 'operator' | 'technology' | 'region'
  onSiteHover: (info: any) => void
  onSiteClick: (info: any) => void
}

export function buildCoverageLayers(params: CoverageLayerParams) {
  const {
    siteLats, siteLons, siteOpIndices, siteAntennaCounts,
    siteCount, zoom, colorMode, onSiteHover, onSiteClick,
  } = params

  // HeatmapLayer (GPU aggregation) does NOT support {length} + callback accessors.
  // It needs an array of objects. 422K objects is fine (~30MB, created once).
  // ScatterplotLayer supports {length} with indexed accessors.
  const heatmapData: { position: [number, number]; weight: number }[] = []
  if (zoom < 12) {
    for (let i = 0; i < siteCount; i++) {
      heatmapData.push({
        position: [siteLons[i], siteLats[i]],
        weight: siteAntennaCounts[i] || 1,
      })
    }
  }

  // ScatterplotLayer can use {length} with indexed accessors (efficient, no object creation)
  const scatterData = { length: siteCount }

  // Heatmap: visible zoom 0-12, fades out 8-12
  const heatmapOpacity = zoom <= 8 ? 0.8 : zoom >= 12 ? 0 : 0.8 * (12 - zoom) / 4

  // Scatter: visible zoom 8+, fades in 8-12
  const scatterOpacity = zoom <= 8 ? 0 : zoom >= 12 ? 0.9 : 0.9 * (zoom - 8) / 4

  const layers = []

  if (heatmapOpacity > 0) {
    layers.push(new HeatmapLayer({
      id: 'antenna-heatmap',
      data: heatmapData,
      getPosition: (d: any) => d.position,
      getWeight: (d: any) => d.weight,
      radiusPixels: Math.max(15, 50 - zoom * 3),
      intensity: 1 + zoom * 0.3,
      threshold: 0.05,
      colorRange: HEATMAP_COLOR_RANGE,
      aggregation: 'SUM',
      opacity: heatmapOpacity,
      debounceTimeout: 200,
    }))
  }

  if (scatterOpacity > 0) {
    layers.push(new ScatterplotLayer({
      id: 'antenna-sites',
      data: scatterData,
      getPosition: (_, { index }) => [siteLons[index], siteLats[index]],
      getRadius: 50,
      radiusMinPixels: 3,
      radiusMaxPixels: 15,
      getFillColor: (_, { index }) => {
        if (colorMode === 'operator') return OP_COLORS[siteOpIndices[index] % OP_COLORS.length]
        if (colorMode === 'technology') return OP_COLORS[siteTechIndices[index] % OP_COLORS.length]
        if (colorMode === 'region') return OP_COLORS[siteRegionIndices[index] % OP_COLORS.length]
        return [59, 130, 245, 220]
      },
      pickable: true,
      onHover: onSiteHover,
      onClick: onSiteClick,
      opacity: scatterOpacity,
      updateTriggers: {
        getFillColor: [colorMode],
      },
    }))
  }

  return layers
}
```

Note: The heatmapData array is rebuilt when zoom crosses the threshold. At 422K entries this takes ~20ms. Cache it in the component (useMemo) so it's only rebuilt when the underlying data changes, not on every zoom tick.

- [ ] **Step 2: Verify the module imports resolve**

```bash
cd aegis-web && npx tsc --noEmit 2>&1 | grep coverageLayers
```

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/scene/coverageLayers.ts
git commit -m "Add deck.gl coverage layer factory with heatmap and scatter layers"
```

---

## Task 5: Build the CoverageMap component

**Files:**
- Modify: `aegis-web/src/components/scene/CoverageMap.tsx` (replace skeleton from Task 1)

- [ ] **Step 1: Implement full CoverageMap with deck.gl overlay**

Replace the skeleton `CoverageMap.tsx` with the full implementation:

```tsx
import { useCallback, useEffect, useState } from 'react'
import { APIProvider, Map, useMap } from '@vis.gl/react-google-maps'
import { GoogleMapsOverlay } from '@deck.gl/google-maps'
import { useSceneStore } from '@/stores/scene'
import { useCoverageStore } from '@/stores/coverage'
import { buildCoverageLayers } from './coverageLayers'

function DeckOverlay() {
  const map = useMap()
  const [overlay] = useState(() => new GoogleMapsOverlay({}))

  // Read coverage data from store
  const siteLats = useCoverageStore(s => s.siteLats)
  const siteLons = useCoverageStore(s => s.siteLons)
  const siteOpIndices = useCoverageStore(s => s.siteOpIndices)
  const siteTechIndices = useCoverageStore(s => s.siteTechIndices)
  const siteRegionIndices = useCoverageStore(s => s.siteRegionIndices)
  const siteAntennaCounts = useCoverageStore(s => s.siteAntennaCounts)
  const siteCount = useCoverageStore(s => s.siteCount)
  const zoom = useCoverageStore(s => s.zoom)
  const colorMode = useCoverageStore(s => s.colorMode)
  const setHoveredSiteIndex = useCoverageStore(s => s.setHoveredSiteIndex)
  const setSelectedSiteIndex = useCoverageStore(s => s.setSelectedSiteIndex)

  // Attach overlay to map
  useEffect(() => {
    if (map) overlay.setMap(map)
    return () => overlay.setMap(null)
  }, [map, overlay])

  // Track zoom level from Google Maps
  useEffect(() => {
    if (!map) return
    const listener = map.addListener('zoom_changed', () => {
      const z = map.getZoom()
      if (z != null) useCoverageStore.getState().setZoom(z)
    })
    // Set initial zoom
    const z = map.getZoom()
    if (z != null) useCoverageStore.getState().setZoom(z)
    return () => listener.remove()
  }, [map])

  // Hover/click handlers
  const onSiteHover = useCallback((info: any) => {
    setHoveredSiteIndex(info.index >= 0 ? info.index : null)
  }, [setHoveredSiteIndex])

  const onSiteClick = useCallback((info: any) => {
    if (info.index >= 0) setSelectedSiteIndex(info.index)
  }, [setSelectedSiteIndex])

  // Update deck.gl layers when data or zoom changes
  useEffect(() => {
    if (!siteLats || !siteLons || !siteOpIndices || !siteTechIndices || !siteRegionIndices || !siteAntennaCounts) {
      overlay.setProps({ layers: [] })
      return
    }

    const layers = buildCoverageLayers({
      siteLats, siteLons, siteOpIndices, siteTechIndices,
      siteRegionIndices, siteAntennaCounts,
      siteCount, zoom, colorMode,
      onSiteHover, onSiteClick,
    })

    overlay.setProps({ layers })
  }, [siteLats, siteLons, siteOpIndices, siteTechIndices, siteRegionIndices,
      siteAntennaCounts, siteCount, zoom, colorMode, overlay, onSiteHover, onSiteClick])

  return null
}

export function CoverageMap() {
  const googleApiKey = useSceneStore(s => s.capabilities?.google_api_key) ?? ''

  if (!googleApiKey) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-zinc-950 text-zinc-400 text-sm">
        Google API key not configured. Set GOOGLE_API_KEY on the server.
      </div>
    )
  }

  return (
    <APIProvider apiKey={googleApiKey}>
      <Map
        style={{ width: '100%', height: '100%' }}
        defaultCenter={{ lat: 48.8, lng: 2.3 }}
        defaultZoom={4}
        mapTypeId="hybrid"
        mapId={import.meta.env.VITE_GOOGLE_MAP_ID || undefined}
        disableDefaultUI
        gestureHandling="greedy"
        clickableIcons={false}
      />
      <DeckOverlay />
    </APIProvider>
  )
}
```

Key details:
- `APIProvider` wraps the whole component (required by @vis.gl/react-google-maps)
- `DeckOverlay` is a child component that uses `useMap()` hook to get the Google Maps instance
- `GoogleMapsOverlay` bridges deck.gl layers onto Google Maps
- Zoom tracking via Google Maps `zoom_changed` event updates the coverage store
- Layer rebuilding is triggered by store changes via useEffect

- [ ] **Step 2: Verify it renders in the browser**

Temporarily render CoverageMap in the app to see Google Maps with deck.gl. Open browser dev tools, check for errors. If `mapId` is needed for vector mode (interleaved deck.gl), create one in Google Cloud Console or test without it first (overlaid mode).

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/scene/CoverageMap.tsx
git commit -m "Implement CoverageMap with Google Maps + deck.gl overlay"
```

---

## Task 6: Wire CoverageMap into SceneRoot

**Files:**
- Modify: `aegis-web/src/components/scene/SceneRoot.tsx`
- Modify: `aegis-web/src/stores/environment.ts`
- Modify: `aegis-web/src/hooks/useScenario.ts`

- [ ] **Step 1: Add 'coverage' to EnvironmentSource**

In `aegis-web/src/stores/environment.ts`, change the union type:

```typescript
export type EnvironmentSource = 'none' | 'voxels' | 'osm' | '3dtiles' | 'cesium' | 'coverage'
```

- [ ] **Step 2: Update backend config to use 'coverage' source**

In `src/aegis/viewer/config.py` line 561, change the coverage_globe scenario's environment source:
```python
# Old:
"source": "cesium",
# New:
"source": "coverage",
```

This is critical: the frontend reads `webState.environment.source` from this config. Without this change, `envSource` stays `'cesium'` and `isCoverageMode` is never true.

- [ ] **Step 2b: Update environment.ts geocodeAndFetch guard**

In `aegis-web/src/stores/environment.ts` line 105, add `'coverage'` to the allowed sources:
```typescript
// Old:
if (source !== 'osm' && source !== '3dtiles' && source !== 'cesium') return
// New:
if (source !== 'osm' && source !== '3dtiles' && source !== 'coverage') return
```

Without this, geocoding (location search) silently fails in coverage mode.

- [ ] **Step 3: Swap CesiumGlobe for CoverageMap in SceneRoot**

In `SceneRoot.tsx`:

1. Replace `import { CesiumGlobe } from './CesiumGlobe'` with `import { CoverageMap } from './CoverageMap'`
2. Change `const isCesiumMode = envSource === 'cesium'` to `const isCoverageMode = envSource === 'coverage'`
3. Replace all `isCesiumMode` references with `isCoverageMode`
4. Replace the CesiumGlobe div:

```tsx
{isCoverageMode && (
  <div style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
    <CoverageMap />
  </div>
)}
```

5. The Three.js Canvas gets `pointerEvents: isCoverageMode ? 'none' : 'auto'` (same pattern as before)

- [ ] **Step 4: Update CoverageHud handleBackToGlobe**

In `CoverageHud.tsx`, change:
```typescript
// Old:
useEnvironmentStore.getState().setSource('cesium')
// New:
useEnvironmentStore.getState().setSource('coverage')
```

- [ ] **Step 5: Test the full flow in the browser**

1. Load the app, select the coverage_globe scenario
2. Verify Google Maps appears with the heatmap layer
3. Zoom in and verify scatter dots appear
4. Click "Set up scene here" and verify it transitions to the Three.js local view
5. Click "Back to globe" and verify it returns to the coverage map

- [ ] **Step 6: Commit**

```bash
git add aegis-web/src/components/scene/SceneRoot.tsx aegis-web/src/stores/environment.ts aegis-web/src/hooks/useScenario.ts aegis-web/src/components/hud/CoverageHud.tsx
git commit -m "Wire CoverageMap into SceneRoot, replace CesiumGlobe rendering path"
```

---

## Task 7: Build the hover tooltip

**Files:**
- Create: `aegis-web/src/components/hud/CoverageTooltip.tsx`
- Modify: `aegis-web/src/components/layout/HudOverlay.tsx`

- [ ] **Step 1: Create CoverageTooltip component**

A positioned tooltip that appears near the cursor when hovering a site on the coverage map. Reads `hoveredSiteIndex` from the coverage store and displays site info.

```tsx
import { useCoverageStore } from '@/stores/coverage'

export function CoverageTooltip() {
  const hoveredIndex = useCoverageStore(s => s.hoveredSiteIndex)
  const siteLats = useCoverageStore(s => s.siteLats)
  const siteLons = useCoverageStore(s => s.siteLons)
  const siteOpIndices = useCoverageStore(s => s.siteOpIndices)
  const siteAntennaCounts = useCoverageStore(s => s.siteAntennaCounts)
  const operatorNames = useCoverageStore(s => s.operatorNames)
  // ... read cursor position from a ref or store

  if (hoveredIndex == null || !siteLats || !siteOpIndices) return null

  const lat = siteLats[hoveredIndex]
  const lon = siteLons[hoveredIndex]
  const operator = operatorNames[siteOpIndices[hoveredIndex]] ?? 'Unknown'
  const antennaCount = siteAntennaCounts?.[hoveredIndex] ?? 1

  return (
    <div
      className="pointer-events-none fixed z-50 rounded-lg bg-zinc-900/95 border border-zinc-700 p-2.5 text-xs text-white shadow-xl"
      style={{ left: cursorX + 12, top: cursorY - 20 }}
    >
      <div className="font-medium">{operator}</div>
      <div className="text-zinc-400">{antennaCount} antenna{antennaCount !== 1 ? 's' : ''}</div>
      <div className="text-zinc-500">{lat.toFixed(4)}, {lon.toFixed(4)}</div>
    </div>
  )
}
```

Note: The cursor position needs to come from the deck.gl `onHover` callback's `info.x` / `info.y` (screen coordinates). Store these in the coverage store alongside `hoveredSiteIndex`, or pass via a ref. The exact approach depends on what deck.gl provides in the `info` object.

- [ ] **Step 2: Add CoverageTooltip to HudOverlay**

In `aegis-web/src/components/layout/HudOverlay.tsx`, import and render `<CoverageTooltip />` alongside the existing HUD components.

- [ ] **Step 3: Test tooltip in browser**

Hover over antenna sites at city zoom. Verify tooltip appears with operator name, antenna count, and coordinates. Verify it follows the cursor smoothly. Verify it disappears when moving off a site.

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/hud/CoverageTooltip.tsx aegis-web/src/components/layout/HudOverlay.tsx
git commit -m "Add hover tooltip for coverage map sites"
```

---

## Task 8: Add color mode toggle to CoverageHud

**Files:**
- Modify: `aegis-web/src/components/hud/CoverageHud.tsx`

- [ ] **Step 1: Add color mode selector**

Add a dropdown or segmented control to CoverageHud that lets the user switch between color modes: Density (heatmap), Operator, Technology, Region. This updates `colorMode` in the coverage store, which triggers layer rebuilding in CoverageMap.

```tsx
const colorMode = useCoverageStore(s => s.colorMode)
const setColorMode = useCoverageStore(s => s.setColorMode)

// In the JSX:
<select
  value={colorMode}
  onChange={e => setColorMode(e.target.value as any)}
  className="bg-zinc-800 border border-zinc-600 rounded text-xs px-2 py-1"
>
  <option value="density">Density heatmap</option>
  <option value="operator">By operator</option>
  <option value="technology">By technology</option>
  <option value="region">By country</option>
</select>
```

- [ ] **Step 2: Update coverageLayers.ts getFillColor for all color modes**

In the ScatterplotLayer's `getFillColor` accessor, handle all four modes:
- `density`: single blue color (heatmap does the density communication)
- `operator`: color by operator index (existing palette)
- `technology`: color by technology index (new palette or reuse)
- `region`: color by region index

Update the `updateTriggers` to include `colorMode`.

- [ ] **Step 3: Update CoverageHud transition button to use zoom**

Replace the altitude-based transition check with zoom-based:

```tsx
const zoom = useCoverageStore(s => s.zoom)
const showTransitionButton = enabled && zoom >= 14 && cameraLatLon
```

The `cameraLatLon` can be read from the Google Maps center via the store, or computed from the map's `center_changed` event.

- [ ] **Step 4: Test color mode switching**

Toggle between color modes in the browser. Verify instant color changes on the scatter layer. Verify the heatmap layer is only visible in 'density' mode (or always visible as a base with scatter on top in other modes -- decide based on what looks best).

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/components/hud/CoverageHud.tsx aegis-web/src/components/scene/coverageLayers.ts
git commit -m "Add color mode toggle and zoom-based transition to CoverageHud"
```

---

## Task 9: Clean up old CesiumJS code

**Files:**
- Remove: `aegis-web/src/components/scene/CoverageOverlay3D.ts`
- Modify: `aegis-web/src/components/scene/CesiumGlobe.tsx` (verify nothing else imports it, then remove)

- [ ] **Step 1: Check for remaining CesiumJS imports**

```bash
cd aegis-web && grep -r "CesiumGlobe\|CoverageOverlay3D\|resium\|from 'cesium'" src/ --include='*.ts' --include='*.tsx' | grep -v node_modules
```

If only SceneRoot.tsx imported CesiumGlobe (already replaced in Task 6), and only CesiumGlobe imported CoverageOverlay3D, both files can be safely removed.

- [ ] **Step 2: Remove old files**

```bash
rm aegis-web/src/components/scene/CoverageOverlay3D.ts
rm aegis-web/src/components/scene/CesiumGlobe.tsx
```

- [ ] **Step 3: Remove Cesium from Vite config and main.tsx**

In `aegis-web/vite.config.ts`:
- Remove `import cesium from 'vite-plugin-cesium'` (line 5)
- Remove `cesium()` from the plugins array (line 15)

In `aegis-web/src/main.tsx`:
- Remove `import 'cesium/Build/Cesium/Widgets/widgets.css'` (line 4)

These imports will cause build failures after the packages are removed.

- [ ] **Step 4: Remove cesium, resium, and vite-plugin-cesium packages**

Check if any other component still imports from cesium or resium:

```bash
grep -r "from 'cesium'\|from 'resium'" aegis-web/src/ --include='*.ts' --include='*.tsx'
```

If no remaining imports, remove all three packages:

```bash
cd aegis-web && npm uninstall cesium resium vite-plugin-cesium
```

- [ ] **Step 5: Verify build**

```bash
cd aegis-web && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add -A aegis-web/
git commit -m "Remove CesiumJS globe and 3-tier LOD overlay"
```

---

## Task 10: Visual tuning and polish

**Files:**
- Modify: `aegis-web/src/components/scene/coverageLayers.ts`
- Modify: `aegis-web/src/components/scene/CoverageMap.tsx`
- Modify: `aegis-web/src/components/hud/CoverageTooltip.tsx`

- [ ] **Step 1: Tune heatmap parameters**

Open the coverage map in the browser. Adjust these parameters until the visualization looks right:

- `radiusPixels`: controls how wide each point's influence is. Too large = uniform wash. Too small = dots. Start with `Math.max(15, 50 - zoom * 3)` and adjust.
- `intensity`: controls brightness. Should make Paris glow bright without making rural France invisible.
- `threshold`: controls minimum density to show. 0.05 is a good start. Increase if too much background noise.
- `colorRange`: the plasma ramp should give good contrast on satellite imagery. Try magma if plasma is too bright.
- `opacity`: the heatmap should be semi-transparent so the satellite map shows through.

- [ ] **Step 2: Tune scatter layer appearance**

At city zoom (12+):
- Dots should be small enough not to overlap in suburbs, large enough to click in cities
- `radiusMinPixels: 3` and `radiusMaxPixels: 15` are good starting points
- Add a subtle outline (via `getLineColor` and `lineWidthMinPixels`) for better contrast on satellite imagery

- [ ] **Step 3: Tune cross-fade transition**

Zoom slowly from continental to city view. The heatmap should fade smoothly into individual dots with no jarring pop. Adjust the zoom thresholds (currently 8-12) if the transition feels too early or too late.

- [ ] **Step 4: Test on different regions**

Check that the visualization looks good for:
- Dense areas: Paris, Flanders (should glow hot)
- Sparse areas: rural Australia (should show faint dots)
- Mixed: Germany (Berlin hot, rural Saxony faint)
- Edge case: Brussels (tiny region, very dense)

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/components/scene/coverageLayers.ts
git commit -m "Tune heatmap and scatter layer visual parameters"
```

---

## Task 11: Final integration test and PR

- [ ] **Step 1: Run full QA checklist**

Test the complete flow:
1. Load app -> coverage_globe scenario loads -> Google Maps appears with heatmap
2. Pan/zoom at continental level -> smooth 60fps, density visible
3. Zoom into Paris -> heatmap fades, individual dots appear
4. Hover a dot -> tooltip shows operator, antenna count
5. Toggle color modes -> instant color change
6. Zoom to street level -> Google 3D buildings visible
7. Click "Set up scene here" -> transitions to local Three.js view
8. Click "Back to globe" -> returns to coverage map
9. All other scenarios (empty, local scenes) still work normally

- [ ] **Step 2: Run lint**

```bash
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/
cd aegis-web && npx tsc --noEmit
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/ -m "not slow" -x
```

- [ ] **Step 4: Build production frontend**

```bash
cd aegis-web && npm run build
```

- [ ] **Step 5: Create PR**

```bash
git checkout -b feature/coverage-map-redesign
git push -u origin feature/coverage-map-redesign
gh pr create --title "Replace CesiumJS globe with Google Maps + deck.gl coverage map" --body "## Summary
- Replace CesiumJS 3-tier LOD globe with Google Maps + deck.gl
- GPU-accelerated heatmap layer for antenna density at continental zoom
- Individual pickable site markers at city zoom
- Hover tooltips with operator and antenna count
- Color mode toggle (density, operator, technology, region)
- Google Photorealistic 3D Tiles at street zoom
- 422K sites loaded as single binary blob (~2MB), no tiles needed

## Test plan
- [ ] Coverage map loads in <3 seconds
- [ ] Smooth 60fps pan/zoom on desktop
- [ ] Heatmap density visible at continental zoom
- [ ] Individual sites hoverable at city zoom
- [ ] 3D buildings visible at street zoom
- [ ] Set up scene here transition works
- [ ] Back to globe transition works
- [ ] Other scenarios unaffected
- [ ] Frontend builds without errors"
```

---

## Deferred to follow-up PR

These features are in the spec but intentionally deferred from this plan to keep the initial PR focused:

1. **Region hover (GeoJsonLayer + Natural Earth boundaries)**: needs a GeoJSON file of region polygons and a separate tooltip component for region stats. Add after the core map is working.
2. **Site click expansion (fan-out animation)**: requires sub-site antenna data and an expansion UI. The foundation (`selectedSiteIndex` in the store) is laid but no consuming component is built here.
3. **Fidelity color mode**: requires per-site fidelity tier in the binary blob (not included in this plan's 12-byte format). Add fidelity_tier as a 13th byte in a follow-up.
4. **Google Maps Map ID for vector mode**: needed for interleaved deck.gl rendering and 3D buildings. Requires creating a Map ID in Google Cloud Console. The code supports it via `VITE_GOOGLE_MAP_ID` env var. Without it, deck.gl renders in overlaid mode (functional but no depth interleaving).
