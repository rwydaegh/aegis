import { useEffect, useRef, useCallback } from 'react'
import { Viewer as ResiumViewer } from 'resium'
import {
  Ion,
  Viewer,
  Cartographic,
  Cartesian3,
  Math as CesiumMath,
  Terrain,
  Cesium3DTileset,
} from 'cesium'
import { useSceneStore } from '@/stores/scene'
import { useEnvironmentStore } from '@/stores/environment'
import { useCoverageStore } from '@/stores/coverage'
import { addCoverageOverlay, type CoverageOverlayHandle } from './CoverageOverlay3D'

export function CesiumGlobe() {
  const viewerRef = useRef<Viewer | null>(null)
  const tickListenerRef = useRef<(() => void) | null>(null)
  const overlayRef = useRef<CoverageOverlayHandle | null>(null)
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

    // Style credits to be subtle but visible (required by Cesium ion ToS)
    const creditEl = viewer.cesiumWidget.creditContainer as HTMLElement
    creditEl.style.fontSize = '10px'
    creditEl.style.opacity = '0.7'

    // Load terrain
    try {
      viewer.scene.setTerrain(Terrain.fromWorldTerrain())
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
      destination: Cartesian3.fromDegrees(10, 20, 20_000_000),
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

    // If coverage data was already loaded before the viewer was ready,
    // add the overlay now (the useEffect fast-path would have missed it
    // because viewerRef.current was still null at that point).
    const coverageState = useCoverageStore.getState()
    if (coverageState.loaded && coverageState.siteLats && coverageState.siteLons && coverageState.siteOpIndices) {
      if (overlayRef.current) overlayRef.current.destroy()
      overlayRef.current = addCoverageOverlay(
        viewer,
        coverageState.siteLats,
        coverageState.siteLons,
        coverageState.siteOpIndices,
        coverageState.siteCount,
        coverageState.regions,
      )
    }
  }, [googleApiKey])

  // Cleanup tick listener on unmount
  useEffect(() => {
    return () => {
      if (viewerRef.current && tickListenerRef.current) {
        viewerRef.current.clock.onTick.removeEventListener(tickListenerRef.current)
      }
    }
  }, [])

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
