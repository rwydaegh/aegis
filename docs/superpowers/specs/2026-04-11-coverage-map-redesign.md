# Coverage map redesign: Google Maps + deck.gl

Replace the CesiumJS 3-tier LOD globe with a Google Maps base map and deck.gl data layers.

## Why

The current CesiumJS implementation has a hand-rolled 3-tier LOD system (text labels, cluster dots, individual points) that looks bad and was over-engineered for performance concerns that turned out to be unfounded. CesiumJS is built for 3D scenes, not data-dense maps. deck.gl is purpose-built for rendering large geospatial datasets with GPU acceleration.

## Scale

422K unique sites. 5.25M antenna rows across 15 countries. The sites-vs-rows distinction matters: a single tower has ~12 antenna installations on average. The globe shows sites (towers). Expanding a site to show individual antennas is a separate interaction.

At 422K sites, every single point is individually renderable and pickable at 60fps. No clustering, tiling, or aggregation is needed for performance. The heatmap is a visual choice, not a performance crutch.

## Architecture

```
Backend (Flask):
  /api/basestations/coverage  ->  binary blob of 422K sites (~2MB gzip)
                                  + region metadata (names, counts, bboxes)
                                  + operator/technology name lists
                                  + per-site antenna counts
                                  Cached in memory after first computation.

Frontend (React):
  Google Maps (base map)       <-  @vis.gl/react-google-maps
    + Photorealistic 3D Tiles       (automatic at street zoom)
    + Labels, borders, search       (built into Google Maps)
  deck.gl (data layers)       <-  GoogleMapsOverlay
    + HeatmapLayer                  (GPU KDE density, aesthetic overlay at low/mid zoom)
    + ScatterplotLayer              (all 422K sites, all zoom levels, always pickable)
    + GeoJsonLayer                  (region hover boundaries, Natural Earth polygons)
    + Hover tooltips                (site info, region stats)
    + Click interactions            (site expand, "set up scene here")

Transition to local scene:
  "Set up scene here" button   ->  same flow as today:
                                   disable coverage, switch to OSM env,
                                   load base stations in radius, show Three.js scene
```

## Data flow

1. User opens coverage_globe scenario
2. Frontend fetches `/api/basestations/coverage` (one request, ~2MB gzipped)
3. Response decoded into typed arrays: Float32Array lats/lons, Uint8Array operator/tech/region indices
4. Arrays stored in Zustand coverage store (same pattern as today)
5. deck.gl layers read from store, render on Google Maps
6. No tiles, no progressive loading, no LOD tiers. Everything is in memory.

## Backend changes

**`src/aegis/viewer/routes/coverage.py`**: Simplify. Remove the cluster computation (Tier 2). Keep region metadata and binary site packing. The response becomes:
- `regions`: array of {name, label, bbox, count, completeness} (unchanged)
- `sites_b64`: base64-encoded binary of all unique sites (extended format, see below)
- `sites_meta`: {count, operators, technologies, regions} (add region names list)
- Remove: `clusters` field entirely

Extended binary format per site (12 bytes, up from 10):
- float32 latitude (4 bytes)
- float32 longitude (4 bytes)
- uint8 operator_index (1 byte)
- uint8 technology_index (1 byte)
- uint8 region_index (1 byte) -- NEW: which country/region this site belongs to
- uint8 antenna_count (1 byte) -- NEW: number of antennas at this site (capped at 255)

Total payload: 422K x 12 = 5.07 MB raw, ~2.5 MB gzipped.

**Performance**: Current backend takes ~16s to load all parquet files and deduplicate. This is a one-time cost (cached). Acceptable. Could pre-compute and cache to disk if needed later.

## Frontend changes

### New dependencies

```
npm install @vis.gl/react-google-maps @deck.gl/core @deck.gl/layers @deck.gl/aggregation-layers @deck.gl/google-maps
```

### New component: CoverageMap.tsx

Replaces `CesiumGlobe.tsx`. Uses `@vis.gl/react-google-maps` to render a Google Map with the API key from capabilities. Creates a `GoogleMapsOverlay` from deck.gl with these layers:

### Visual plan by zoom level

The heatmap and scatter layers are NOT shown simultaneously. The heatmap communicates density at low zoom. Scatter dots show individual sites at high zoom. A cross-fade transition bridges the two.

| Zoom range | Layers active | Visual result |
|---|---|---|
| 0-8 (world/continent) | HeatmapLayer (full opacity) + GeoJsonLayer (region hover) | Smooth density field. Europe glows. Paris is a bright hotspot, rural areas are dim. No dots, no circles, no clutter. Hovering a country shows aggregate stats. |
| 8-12 (country/region) | HeatmapLayer (fading out) + ScatterplotLayer (fading in) | Cross-fade transition. Individual city clusters emerge from the heatmap. Dots become pickable as they appear. |
| 12-15 (city) | ScatterplotLayer (full opacity) | Individual towers visible, spaced apart, colored by operator/tech/fidelity. Hoverable, clickable. No heatmap. |
| 15+ (street) | ScatterplotLayer + Google 3D buildings | Photorealistic buildings appear. "Set up scene here" available. |

**HeatmapLayer** (zoom 0-12, fades out above 10):
- `data`: all 422K sites
- `getPosition`: [lon, lat] from typed arrays
- `getWeight`: antenna_count per site (towers with more antennas glow hotter)
- `radiusPixels`: zoom-responsive via interpolation (~40px at zoom 2, ~20px at zoom 10)
- `intensity`: zoom-responsive (~1 at zoom 2, ~3 at zoom 10)
- `threshold`: 0.05 (hides near-zero density areas, keeps background clean)
- `colorRange`: plasma or magma ramp (good contrast on satellite imagery)
- `aggregation`: 'SUM'
- `opacity`: 1.0 at zoom <= 8, fades to 0.0 by zoom 12
- GPU kernel density estimation produces smooth continuous gradients, not circles

**ScatterplotLayer** (zoom 8+, fades in from 8-12):
- `data`: all 422K sites
- `getPosition`: [lon, lat]
- `getRadius`: ~50m (meters, not pixels, so they scale with zoom)
- `getFillColor`: by operator index (existing palette), switchable to technology/fidelity/region
- `pickable`: true
- `onHover`: show tooltip (see Interactions section)
- `onClick`: expand site or set up scene (see Interactions section)
- `opacity`: 0.0 at zoom <= 8, fades to 1.0 by zoom 12

**GeoJsonLayer** (zoom 0-10, region hover boundaries):
- `data`: simplified Natural Earth country/region polygons for the 15 regions with data
- `getFillColor`: transparent
- `getLineColor`: transparent (only used for picking, not visual)
- `pickable`: true
- `onHover`: show region stats tooltip (name, antenna count, operators, fidelity distribution)
- `opacity`: fades out above zoom 8

### Interactions (tooltips and clicks)

**Region hover (low zoom)**:
Hovering over a country/region boundary shows a floating card:
- Country/region name
- Total antenna count (from region metadata)
- Dominant operators
- Fidelity tier distribution (mini stacked bar)
- Data completeness percentage
- "Zoom in to explore" hint

**Site hover (mid/high zoom)**:
Hovering a site dot shows a compact tooltip:
- Operator name
- Technology (LTE/5G NR/etc.)
- Antenna count on this tower (e.g., "12 antennas")
- Fidelity tier badge
- Frequency bands present (if available in data)

**Site click (high zoom)**:
Two possible behaviors based on zoom:
1. **Zoom < transition threshold**: Fly the camera to center on this site and zoom in
2. **Zoom >= transition threshold**: Expand the site, showing individual antennas. Options for expansion:
   - **Fan-out**: dots animate outward from the tower position, arranged by azimuth (each antenna placed at its bearing direction). Inspired by OpenCelliD's cluster expansion but using real azimuth data.
   - **Detail panel**: sidebar panel showing all antennas in a compact list with azimuth, frequency, power, tilt. Click any antenna to set up a local simulation scene centered on it.
   - **Recommendation**: do both. Fan-out for visual quick scan, panel for detailed inspection. The fan-out uses azimuth to position sub-dots, making it physically meaningful rather than arbitrary.

**"Set up scene here"**:
- Button appears when zoom >= transition threshold and a site or location is focused
- Same flow as today: disable coverage, load OSM buildings, load base stations in radius, switch to Three.js

### Modified: SceneRoot.tsx

Replace the CesiumGlobe rendering path with CoverageMap. The Three.js canvas still renders on top for the local scene. When coverage is enabled, show CoverageMap. When coverage is disabled (user clicked "Set up scene here"), show Three.js scene.

### Modified: CoverageHud.tsx

Carry over existing functionality:
- Loading state with progress bar
- Error with retry
- Region count and antenna count summary
- "Set up scene here" button (triggered by zoom level)
- "Back to globe" button

Add:
- Color mode toggle (density heatmap, operator, technology, fidelity tier, region)
- Active filter indicators

### Modified: coverage.ts store

- Remove `clusters` (no longer needed)
- Add `hoveredSite: number | null` for tooltip state
- Add `selectedSite: number | null` for expanded site state
- Add `zoom: number` (from Google Maps, replaces cameraAltitude)
- Add `colorMode: 'density' | 'operator' | 'technology' | 'fidelity' | 'region'`
- Add `siteRegionIndices: Uint8Array | null` and `siteAntennaCounts: Uint8Array | null`
- Keep typed arrays for positions and indices (siteLats, siteLons, siteOpIndices, siteTechIndices)

### Removed files

- `components/scene/CoverageOverlay3D.ts` (the 3-tier LOD system)
- CesiumJS and Resium removed from dependencies

### Preserved features

- Region metadata display
- Operator coloring palette
- "Set up scene here" transition to local Three.js view
- "Back to globe" button to return to coverage map
- Loading/error states
- Coverage store data pipeline

## Google Maps specifics

- API key: already in `.env` as `GOOGLE_API_KEY`, served to frontend via `/api/capabilities`
- Map ID: create a map ID in Google Cloud Console for vector map (required for deck.gl interleaved mode). Falls back to raster mode (overlaid) without a map ID.
- Map type: `hybrid` (satellite + labels). Switchable to `satellite` for cleaner heatmap contrast.
- Photorealistic 3D Tiles: enabled by default in Google Maps, shows buildings at street-level zoom
- Controls: Google Maps default navigation (pan, zoom, tilt, rotate)
- Pricing: 10K free map loads/month. At AEGIS's current usage (~100 loads/month), cost is $0.
- US billing account avoids EEA restrictions on Map Tiles API

## Future: dosimetry overlay

The architecture supports adding computed dosimetry results as an additional deck.gl layer. A `BitmapLayer` or `TileLayer` with raster tiles of pre-computed Sab values would overlay naturally on the same map. The same binary-blob-in-memory pattern works: compute dosimetry for a region, pack results as a grid, serve as a single binary, render client-side.

## What this does NOT change

- The Three.js local simulation scene (PanelAntenna, radiation patterns, LSPHeatmap, etc.)
- The base station loading flow (POST /api/basestations/load)
- The dosimetry computation pipeline
- The fidelity readiness system
- The antenna marker hover preview in local Three.js view (R3F onPointerOver)
- Any other viewer functionality

## Risks and mitigations

- **deck.gl + GoogleMapsOverlay compatibility**: verify HeatmapLayer works in interleaved mode. If not, use overlaid mode (visual only, no depth interleaving with 3D buildings).
- **Google Maps pricing at scale**: free tier covers 10K sessions/month. Monitor via Cloud Console. If costs grow, swap to MapLibre (data layer is base-map-agnostic).
- **Mobile performance**: 422K points is fine on desktop. On mobile, reduce ScatterplotLayer radius and increase HeatmapLayer debounceTimeout. Test on real devices.
- **Map ID requirement**: interleaved mode needs a Cloud Console map ID. Without it, deck.gl renders in overlaid mode (still functional, just no depth interleaving).

## Success criteria

- Coverage map loads in <3 seconds (including data fetch)
- Smooth 60fps pan/zoom on desktop with all 422K sites
- Beautiful density heatmap visible from space-level zoom
- Every site individually hoverable with tooltip at city zoom
- Region hover shows aggregate stats at continental zoom
- Site click expands to show individual antennas (fan-out or panel)
- Google Photorealistic 3D Tiles visible at street zoom
- "Set up scene here" transition works as before
- Country borders, place names, and labels visible at all zoom levels
- Color mode switching (operator, technology, fidelity, density) is instant
