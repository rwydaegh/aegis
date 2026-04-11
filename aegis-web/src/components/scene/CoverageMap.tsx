import { useCallback, useEffect, useRef, useState } from 'react'
import { APIProvider, Map, Map3D, MapMode, useMap } from '@vis.gl/react-google-maps'
import { GoogleMapsOverlay } from '@deck.gl/google-maps'
import { useSceneStore } from '@/stores/scene'
import { useCoverageStore } from '@/stores/coverage'
import { buildCoverageLayers } from './coverageLayers'

/** Zoom level at which we switch from 2D heatmap to 3D photorealistic view */
const SWITCH_TO_3D_ZOOM = 15

function DeckOverlay() {
  const map = useMap()
  const [overlay] = useState(() => new GoogleMapsOverlay({}))

  const siteLats = useCoverageStore(s => s.siteLats)
  const siteLons = useCoverageStore(s => s.siteLons)
  const siteOpIndices = useCoverageStore(s => s.siteOpIndices)
  const siteTechIndices = useCoverageStore(s => s.siteTechIndices)
  const siteRegionIndices = useCoverageStore(s => s.siteRegionIndices)
  const siteAntennaCounts = useCoverageStore(s => s.siteAntennaCounts)
  const siteCount = useCoverageStore(s => s.siteCount)
  const zoom = useCoverageStore(s => s.zoom)
  const colorMode = useCoverageStore(s => s.colorMode)

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
    const z = map.getZoom()
    if (z != null) useCoverageStore.getState().setZoom(z)
    return () => listener.remove()
  }, [map])

  // Track map center for CoverageHud transition
  useEffect(() => {
    if (!map) return
    const listener = map.addListener('center_changed', () => {
      const center = map.getCenter()
      if (center) {
        useCoverageStore.getState().setCameraLatLon({
          lat: center.lat(),
          lon: center.lng(),
        })
      }
    })
    return () => listener.remove()
  }, [map])

  // Hover/click handlers
  const onSiteHover = useCallback((info: any) => {
    const store = useCoverageStore.getState()
    if (info.index >= 0) {
      store.setHoveredSiteIndex(info.index)
      store.setHoveredScreenCoords({ x: info.x, y: info.y })
    } else {
      store.setHoveredSiteIndex(null)
      store.setHoveredScreenCoords(null)
    }
  }, [])

  const onSiteClick = useCallback((info: any) => {
    if (info.index >= 0) {
      useCoverageStore.getState().setSelectedSiteIndex(info.index)
    }
  }, [])

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

/** Photorealistic 3D view using Map3DElement */
function Photorealistic3DView({ center }: { center: { lat: number; lon: number } }) {
  const handleCameraChanged = useCallback((ev: any) => {
    const detail = ev.detail
    if (detail?.center) {
      useCoverageStore.getState().setCameraLatLon({
        lat: detail.center.lat,
        lon: detail.center.lng,
      })
    }
  }, [])

  return (
    <Map3D
      style={{ width: '100%', height: '100%' }}
      mode={MapMode.SATELLITE}
      defaultCenter={{ lat: center.lat, lng: center.lon, altitude: 200 }}
      defaultTilt={60}
      defaultHeading={0}
      defaultRange={500}
      onCameraChanged={handleCameraChanged}
    />
  )
}

export function CoverageMap() {
  const googleApiKey = useSceneStore(s => s.capabilities?.google_api_key) ?? ''
  const googleMapId = useSceneStore(s => s.capabilities?.google_map_id) || undefined
  const zoom = useCoverageStore(s => s.zoom)
  const cameraLatLon = useCoverageStore(s => s.cameraLatLon)
  const [show3D, setShow3D] = useState(false)
  const lastCenterRef = useRef<{ lat: number; lon: number }>({ lat: 48.8, lon: 2.3 })

  // Track center for 3D transition
  useEffect(() => {
    if (cameraLatLon) lastCenterRef.current = cameraLatLon
  }, [cameraLatLon])

  // Auto-switch to 3D when zoomed in enough (if Map ID is configured)
  useEffect(() => {
    if (googleMapId && zoom >= SWITCH_TO_3D_ZOOM && !show3D) {
      setShow3D(true)
    }
  }, [zoom, googleMapId, show3D])

  if (!googleApiKey) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-zinc-950 text-zinc-400 text-sm">
        Google API key not configured. Set GOOGLE_API_KEY on the server.
      </div>
    )
  }

  // Show photorealistic 3D view when zoomed in
  if (show3D && googleMapId) {
    return (
      <APIProvider apiKey={googleApiKey} version="beta">
        <Photorealistic3DView center={lastCenterRef.current} />
        <button
          onClick={() => {
            setShow3D(false)
            useCoverageStore.getState().setZoom(10)
          }}
          className="absolute top-16 left-1/2 -translate-x-1/2 z-30 px-4 py-2 bg-zinc-800/90 hover:bg-zinc-700 text-white text-sm rounded-lg border border-zinc-600 shadow-lg transition-colors"
        >
          Back to heatmap overview
        </button>
      </APIProvider>
    )
  }

  return (
    <APIProvider apiKey={googleApiKey}>
      <Map
        style={{ width: '100%', height: '100%' }}
        defaultCenter={{ lat: 48.8, lng: 2.3 }}
        defaultZoom={4}
        mapTypeId="hybrid"
        disableDefaultUI
        gestureHandling="greedy"
        clickableIcons={false}
      />
      <DeckOverlay />
    </APIProvider>
  )
}
