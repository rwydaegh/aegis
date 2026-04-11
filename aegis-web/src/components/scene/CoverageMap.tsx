import { useCallback, useEffect, useState } from 'react'
import { APIProvider, Map, useMap } from '@vis.gl/react-google-maps'
import { GoogleMapsOverlay } from '@deck.gl/google-maps'
import { useSceneStore } from '@/stores/scene'
import { useCoverageStore } from '@/stores/coverage'
import { buildCoverageLayers } from './coverageLayers'

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
