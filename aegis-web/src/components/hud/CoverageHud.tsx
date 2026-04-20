import * as Sentry from '@sentry/react'
import { useCoverageStore } from '@/stores/coverage'
import { useUIStore } from '@/stores/ui'
import { useEnvironmentStore } from '@/stores/environment'
import { useBaseStationsStore } from '@/stores/basestations'
import { useNotificationStore } from '@/stores/notifications'
import { loadBasestations } from '@/api/basestations'
import { isClientError } from '@/api/client'
import { Globe, MapPin, ArrowLeft, RefreshCw, Shield } from 'lucide-react'

/** Zoom level ~14 corresponds to roughly <5 km altitude equivalent */
const TRANSITION_ZOOM = 14

function CoverageHudInner() {
  const enabled = useCoverageStore(s => s.enabled)
  const activeScenario = useUIStore(s => s.activeScenario)
  const zoom = useCoverageStore(s => s.zoom)
  const cameraLatLon = useCoverageStore(s => s.cameraLatLon)
  const regions = useCoverageStore(s => s.regions)
  const loading = useCoverageStore(s => s.loading)
  const error = useCoverageStore(s => s.error)
  const colorMode = useCoverageStore(s => s.colorMode)
  const setColorMode = useCoverageStore(s => s.setColorMode)

  const complianceZoneEnabled = useCoverageStore(s => s.complianceZoneEnabled)
  const complianceZoneLoading = useCoverageStore(s => s.complianceZoneLoading)
  const complianceZone = useCoverageStore(s => s.complianceZone)
  const hasSessionBasestations = useBaseStationsStore(s => s.basestations.length > 0)

  const isCoverageScenario = activeScenario === 'coverage_globe'
  if (!isCoverageScenario) return null

  const showTransitionButton = enabled && zoom >= TRANSITION_ZOOM && cameraLatLon

  const handleToggleCompliance = () => {
    const store = useCoverageStore.getState()
    if (!complianceZoneEnabled) {
      store.setComplianceZoneEnabled(true)
      if (!store.complianceZone) {
        store.fetchComplianceZone()
      }
    } else {
      store.setComplianceZoneEnabled(false)
    }
  }

  const handleSetupScene = () => {
    const ll = useCoverageStore.getState().cameraLatLon
    if (!ll) return

    useCoverageStore.getState().setEnabled(false)
    const env = useEnvironmentStore.getState()
    env.setSource('osm')
    env.setLocation(ll.lat, ll.lon)
    env.fetchOSM().catch(err => {
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', `Failed to load environment: ${(err as Error).message}`)
    })
    loadBasestations({ lat: ll.lat, lon: ll.lon, radius_m: 500 }).then(resp => {
      useBaseStationsStore.getState().setBasestations(resp.basestations, ll)
    }).catch(err => {
      if (!isClientError(err)) Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', `Failed to load base stations: ${(err as Error).message}`)
    })
  }

  const handleBackToGlobe = () => {
    useEnvironmentStore.getState().setSource('coverage')
    useCoverageStore.getState().setEnabled(true)
    useCoverageStore.getState().clearComplianceZone()
    useBaseStationsStore.getState().clear()
  }

  return (
    <div className="pointer-events-auto flex flex-col gap-2 z-20">
      {enabled && (
        <div className="rounded-lg bg-zinc-900/90 border border-zinc-700 p-3 text-xs text-white shadow-lg">
          <div className="flex items-center gap-2 mb-2 font-medium">
            <Globe size={14} />
            Coverage
          </div>
          {loading && (
            <div className="text-zinc-400">Loading coverage data...</div>
          )}
          {error && (
            <div className="text-red-400">
              <div>Failed to load coverage: {error}</div>
              <button
                onClick={() => useCoverageStore.getState().retry()}
                className="mt-1 flex items-center gap-1 text-zinc-300 hover:text-white transition-colors"
              >
                <RefreshCw size={12} />
                Retry
              </button>
            </div>
          )}
          {!loading && !error && (
            <div className="text-zinc-400">
              {regions.length} regions, {regions.reduce((s, r) => s + r.count, 0).toLocaleString()} antennas
            </div>
          )}
          {!loading && !error && (
            <div className="mt-2 pt-2 border-t border-zinc-700/50">
              <label className="text-zinc-500 block mb-1">Color by</label>
              <select
                value={colorMode}
                onChange={e => setColorMode(e.target.value as 'density' | 'operator' | 'technology' | 'region')}
                className="w-full bg-zinc-800 border border-zinc-600 rounded text-xs px-2 py-1 text-white"
              >
                <option value="density">Density heatmap</option>
                <option value="operator">Operator</option>
                <option value="technology">Technology</option>
                <option value="region">Country</option>
              </select>
            </div>
          )}
          {!loading && !error && (
            <div className="mt-2 pt-2 border-t border-zinc-700/50">
              <button
                onClick={handleToggleCompliance}
                disabled={complianceZoneLoading || !hasSessionBasestations}
                title={!hasSessionBasestations ? 'Set up a scene first to compute compliance zones' : undefined}
                className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-colors ${
                  complianceZoneEnabled
                    ? 'bg-emerald-700/30 text-emerald-300 border border-emerald-600/50'
                    : 'bg-zinc-800 text-zinc-400 border border-zinc-600 hover:text-white hover:bg-zinc-700'
                } disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-zinc-800 disabled:hover:text-zinc-400`}
              >
                <Shield size={12} />
                {complianceZoneLoading ? 'Computing...' : 'ICNIRP compliance zones'}
              </button>
              {complianceZoneEnabled && complianceZone && (
                <div className="mt-2 space-y-0.5 text-[10px]">
                  <div className="text-zinc-500 mb-1">Compliance margin (free-space estimate)</div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: 'rgb(248, 113, 113)' }} />
                    <span className="text-zinc-400">Exceeded (margin &lt; 0 dB)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: 'rgb(251, 146, 60)' }} />
                    <span className="text-zinc-400">Near limit (0-3 dB)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: 'rgb(250, 204, 21)' }} />
                    <span className="text-zinc-400">Caution (3-10 dB)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: 'rgb(74, 222, 128)' }} />
                    <span className="text-zinc-400">Safe (&gt; 10 dB)</span>
                  </div>
                  <div className="text-zinc-600 mt-1">
                    {complianceZone.n_stations} stations, {(complianceZone.freq_hz_dominant / 1e9).toFixed(1)} GHz dominant
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {showTransitionButton && (
        <button
          onClick={handleSetupScene}
          className="flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 px-3 py-2 text-sm text-white font-medium shadow-lg transition-colors"
        >
          <MapPin size={14} />
          Set up scene here
        </button>
      )}

      {!enabled && isCoverageScenario && (
        <button
          onClick={handleBackToGlobe}
          className="flex items-center gap-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 px-3 py-2 text-sm text-white font-medium shadow-lg transition-colors"
        >
          <ArrowLeft size={14} />
          Back to globe
        </button>
      )}
    </div>
  )
}

export function CoverageHud() {
  const isCoverageScenario = useUIStore(s => s.activeScenario) === 'coverage_globe'
  if (!isCoverageScenario) return null
  return <CoverageHudInner />
}
