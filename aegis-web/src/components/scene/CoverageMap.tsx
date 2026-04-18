import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { APIProvider, Map, Map3D, MapMode, Marker3D, AltitudeMode, useMap } from '@vis.gl/react-google-maps'
import { GoogleMapsOverlay } from '@deck.gl/google-maps'
import { useSceneStore } from '@/stores/scene'
import { useCoverageStore } from '@/stores/coverage'
import { buildCoverageLayers, buildComplianceZoneLayer, OP_COLORS } from './coverageLayers'
import { Radio, Building2, Layers, MapPin, X, Signal } from 'lucide-react'

const FALLBACK_COVERAGE_MAP = {
  switch_to_3d_zoom: 15,
  max_3d_markers: 2000,
  marker_radius_deg: 0.05,
}

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
  const complianceZone = useCoverageStore(s => s.complianceZone)
  const complianceZoneEnabled = useCoverageStore(s => s.complianceZoneEnabled)

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

    const coverageLayers = buildCoverageLayers({
      siteLats, siteLons, siteOpIndices, siteTechIndices,
      siteRegionIndices, siteAntennaCounts,
      siteCount, zoom, colorMode,
      onSiteHover, onSiteClick,
    })

    // Add compliance zone layer below coverage layers
    const complianceLayers = complianceZoneEnabled
      ? buildComplianceZoneLayer(complianceZone)
      : []

    overlay.setProps({ layers: [...complianceLayers, ...coverageLayers] })
  }, [siteLats, siteLons, siteOpIndices, siteTechIndices, siteRegionIndices,
      siteAntennaCounts, siteCount, zoom, colorMode, overlay, onSiteHover, onSiteClick,
      complianceZone, complianceZoneEnabled])

  return null
}

/** Site info for 3D markers */
interface SiteInfo {
  index: number
  lat: number
  lon: number
  operator: string
  technology: string
  region: string
  antennaCount: number
  opIndex: number
}

/** Rich tooltip panel for a selected antenna site */
function SiteInfoPanel({ site, onClose }: { site: SiteInfo; onClose: () => void }) {
  const color = OP_COLORS[site.opIndex % OP_COLORS.length]
  const colorHex = `rgb(${color[0]}, ${color[1]}, ${color[2]})`

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-40 w-80 max-w-[90vw] bg-zinc-900/95 backdrop-blur-sm border border-zinc-700 rounded-xl shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-700/50" style={{ borderLeftColor: colorHex, borderLeftWidth: 4 }}>
        <div className="flex items-center gap-2">
          <Radio size={16} className="text-blue-400" />
          <span className="text-white font-medium text-sm">Base Station</span>
        </div>
        <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors p-1 rounded hover:bg-zinc-700">
          <X size={14} />
        </button>
      </div>

      {/* Content */}
      <div className="px-4 py-3 space-y-3">
        {/* Operator */}
        <div className="flex items-start gap-3">
          <Building2 size={14} className="text-zinc-500 mt-0.5 shrink-0" />
          <div>
            <div className="text-zinc-500 text-xs">Operator</div>
            <div className="text-white text-sm font-medium" style={{ color: colorHex }}>{site.operator}</div>
          </div>
        </div>

        {/* Technology */}
        <div className="flex items-start gap-3">
          <Signal size={14} className="text-zinc-500 mt-0.5 shrink-0" />
          <div>
            <div className="text-zinc-500 text-xs">Technology</div>
            <div className="text-white text-sm">{site.technology}</div>
          </div>
        </div>

        {/* Antennas */}
        <div className="flex items-start gap-3">
          <Layers size={14} className="text-zinc-500 mt-0.5 shrink-0" />
          <div>
            <div className="text-zinc-500 text-xs">Antennas at site</div>
            <div className="text-white text-sm">{site.antennaCount}</div>
          </div>
        </div>

        {/* Region */}
        <div className="flex items-start gap-3">
          <MapPin size={14} className="text-zinc-500 mt-0.5 shrink-0" />
          <div>
            <div className="text-zinc-500 text-xs">Region</div>
            <div className="text-white text-sm">{site.region.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
          </div>
        </div>

        {/* Coordinates */}
        <div className="pt-2 border-t border-zinc-800 flex gap-4">
          <div>
            <div className="text-zinc-600 text-[10px] uppercase tracking-wider">Lat</div>
            <div className="text-zinc-400 text-xs font-mono">{site.lat.toFixed(5)}</div>
          </div>
          <div>
            <div className="text-zinc-600 text-[10px] uppercase tracking-wider">Lon</div>
            <div className="text-zinc-400 text-xs font-mono">{site.lon.toFixed(5)}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

/** Photorealistic 3D view with antenna markers */
function Photorealistic3DView({ center }: { center: { lat: number; lon: number } }) {
  const siteLats = useCoverageStore(s => s.siteLats)
  const siteLons = useCoverageStore(s => s.siteLons)
  const siteOpIndices = useCoverageStore(s => s.siteOpIndices)
  const siteTechIndices = useCoverageStore(s => s.siteTechIndices)
  const siteRegionIndices = useCoverageStore(s => s.siteRegionIndices)
  const siteAntennaCounts = useCoverageStore(s => s.siteAntennaCounts)
  const siteCount = useCoverageStore(s => s.siteCount)
  const operatorNames = useCoverageStore(s => s.operatorNames)
  const technologyNames = useCoverageStore(s => s.technologyNames)
  const regionNames = useCoverageStore(s => s.regionNames)
  const cameraLatLon = useCoverageStore(s => s.cameraLatLon)
  const [selectedSite, setSelectedSite] = useState<SiteInfo | null>(null)

  // Filter sites near the camera center
  const visibleSites = useMemo(() => {
    if (!siteLats || !siteLons || !siteOpIndices || !siteTechIndices || !siteRegionIndices || !siteAntennaCounts) return []
    const cLat = cameraLatLon?.lat ?? center.lat
    const cLon = cameraLatLon?.lon ?? center.lon
    const cmCfg = useSceneStore.getState().viewerConfig?.coverage_map ?? FALLBACK_COVERAGE_MAP
    const r = cmCfg.marker_radius_deg
    const maxMarkers = cmCfg.max_3d_markers

    const sites: SiteInfo[] = []
    for (let i = 0; i < siteCount && sites.length < maxMarkers; i++) {
      const lat = siteLats[i]
      const lon = siteLons[i]
      if (lat >= cLat - r && lat <= cLat + r && lon >= cLon - r && lon <= cLon + r) {
        sites.push({
          index: i,
          lat, lon,
          operator: operatorNames[siteOpIndices[i]] ?? 'Unknown',
          technology: technologyNames[siteTechIndices[i]] ?? 'Unknown',
          region: regionNames[siteRegionIndices[i]] ?? 'Unknown',
          antennaCount: siteAntennaCounts[i],
          opIndex: siteOpIndices[i],
        })
      }
    }
    return sites
  }, [siteLats, siteLons, siteOpIndices, siteTechIndices, siteRegionIndices,
      siteAntennaCounts, siteCount, operatorNames, technologyNames, regionNames,
      cameraLatLon, center])

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
    <>
      <Map3D
        style={{ width: '100%', height: '100%' }}
        mode={MapMode.SATELLITE}
        defaultCenter={{ lat: center.lat, lng: center.lon, altitude: 200 }}
        defaultTilt={60}
        defaultHeading={0}
        defaultRange={500}
        onCameraChanged={handleCameraChanged}
      >
        {visibleSites.map(site => {
          const color = OP_COLORS[site.opIndex % OP_COLORS.length]
          return (
            <Marker3D
              key={site.index}
              position={{ lat: site.lat, lng: site.lon, altitude: 30 }}
              altitudeMode={AltitudeMode.RELATIVE_TO_GROUND}
              extruded
              label={site.antennaCount > 1 ? `${site.antennaCount}` : undefined}
              onClick={() => setSelectedSite(site)}
            >
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: '50%',
                  backgroundColor: `rgb(${color[0]}, ${color[1]}, ${color[2]})`,
                  border: '2px solid white',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
                  cursor: 'pointer',
                }}
              />
            </Marker3D>
          )
        })}
      </Map3D>

      {/* Marker count indicator */}
      <div className="absolute top-16 right-4 z-30 px-3 py-1.5 bg-zinc-900/80 text-zinc-400 text-xs rounded-lg border border-zinc-700">
        <Radio size={12} className="inline mr-1.5" />
        {visibleSites.length} sites in view
      </div>

      {/* Selected site info panel */}
      {selectedSite && (
        <SiteInfoPanel site={selectedSite} onClose={() => setSelectedSite(null)} />
      )}
    </>
  )
}

export function CoverageMap() {
  const googleApiKey = useSceneStore(s => s.capabilities?.google_api_key) ?? ''
  const googleMapId = useSceneStore(s => s.capabilities?.google_map_id) || undefined
  const zoom = useCoverageStore(s => s.zoom)
  const cameraLatLon = useCoverageStore(s => s.cameraLatLon)
  const coverageMapCfg = useSceneStore(s => s.viewerConfig?.coverage_map) ?? FALLBACK_COVERAGE_MAP
  const switchTo3dZoom = coverageMapCfg.switch_to_3d_zoom
  const [show3D, setShow3D] = useState(false)
  const lastCenterRef = useRef<{ lat: number; lon: number }>({ lat: 48.8, lon: 2.3 })

  // Track center for 3D transition
  useEffect(() => {
    if (cameraLatLon) lastCenterRef.current = cameraLatLon
  }, [cameraLatLon])

  // Auto-switch to 3D when zoomed in enough (if Map ID is configured)
  useEffect(() => {
    if (googleMapId && zoom >= switchTo3dZoom && !show3D) {
      setShow3D(true)
    }
  }, [zoom, googleMapId, show3D, switchTo3dZoom])

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
            // Restore zoom to just below the 3D threshold so we stay in 2D
            useCoverageStore.getState().setZoom(switchTo3dZoom - 3)
          }}
          className="absolute top-16 left-1/2 -translate-x-1/2 z-30 px-4 py-2 bg-zinc-800/90 hover:bg-zinc-700 text-white text-sm rounded-lg border border-zinc-600 shadow-lg transition-colors"
        >
          Back to heatmap overview
        </button>
      </APIProvider>
    )
  }

  // Use last known center when returning from 3D view, otherwise default to Europe
  const mapCenter = lastCenterRef.current.lat !== 48.8 || lastCenterRef.current.lon !== 2.3
    ? { lat: lastCenterRef.current.lat, lng: lastCenterRef.current.lon }
    : { lat: 48.8, lng: 2.3 }
  const mapZoom = mapCenter.lat !== 48.8 || mapCenter.lng !== 2.3
    ? Math.min(zoom, switchTo3dZoom - 3)
    : 4

  return (
    <APIProvider apiKey={googleApiKey}>
      <Map
        style={{ width: '100%', height: '100%' }}
        defaultCenter={mapCenter}
        defaultZoom={mapZoom}
        mapTypeId="hybrid"
        disableDefaultUI
        gestureHandling="greedy"
        clickableIcons={false}
      />
      <DeckOverlay />
    </APIProvider>
  )
}
