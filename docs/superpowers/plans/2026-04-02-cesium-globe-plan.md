# Cesium globe implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken `3d-tiles-renderer` globe with CesiumJS/Resium for proper Google Earth-quality globe with coverage overlay.

**Architecture:** Two-canvas overlay: Cesium Viewer handles globe/imagery/terrain/coverage-points, R3F Canvas sits on top for dosimetry objects. Cesium is camera authority, syncs to R3F each frame. Coverage data rendered via Cesium PointPrimitiveCollection (no manual ECEF math).

**Tech Stack:** CesiumJS, Resium, Cesium ion, Google Photorealistic 3D Tiles (optional), Zustand, React

**Spec:** `docs/superpowers/specs/2026-04-02-cesium-globe-design.md`

---

## Task 1: Install dependencies and configure Vite

Remove `3d-tiles-renderer` and add CesiumJS with its Vite plugin. The `vite-plugin-cesium` package handles static asset copying (Workers, Assets, Widgets, ThirdParty) automatically during dev and build.

**Files:**
- Modify: `aegis-web/package.json`
- Modify: `aegis-web/vite.config.ts`
- Modify: `aegis-web/src/main.tsx`

- [ ] **Step 1: Install cesium, resium, and vite-plugin-cesium**

```bash
cd aegis-web
npm uninstall 3d-tiles-renderer
npm install cesium resium
npm install --save-dev vite-plugin-cesium
```

This removes `3d-tiles-renderer` (v0.4.23) and installs:
- `cesium` (latest 1.x, peer dep of resium)
- `resium` (v1.20.0, React component wrappers for Cesium)
- `vite-plugin-cesium` (v1.2.23, handles Cesium static asset serving)

- [ ] **Step 2: Add cesium plugin to vite.config.ts**

```typescript
// aegis-web/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import cesium from 'vite-plugin-cesium'
import { sentryVitePlugin } from '@sentry/vite-plugin'
import path from 'path'

export default defineConfig({
  build: {
    sourcemap: true,
  },
  plugins: [
    react(),
    tailwindcss(),
    cesium(),
    // Upload source maps to Sentry during production builds (requires SENTRY_AUTH_TOKEN env var)
    sentryVitePlugin({
      org: process.env.SENTRY_ORG,
      project: process.env.SENTRY_PROJECT,
      authToken: process.env.SENTRY_AUTH_TOKEN,
      disable: !process.env.SENTRY_AUTH_TOKEN,
      errorHandler: (err) => {
        console.warn('[sentry-vite-plugin] Source map upload failed (non-fatal):', err.message)
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        timeout: 120000,
      },
    },
  },
})
```

- [ ] **Step 3: Import Cesium widget CSS in main.tsx**

Add the Cesium widgets CSS import to `aegis-web/src/main.tsx`, after the existing CSS imports:

```typescript
// aegis-web/src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'katex/dist/katex.min.css'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import './index.css'
import App from './App.tsx'
import { TooltipProvider } from '@/components/ui/tooltip'
import { initSentry } from '@/lib/sentry'

initSentry()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <TooltipProvider>
      <App />
    </TooltipProvider>
  </StrictMode>,
)
```

- [ ] **Step 4: Verify build succeeds**

```bash
cd aegis-web && npm run build
```

The build will have TypeScript errors from `Environment3DTiles.tsx` importing from the removed `3d-tiles-renderer`. That is expected and will be fixed in Task 8. For now, verify the Cesium plugin initializes correctly and assets are copied. If TS errors block the build, temporarily comment out the `Environment3DTiles` import in `SceneRoot.tsx` (line 25) and the usage at lines 429-433.

- [ ] **Step 5: Commit**

```bash
git add aegis-web/package.json aegis-web/package-lock.json aegis-web/vite.config.ts aegis-web/src/main.tsx
git commit -m "Add CesiumJS/Resium deps, remove 3d-tiles-renderer, configure Vite plugin"
```

---

## Task 2: Backend token plumbing

Serve the Cesium Ion access token from the backend config and update TypeScript types. The coverage_globe scenario needs to switch from `"3dtiles"` source to `"cesium"`.

**Files:**
- Modify: `src/aegis/viewer/routes/data.py` (line ~254)
- Modify: `src/aegis/viewer/config.py` (line ~561)
- Modify: `aegis-web/src/api/types.ts` (line ~176)
- Modify: `aegis-web/src/stores/environment.ts` (line 6)

- [ ] **Step 1: Add cesium_ion_token to viewer-config response**

In `src/aegis/viewer/routes/data.py`, find the capabilities dict (around line 253-257) and add `cesium_ion_token` after `google_api_key`:

```python
            "google_api_key": os.environ.get("GOOGLE_API_KEY", ""),
            "cesium_ion_token": os.environ.get("CESIUM_ION_TOKEN", ""),
            "body_placement": cache.get("body_placement"),
```

- [ ] **Step 2: Update coverage_globe scenario source in config.py**

In `src/aegis/viewer/config.py`, find the `coverage_globe` scenario (line ~551-566) and change the environment source from `"3dtiles"` to `"cesium"`:

```python
        "coverage_globe": {
            "description": "Browse base station coverage worldwide",
            "launch": {},
            "label": "Coverage globe",
            "icon": "globe",
            "instant": True,
            "autoCompute": False,
            "webState": {
                "antennaPos": None,
                "environment": {
                    "source": "cesium",
                    "lat": 0,
                    "lon": 0,
                },
            },
        },
```

- [ ] **Step 3: Add cesium_ion_token to TypeScript Capabilities interface**

In `aegis-web/src/api/types.ts`, find the `Capabilities` interface (line ~160) and add the new field after `google_api_key`:

```typescript
export interface Capabilities {
  bodies: string[]
  body_name: string
  skin_models: { id: string; label: string }[]
  levels: number[]
  has_voxels: boolean
  has_differt: boolean
  has_sionna: boolean
  voxel_rt_available: boolean
  has_tiles: boolean
  n_tiles: number
  scenes: Array<string | { name: string; path: string }>
  body_meta: BodyMeta | null
  voxel_meta: VoxelMeta | null
  has_location_loader: boolean
  has_api_key: boolean
  google_api_key: string
  cesium_ion_token: string
  body_placement: [number, number, number] | null
  body_device_offsets: Record<string, [number, number, number]>
}
```

- [ ] **Step 4: Add 'cesium' to EnvironmentSource type**

In `aegis-web/src/stores/environment.ts`, update the type on line 6:

```typescript
export type EnvironmentSource = 'none' | 'voxels' | 'osm' | '3dtiles' | 'cesium'
```

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/routes/data.py src/aegis/viewer/config.py aegis-web/src/api/types.ts aegis-web/src/stores/environment.ts
git commit -m "Add Cesium Ion token to backend config and TypeScript types"
```

---

## Task 3: CesiumGlobe component (minimal)

Create the core Cesium viewer component. This renders a full-screen Cesium globe with all default UI disabled. It reads the Ion token from capabilities, optionally loads Google 3D Tiles, and writes camera position to the coverage store each frame.

**Files:**
- Create: `aegis-web/src/components/scene/CesiumGlobe.tsx`

- [ ] **Step 1: Create the CesiumGlobe component**

```typescript
// aegis-web/src/components/scene/CesiumGlobe.tsx
import { useEffect, useRef, useCallback } from 'react'
import { Viewer as ResiumViewer } from 'resium'
import {
  Ion,
  Viewer,
  Cartographic,
  Math as CesiumMath,
  createWorldTerrainAsync,
  Cesium3DTileset,
} from 'cesium'
import { useSceneStore } from '@/stores/scene'
import { useEnvironmentStore } from '@/stores/environment'
import { useCoverageStore } from '@/stores/coverage'

/**
 * CesiumGlobe renders a Cesium Viewer as the globe/terrain layer.
 * Only mounts when envSource is 'cesium'.
 */
export function CesiumGlobe() {
  const viewerRef = useRef<Viewer | null>(null)
  const tickListenerRef = useRef<(() => void) | null>(null)
  const capabilities = useSceneStore(s => s.capabilities)
  const envSource = useEnvironmentStore(s => s.source)

  const cesiumToken = capabilities?.cesium_ion_token ?? ''
  const googleApiKey = capabilities?.google_api_key ?? ''

  // Set Ion token before viewer creation
  useEffect(() => {
    if (cesiumToken) {
      Ion.defaultAccessToken = cesiumToken
    }
  }, [cesiumToken])

  // Handle viewer ready
  const handleViewerReady = useCallback(async (viewer: Viewer) => {
    viewerRef.current = viewer

    // Disable default UI elements that Resium props don't cover
    viewer.cesiumWidget.creditContainer.setAttribute('style', 'display: none !important')

    // Load terrain
    try {
      viewer.terrainProvider = await createWorldTerrainAsync()
    } catch (e) {
      console.warn('Failed to load Cesium World Terrain:', e)
    }

    // Optionally load Google Photorealistic 3D Tiles
    if (googleApiKey) {
      try {
        const tileset = await Cesium3DTileset.fromUrl(
          `https://tile.googleapis.com/v1/3dtiles/root.json?key=${googleApiKey}`,
        )
        viewer.scene.primitives.add(tileset)
      } catch (e) {
        console.warn('Failed to load Google 3D Tiles:', e)
      }
    }

    // Initial camera: high altitude for globe view
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(10, 20, 20_000_000),
      duration: 0,
    })

    // Camera tick: write lat/lon/altitude to coverage store each frame
    const onTick = () => {
      const carto = Cartographic.fromCartesian(viewer.camera.positionWC)
      const alt = carto.height
      const lat = CesiumMath.toDegrees(carto.latitude)
      const lon = CesiumMath.toDegrees(carto.longitude)
      const store = useCoverageStore.getState()
      store.setCameraAltitude(alt)
      store.setCameraLatLon({ lat, lon })
    }
    viewer.clock.onTick.addEventListener(onTick)
    tickListenerRef.current = onTick
  }, [googleApiKey])

  // Cleanup tick listener on unmount
  useEffect(() => {
    return () => {
      if (viewerRef.current && tickListenerRef.current) {
        viewerRef.current.clock.onTick.removeEventListener(tickListenerRef.current)
      }
    }
  }, [])

  // Only render for cesium source
  if (envSource !== 'cesium') return null
  if (!cesiumToken) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-zinc-950 text-zinc-400 text-sm">
        Cesium Ion token not configured. Set CESIUM_ION_TOKEN on the server.
      </div>
    )
  }

  return (
    <ResiumViewer
      full
      timeline={false}
      animation={false}
      baseLayerPicker={false}
      geocoder={false}
      homeButton={false}
      navigationHelpButton={false}
      sceneModePicker={false}
      fullscreenButton={false}
      vrButton={false}
      selectionIndicator={false}
      infoBox={false}
      ref={(e: any) => {
        if (e?.cesiumElement && !viewerRef.current) {
          handleViewerReady(e.cesiumElement)
        }
      }}
    />
  )
}
```

**Important notes:**
- The `ref` callback on ResiumViewer fires with `{ cesiumElement: Viewer }`. We check `!viewerRef.current` to avoid re-initializing.
- `Ion.defaultAccessToken` must be set before Viewer construction. The `useEffect` runs before the first render that includes `<ResiumViewer>`.
- `viewer.clock.onTick` fires every animation frame, so the coverage store always has fresh camera data.
- The `Cesium` namespace import for `Cartesian3.fromDegrees` in the `flyTo` call needs to be imported. Add `import * as Cesium from 'cesium'` at the top, or use the named import directly. Use `import { Cartesian3 } from 'cesium'` and replace `Cesium.Cartesian3.fromDegrees(...)` with `Cartesian3.fromDegrees(...)`.

Corrected imports at the top of the file:

```typescript
import {
  Ion,
  Viewer,
  Cartographic,
  Cartesian3,
  Math as CesiumMath,
  createWorldTerrainAsync,
  Cesium3DTileset,
} from 'cesium'
```

And the flyTo becomes:

```typescript
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(10, 20, 20_000_000),
      duration: 0,
    })
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd aegis-web && npx tsc --noEmit
```

Fix any import issues. The component is not yet used in SceneRoot, so there should be no integration errors.

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/scene/CesiumGlobe.tsx
git commit -m "Add CesiumGlobe component with Ion token, terrain, and camera sync"
```

---

## Task 4: SceneRoot restructure (two-canvas layout)

Restructure `SceneRoot` to use a two-layer layout: Cesium Viewer as the bottom layer, R3F Canvas on top. When in cesium mode, the R3F canvas gets a transparent background and passes pointer events through to Cesium.

**Files:**
- Modify: `aegis-web/src/components/scene/SceneRoot.tsx`

- [ ] **Step 1: Add CesiumGlobe import and remove Environment3DTiles wrapping**

At the top of `SceneRoot.tsx`, add the CesiumGlobe import and keep the Environment3DTiles import for now (it will be deleted in Task 8):

```typescript
import { CesiumGlobe } from './CesiumGlobe'
```

- [ ] **Step 2: Restructure the return JSX**

Replace the current return block (lines 411-435) with a two-div layout. The key changes:
1. Outer wrapper div with `position: absolute, inset: 0`
2. CesiumGlobe div at z-index 1 (only visible for cesium source)
3. R3F Canvas div at z-index 2, with transparent background and no pointer events when cesium is active
4. Remove the `Environment3DTiles` conditional wrapping (the `{envSource === '3dtiles' ? ... : ...}` ternary)

```typescript
export default function SceneRoot() {
  const webglAvailable = useMemo(() => hasWebGL(), [])
  const config = useSceneStore(s => s.viewerConfig)
  const bodyMeshVisible = useSceneStore(s => s.bodyMeshVisible)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const cameraMode = useUIStore(s => s.cameraMode)
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const envSource = useEnvironmentStore(s => s.source)
  const controlsRef = useRef<OrbitControlsImpl | null>(null)
  if (!webglAvailable) return <WebGLUnavailable />
  if (!config) return null

  const cam = config.camera
  const ren = config.renderer
  const initialPosition = (cam.initial_position as [number, number, number]) ?? [0, 2, 5]
  const isCesiumMode = envSource === 'cesium'

  const sceneContent = (
    <>
      {!isCesiumMode && <color attach="background" args={[config.scene.background_color ?? '#0a0a0f']} />}
      <SceneLighting />
      <ClickPlane />
      {(envSource === 'none' || envSource === 'voxels') && (
        <>
          <VoxelField />
          <HullMesh />
          <SceneGeometry />
          <Environment />
        </>
      )}
      {envSource === 'osm' && <EnvironmentOSM />}
      {envSource === '3dtiles' && <Environment3DTiles><></></Environment3DTiles>}
      {bodyMeshVisible && (mimoEnabled ? (
        <MIMOScene />
      ) : (
        <>
          <BodyMesh />
          <Antenna />
          <DistanceLine />
        </>
      ))}
      <RayPaths />
      <GroundPlane />
      <SceneGrid />
      <EnvironmentTerrain />
      <BaseStationMarkers />
      <DosimetryController />
      <MIMODosimetryController />
      <MIMOKeyboardController />
      <PhysicsController />
      <FollowCamera />
      {cameraMode === 'orbit' && (
        <>
          <OrbitControls ref={controlsRef} makeDefault enableDamping />
          <CameraController controlsRef={controlsRef} initialPosition={initialPosition} />
          <CameraInitializer controlsRef={controlsRef} initialOffset={bodyOffset} />
          <CameraSyncer controlsRef={controlsRef} />
        </>
      )}
    </>
  )

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {isCesiumMode && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
          <CesiumGlobe />
        </div>
      )}
      <div style={{
        position: 'absolute',
        inset: 0,
        zIndex: 2,
        pointerEvents: isCesiumMode ? 'none' : 'auto',
      }}>
        <Canvas
          camera={{
            fov: cam.fov,
            near: cam.near,
            far: cam.far,
            position: initialPosition,
          }}
          shadows={ren.shadows_enabled ? { type: THREE.PCFShadowMap } : false}
          gl={{
            antialias: ren.antialias ?? true,
            toneMapping: THREE.ACESFilmicToneMapping,
            preserveDrawingBuffer: true,
            logarithmicDepthBuffer: true,
            alpha: isCesiumMode,
          }}
          style={{
            position: 'absolute',
            inset: 0,
            background: isCesiumMode ? 'transparent' : undefined,
          }}
          tabIndex={0}
        >
          {sceneContent}
        </Canvas>
      </div>
    </div>
  )
}
```

Key changes from the original:
- `<CoverageOverlay />` and `<CoverageGlobe />` removed from sceneContent (coverage is now handled by Cesium primitives)
- `<color attach="background" ...>` is conditional, skipped in cesium mode so the R3F canvas is transparent
- `gl.alpha: true` when in cesium mode, so WebGL clears to transparent
- `pointerEvents: 'none'` on the R3F wrapper lets mouse events fall through to the Cesium div
- The `Environment3DTiles` wrapping ternary is gone. For `3dtiles` source, the component still renders but without wrapping sceneContent (it renders an empty fragment as children instead). This will be fully cleaned up in Task 8.

- [ ] **Step 3: Verify build succeeds**

```bash
cd aegis-web && npm run build
```

Check that non-globe scenarios (open_ground, urban_ghent) still work by loading the viewer.

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/scene/SceneRoot.tsx
git commit -m "Restructure SceneRoot for two-canvas Cesium/R3F layout"
```

---

## Task 5: Coverage store simplification

The coverage store currently converts lat/lon to ECEF positions and creates color arrays for R3F `<points>` rendering. With Cesium handling the rendering, we store raw lat/lon/opIndex arrays and let Cesium do the ECEF conversion via `Cartesian3.fromDegrees()`.

**Files:**
- Modify: `aegis-web/src/stores/coverage.ts`

- [ ] **Step 1: Simplify the coverage store**

Replace the contents of `aegis-web/src/stores/coverage.ts`:

```typescript
import { create } from 'zustand'
import { fetchCoverage, decodeSitesBinary } from '@/api/coverage'
import type { RegionSummary, ClusterPoint } from '@/api/types'

interface CoverageState {
  enabled: boolean
  loaded: boolean
  loading: boolean
  error: string | null
  regions: RegionSummary[]
  clusters: ClusterPoint[]
  siteLats: Float32Array | null
  siteLons: Float32Array | null
  siteOpIndices: Uint8Array | null
  siteCount: number
  operatorNames: string[]
  technologyNames: string[]
  cameraLatLon: { lat: number; lon: number } | null
  cameraAltitude: number

  fetch: () => Promise<void>
  setEnabled: (v: boolean) => void
  setCameraLatLon: (ll: { lat: number; lon: number }) => void
  setCameraAltitude: (alt: number) => void
}

export const useCoverageStore = create<CoverageState>((set, get) => ({
  enabled: false,
  loaded: false,
  loading: false,
  error: null,
  regions: [],
  clusters: [],
  siteLats: null,
  siteLons: null,
  siteOpIndices: null,
  siteCount: 0,
  operatorNames: [],
  technologyNames: [],
  cameraLatLon: null,
  cameraAltitude: Infinity,

  fetch: async () => {
    if (get().loaded || get().loading) return
    set({ loading: true, error: null })
    try {
      const data = await fetchCoverage()
      const { latitudes, longitudes, opIndices } = decodeSitesBinary(
        data.sites_b64,
        data.sites_meta.count,
      )

      set({
        regions: data.regions,
        clusters: data.clusters,
        siteLats: latitudes,
        siteLons: longitudes,
        siteOpIndices: opIndices,
        siteCount: data.sites_meta.count,
        operatorNames: data.sites_meta.operators,
        technologyNames: data.sites_meta.technologies,
        loaded: true,
        loading: false,
      })
    } catch (err) {
      console.error('Failed to fetch coverage data:', err)
      set({ error: (err as Error).message, loading: false })
    }
  },

  setEnabled: (v) => set({ enabled: v }),
  setCameraLatLon: (ll) => set({ cameraLatLon: ll }),
  setCameraAltitude: (alt) => set({ cameraAltitude: alt }),
}))
```

Removed fields: `sitePositions`, `siteColors`, `activeTier`, `hoveredRegion`, `setActiveTier`, `setHoveredRegion`.
Removed imports: `latLonToECEF` from `@/lib/geo`.
Removed logic: ECEF conversion loop, color array generation, `OPERATOR_COLORS` constant.
Added fields: `siteLats`, `siteLons`, `siteOpIndices` (raw decoded arrays, no transformation).

- [ ] **Step 2: Fix compilation errors from removed fields**

Check if any other files reference the removed fields:

```bash
cd aegis-web && grep -rn 'sitePositions\|siteColors\|activeTier\|hoveredRegion\|setActiveTier\|setHoveredRegion' src/ --include='*.ts' --include='*.tsx'
```

The `CoverageGlobe.tsx` component uses `activeTier` and `setActiveTier`. This file will be deleted in Task 8, but for now it will have TS errors. If it blocks compilation, comment out the broken references temporarily.

The `CoverageHud.tsx` component does NOT reference any of the removed fields (verified from source). It uses `enabled`, `cameraAltitude`, `cameraLatLon`, `regions`, `loading`, `error`, which all remain.

- [ ] **Step 3: Verify TypeScript**

```bash
cd aegis-web && npx tsc --noEmit
```

Fix any remaining type errors. Expected errors in `CoverageGlobe.tsx` are acceptable since that file is deleted in Task 8.

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/stores/coverage.ts
git commit -m "Simplify coverage store: raw lat/lon arrays, remove ECEF conversion"
```

---

## Task 6: CoverageOverlay3D (Cesium primitives)

Create an imperative module that adds coverage data as Cesium primitives (points, polylines, labels) to the Cesium viewer. This is called from CesiumGlobe when the viewer is ready and coverage data is loaded.

**Files:**
- Create: `aegis-web/src/components/scene/CoverageOverlay3D.ts`
- Modify: `aegis-web/src/components/scene/CesiumGlobe.tsx`

- [ ] **Step 1: Create the CoverageOverlay3D module**

```typescript
// aegis-web/src/components/scene/CoverageOverlay3D.ts
import {
  Viewer,
  Cartesian3,
  Color,
  NearFarScalar,
  DistanceDisplayCondition,
  LabelStyle,
  PointPrimitiveCollection,
  LabelCollection,
  PolylineCollection,
  Material,
} from 'cesium'
import type { RegionSummary } from '@/api/types'

// 16-color operator palette matching the original OPERATOR_COLORS
const OP_COLORS: Color[] = [
  new Color(0.23, 0.51, 0.96, 1),
  new Color(0.96, 0.51, 0.11, 1),
  new Color(0.18, 0.76, 0.49, 1),
  new Color(0.66, 0.33, 0.83, 1),
  new Color(0.91, 0.30, 0.24, 1),
  new Color(0.10, 0.74, 0.81, 1),
  new Color(0.98, 0.75, 0.18, 1),
  new Color(0.55, 0.34, 0.16, 1),
  new Color(0.44, 0.50, 0.56, 1),
  new Color(0.84, 0.37, 0.65, 1),
  new Color(0.40, 0.65, 0.12, 1),
  new Color(0.70, 0.20, 0.36, 1),
  new Color(0.30, 0.30, 0.80, 1),
  new Color(0.80, 0.60, 0.40, 1),
  new Color(0.50, 0.80, 0.80, 1),
  new Color(0.60, 0.60, 0.20, 1),
]

function completenessColor(c: number): Color {
  if (c > 0.8) return Color.fromCssColorString('#22c55e')
  if (c > 0.4) return Color.fromCssColorString('#f59e0b')
  return Color.fromCssColorString('#ef4444')
}

export interface CoverageOverlayHandle {
  points: PointPrimitiveCollection
  lines: PolylineCollection
  labels: LabelCollection
  destroy: () => void
  setVisible: (v: boolean) => void
}

/**
 * Add coverage site points, region boundaries, and region labels to a Cesium viewer.
 * Returns a handle for visibility control and cleanup.
 */
export function addCoverageOverlay(
  viewer: Viewer,
  siteLats: Float32Array,
  siteLons: Float32Array,
  siteOpIndices: Uint8Array,
  siteCount: number,
  regions: RegionSummary[],
): CoverageOverlayHandle {
  // Site points
  const points = viewer.scene.primitives.add(new PointPrimitiveCollection())
  for (let i = 0; i < siteCount; i++) {
    points.add({
      position: Cartesian3.fromDegrees(siteLons[i], siteLats[i], 100),
      pixelSize: 6,
      color: OP_COLORS[siteOpIndices[i] % OP_COLORS.length],
      scaleByDistance: new NearFarScalar(1e3, 2.0, 1e7, 0.5),
      translucencyByDistance: new NearFarScalar(1e3, 1.0, 1e7, 0.3),
    })
  }

  // Region boundary polylines
  const lines = viewer.scene.primitives.add(new PolylineCollection())
  for (const region of regions) {
    if (!region.bbox) continue
    const [minLon, maxLon, minLat, maxLat] = region.bbox
    lines.add({
      positions: Cartesian3.fromDegreesArray([
        minLon, minLat,
        maxLon, minLat,
        maxLon, maxLat,
        minLon, maxLat,
        minLon, minLat,
      ]),
      width: 2,
      material: Material.fromType('Color', {
        color: completenessColor(region.completeness),
      }),
      distanceDisplayCondition: new DistanceDisplayCondition(2e5, Infinity),
    })
  }

  // Region labels
  const labels = viewer.scene.primitives.add(new LabelCollection())
  for (const region of regions) {
    if (!region.bbox) continue
    const [minLon, maxLon, minLat, maxLat] = region.bbox
    labels.add({
      position: Cartesian3.fromDegrees(
        (minLon + maxLon) / 2,
        (minLat + maxLat) / 2,
        5000,
      ),
      text: `${region.label}\n${region.count.toLocaleString()} antennas`,
      font: '14px sans-serif',
      fillColor: Color.WHITE,
      outlineColor: Color.BLACK,
      outlineWidth: 2,
      style: LabelStyle.FILL_AND_OUTLINE,
      distanceDisplayCondition: new DistanceDisplayCondition(5e5, Infinity),
      scaleByDistance: new NearFarScalar(5e5, 1.0, 5e6, 0.3),
    })
  }

  return {
    points,
    lines,
    labels,
    destroy: () => {
      viewer.scene.primitives.remove(points)
      viewer.scene.primitives.remove(lines)
      viewer.scene.primitives.remove(labels)
    },
    setVisible: (v: boolean) => {
      points.show = v
      lines.show = v
      labels.show = v
    },
  }
}
```

- [ ] **Step 2: Integrate with CesiumGlobe**

Update `CesiumGlobe.tsx` to call `addCoverageOverlay` when the viewer is ready and coverage data is loaded. Add a `useEffect` that subscribes to the coverage store:

Add this import at the top of `CesiumGlobe.tsx`:

```typescript
import { addCoverageOverlay, type CoverageOverlayHandle } from './CoverageOverlay3D'
```

Add a ref for the overlay handle:

```typescript
const overlayRef = useRef<CoverageOverlayHandle | null>(null)
```

Add a `useEffect` after the existing effects in `CesiumGlobe.tsx`:

```typescript
  // Subscribe to coverage store and add/update primitives
  useEffect(() => {
    if (envSource !== 'cesium') return

    const unsub = useCoverageStore.subscribe((state, prevState) => {
      const viewer = viewerRef.current
      if (!viewer || viewer.isDestroyed()) return

      // Coverage data just loaded
      if (state.loaded && !prevState.loaded && state.siteLats && state.siteLons && state.siteOpIndices) {
        if (overlayRef.current) overlayRef.current.destroy()
        overlayRef.current = addCoverageOverlay(
          viewer,
          state.siteLats,
          state.siteLons,
          state.siteOpIndices,
          state.siteCount,
          state.regions,
        )
      }

      // Visibility toggled
      if (state.enabled !== prevState.enabled && overlayRef.current) {
        overlayRef.current.setVisible(state.enabled)
      }
    })

    // If data is already loaded when we mount, add overlay immediately
    const state = useCoverageStore.getState()
    if (state.loaded && state.siteLats && state.siteLons && state.siteOpIndices && viewerRef.current) {
      overlayRef.current = addCoverageOverlay(
        viewerRef.current,
        state.siteLats,
        state.siteLons,
        state.siteOpIndices,
        state.siteCount,
        state.regions,
      )
    }

    return () => {
      unsub()
      if (overlayRef.current) {
        overlayRef.current.destroy()
        overlayRef.current = null
      }
    }
  }, [envSource])
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd aegis-web && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/scene/CoverageOverlay3D.ts aegis-web/src/components/scene/CesiumGlobe.tsx
git commit -m "Add Cesium coverage overlay with site points, region boundaries, and labels"
```

---

## Task 7: useScenario update and HUD adjustments

The `useScenario` hook needs to handle the `cesium` environment source. The `CoverageHud` should already work since it reads `cameraLatLon` and `cameraAltitude` from the coverage store (which CesiumGlobe writes to each frame).

**Files:**
- Modify: `aegis-web/src/hooks/useScenario.ts`
- Verify: `aegis-web/src/components/hud/CoverageHud.tsx` (no changes expected)

- [ ] **Step 1: Update geocodeAndFetch to handle cesium source**

In `aegis-web/src/stores/environment.ts`, the `geocodeAndFetch` method (line 101-136) checks `if (source !== 'osm' && source !== '3dtiles') return`. This blocks geocoding for `cesium` source. Update the condition to also allow `cesium`:

```typescript
    if (source !== 'osm' && source !== '3dtiles' && source !== 'cesium') return
```

No other changes are needed in `geocodeAndFetch` since the `cesium` source does not need to call `fetchOSM()` or `fetchTilesForRT()` after geocoding. The `if (source === 'osm')` and `else if (source === '3dtiles')` branches handle those cases, and `cesium` falls through without fetching, which is correct.

- [ ] **Step 2: Verify CoverageHud works with new store shape**

The `CoverageHud` component reads these fields from the coverage store:
- `enabled` (kept)
- `cameraAltitude` (kept)
- `cameraLatLon` (kept)
- `regions` (kept)
- `loading` (kept)
- `error` (kept)

All fields are present in the simplified store. No changes needed.

- [ ] **Step 3: Verify other scenarios still work**

The `useScenario` hook sets `env.setSource(webState.environment.source as any)`. For `open_ground` that sets `'osm'`, for `coverage_globe` it now sets `'cesium'` (from Task 2). For `empty` it sets `'none'`. All are valid `EnvironmentSource` values after Task 2.

```bash
cd aegis-web && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/stores/environment.ts
git commit -m "Allow cesium source in geocodeAndFetch guard"
```

---

## Task 8: Cleanup old files

Delete the old R3F-based globe and coverage overlay components that are replaced by Cesium. Fix any broken imports.

**Files:**
- Delete: `aegis-web/src/components/scene/Environment3DTiles.tsx`
- Delete: `aegis-web/src/components/scene/CoverageGlobe.tsx`
- Delete: `aegis-web/src/components/scene/CoverageOverlay.tsx`
- Modify: `aegis-web/src/components/scene/SceneRoot.tsx` (remove imports)

- [ ] **Step 1: Delete old files**

```bash
rm aegis-web/src/components/scene/Environment3DTiles.tsx
rm aegis-web/src/components/scene/CoverageGlobe.tsx
rm aegis-web/src/components/scene/CoverageOverlay.tsx
```

- [ ] **Step 2: Remove imports and usages from SceneRoot.tsx**

Remove these import lines from `SceneRoot.tsx`:

```typescript
// DELETE these lines:
import { Environment3DTiles } from './Environment3DTiles'
import { CoverageOverlay } from './CoverageOverlay'
import { CoverageGlobe } from './CoverageGlobe'
```

Remove any remaining references to these components in the JSX. After Task 4, the only remaining reference should be the `envSource === '3dtiles'` conditional rendering of `Environment3DTiles`. Remove that line from sceneContent:

```typescript
// DELETE this line from sceneContent:
{envSource === '3dtiles' && <Environment3DTiles><></></Environment3DTiles>}
```

Also remove the `3dtiles` source handling from SceneRoot entirely. If users want the old `3dtiles` behavior (Google tiles via three.js), they can use `cesium` source instead. But keep the `EnvironmentSource` type including `'3dtiles'` for backward compatibility with configs.

- [ ] **Step 3: Check for other imports of deleted files**

```bash
cd aegis-web && grep -rn 'Environment3DTiles\|CoverageGlobe\|CoverageOverlay' src/ --include='*.ts' --include='*.tsx'
```

Fix any remaining references. Expected locations:
- `SceneRoot.tsx` (handled in step 2)
- No other files should import these components directly

- [ ] **Step 4: Verify build and TypeScript**

```bash
cd aegis-web && npx tsc --noEmit && npm run build
```

Both must pass with zero errors.

- [ ] **Step 5: Commit**

```bash
git add -A aegis-web/src/components/scene/
git commit -m "Remove old 3d-tiles-renderer globe and R3F coverage overlay components"
```

---

## Task 9: Production deployment

Deploy the Cesium globe to the Hetzner production server. The Cesium Ion token must be added to the server environment.

**Files:**
- Modify: `/opt/aegis/app.env` on server (manual or via SSH)
- No workflow changes needed (token is read via `os.environ` at runtime, not at build time)

- [ ] **Step 1: Add Cesium Ion token to server**

SSH to the Hetzner server and add the token to the app environment file:

```bash
ssh root@<HETZNER_HOST> "grep -q CESIUM_ION_TOKEN /opt/aegis/app.env || echo 'CESIUM_ION_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJkYmM4NWM1YS1jZDhjLTQxOTctODI3My03ZGQ1MjM1NDY5NzAiLCJpZCI6NDEyOTU1LCJpYXQiOjE3NzUxNDg3Mzh9._0QXdOiwatLjXe95Qdke9a7vDIllWpFUx1Hg52z1Yvg' >> /opt/aegis/app.env"
```

The Docker Compose file already passes `app.env` to the container, so the token will be available via `os.environ.get("CESIUM_ION_TOKEN")` in the Flask backend.

- [ ] **Step 2: Add token to GitHub secrets (for future reference)**

This is a manual step in the GitHub repo settings. Go to Settings > Secrets and variables > Actions and add:
- Name: `CESIUM_ION_TOKEN`
- Value: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJkYmM4NWM1YS1jZDhjLTQxOTctODI3My03ZGQ1MjM1NDY5NzAiLCJpZCI6NDEyOTU1LCJpYXQiOjE3NzUxNDg3Mzh9._0QXdOiwatLjXe95Qdke9a7vDIllWpFUx1Hg52z1Yvg`

This is not used by the deploy workflow currently (the token is read at runtime, not build time), but is good practice for documentation.

- [ ] **Step 3: Push changes and create PR**

All tasks 1-8 should be committed on a feature branch. Push and create a PR:

```bash
git push -u origin feature/cesium-globe
gh pr create --title "Replace 3d-tiles-renderer with CesiumJS globe" --body "$(cat <<'EOF'
## Summary
- Replace broken `3d-tiles-renderer` globe with CesiumJS/Resium for proper globe rendering
- Two-canvas layout: Cesium Viewer (globe/terrain/coverage) + R3F Canvas (dosimetry objects)
- Coverage data rendered via Cesium PointPrimitiveCollection (293K antenna sites)
- Simplified coverage store: raw lat/lon arrays, no manual ECEF math
- Backend serves Cesium Ion token via `/api/viewer-config`

## Test plan
- [ ] Verify `coverage_globe` scenario loads with globe, terrain, and site markers
- [ ] Verify `open_ground` and `urban_ghent` scenarios still work normally
- [ ] Verify coverage HUD shows region stats and "Set up scene here" button
- [ ] Verify `npm run build` succeeds with no TypeScript errors
- [ ] Verify non-cesium scenarios have no visual regressions
EOF
)" --base master
```

- [ ] **Step 4: Visual smoke test after deploy**

After the PR merges and deploys (~5 min), load `https://aegis.waves-ugent.be/?scenario=coverage_globe` and verify:
- Globe renders with terrain
- Coverage site points appear as colored dots
- Region boundaries show as colored rectangles at high altitude
- Region labels show country/region names with antenna counts
- Zooming in transitions smoothly
- "Set up scene here" button appears at low altitude
- Clicking it transitions to the OSM scene correctly
