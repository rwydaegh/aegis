import { useCoverageStore } from '@/stores/coverage'
import { useUIStore } from '@/stores/ui'
import { useEnvironmentStore } from '@/stores/environment'
import { useBaseStationsStore } from '@/stores/basestations'
import { loadBasestations } from '@/api/basestations'
import { Globe, MapPin, ArrowLeft } from 'lucide-react'

const TRANSITION_ALTITUDE_M = 5_000

function CoverageHudInner() {
  const enabled = useCoverageStore(s => s.enabled)
  const activeScenario = useUIStore(s => s.activeScenario)
  const cameraAltitude = useCoverageStore(s => s.cameraAltitude)
  const cameraLatLon = useCoverageStore(s => s.cameraLatLon)
  const regions = useCoverageStore(s => s.regions)
  const loading = useCoverageStore(s => s.loading)
  const error = useCoverageStore(s => s.error)

  const isCoverageScenario = activeScenario === 'coverage_globe'
  if (!isCoverageScenario) return null

  const showTransitionButton = enabled && cameraAltitude < TRANSITION_ALTITUDE_M && cameraLatLon

  const handleSetupScene = () => {
    const ll = useCoverageStore.getState().cameraLatLon
    if (!ll) return

    useCoverageStore.getState().setEnabled(false)
    useEnvironmentStore.getState().setLocation(ll.lat, ll.lon)
    loadBasestations({ lat: ll.lat, lon: ll.lon, radius_m: 500 }).then(resp => {
      useBaseStationsStore.getState().setBasestations(resp.basestations, ll)
    })
  }

  const handleBackToGlobe = () => {
    useCoverageStore.getState().setEnabled(true)
    useBaseStationsStore.getState().clear()
  }

  return (
    <div className="absolute bottom-16 left-4 pointer-events-auto flex flex-col gap-2 z-20">
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
              Failed to load coverage: {error}
              <button
                onClick={() => {
                  useCoverageStore.setState({ error: null })
                  useCoverageStore.getState().fetch()
                }}
                className="ml-2 underline text-red-300 hover:text-white"
              >
                Retry
              </button>
            </div>
          )}
          {!loading && !error && (
            <>
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#22c55e' }} />
                  <span className="text-zinc-300">Rich data (&gt;80%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#f59e0b' }} />
                  <span className="text-zinc-300">Partial (40-80%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#ef4444' }} />
                  <span className="text-zinc-300">Location only (&lt;40%)</span>
                </div>
              </div>
              <div className="mt-2 text-zinc-400">
                {regions.length} regions, {regions.reduce((s, r) => s + r.count, 0).toLocaleString()} antennas
              </div>
            </>
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
