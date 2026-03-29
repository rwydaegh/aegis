import { useState, useRef, useEffect } from 'react'
import * as Sentry from '@sentry/react'
import { loadLocation, cancelLocation, loadSceneGeometry, fetchCapabilities } from '@/api/client'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { loadBasestations } from '@/api/basestations'
import { useBaseStationsStore } from '@/stores/basestations'

function SionnaSceneSelector() {
  const scenes = useSceneStore(s => s.scenes)
  const [selected, setSelected] = useState('')
  const [loading, setLoading] = useState(false)

  if (scenes.length === 0) return null

  const selectClass = "w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground"
  const labelClass = "text-xs text-muted-foreground block mb-1"

  const handleLoad = async () => {
    if (!selected) return
    setLoading(true)
    try {
      const result = await loadSceneGeometry(selected)
      useSceneStore.getState().setSceneGeometry({
        vertices: result.vertices,
        indices: result.indices,
        faceColors: result.faceColors,
      })
      useSceneStore.getState().setLoadedScenePath(selected)
      useSceneStore.getState().setVoxelData(null)
    } catch (err) {
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', `Failed to load scene: ${(err as Error).message}`)
    }
    setLoading(false)
  }

  return (
    <div className="mb-3 pb-3 border-b border-border">
      <label className={labelClass}>Sionna scene</label>
      <select className={selectClass} value={selected} onChange={e => setSelected(e.target.value)}>
        <option value="">Select a scene...</option>
        {scenes.map(s => (
          <option key={s.path} value={s.path}>
            {s.name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
          </option>
        ))}
      </select>
      <button
        onClick={handleLoad}
        disabled={!selected || loading}
        className="mt-2 px-3 py-1.5 rounded text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {loading ? 'Loading...' : 'Load scene'}
      </button>
    </div>
  )
}

export default function ScenePanel() {
  const caps = useSceneStore(s => s.capabilities)
  const scenes = useSceneStore(s => s.scenes)
  const actualVoxelSize = useSceneStore(s => s.voxelData?.meta?.voxel_size)
  const locationLoading = useUIStore(s => s.locationLoading)
  const locationLog = useUIStore(s => s.locationLog)

  const [location, setLocation] = useState('')
  const [radius, setRadius] = useState(30)
  const [voxelSize, setVoxelSize] = useState(0.5)
  const [force, setForce] = useState(false)
  const [alsoLoadBS, setAlsoLoadBS] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    return () => { esRef.current?.close() }
  }, [])

  // Show Sionna scene selector even when location loading is unavailable
  const hasScenes = scenes.length > 0
  const hasLocation = caps?.has_location_loader
  const hasApiKey = caps?.has_api_key

  if (!hasScenes && !hasLocation && !hasApiKey) {
    return (
      <p className="text-xs text-muted-foreground">
        Set GOOGLE_API_KEY env var to enable location loading.
      </p>
    )
  }

  const handleLoad = () => {
    if (!location.trim()) return

    useUIStore.getState().setLocationLoading(true)
    useUIStore.getState().clearLocationLog()

    const es = loadLocation(location, radius, voxelSize, force)
    esRef.current = es

    es.addEventListener('progress', (e: MessageEvent) => {
      useUIStore.getState().appendLocationLog(e.data)
    })

    es.addEventListener('done', () => {
      es.close()
      esRef.current = null
      useUIStore.getState().setLocationLoading(false)
      useUIStore.getState().appendLocationLog('Done! Loading voxels...')
      // Re-fetch capabilities so useVoxelLoader picks up the new voxels
      fetchCapabilities().then(caps => {
        useSceneStore.getState().setCapabilities(caps)
      }).catch((err) => {
        Sentry.captureException(err)
        useNotificationStore.getState().addNotification('error', 'Failed to refresh after location load')
      })
      if (alsoLoadBS) {
        ;(async () => {
          try {
            const bsRes = await loadBasestations({ location, radius_m: radius })
            if (bsRes.basestations.length > 0) {
              const first = bsRes.basestations[0]
              useBaseStationsStore.getState().setBasestations(
                bsRes.basestations,
                { lat: first.latitude, lon: first.longitude },
              )
            }
          } catch (err) {
            console.warn('Auto-load base stations failed:', err)
          }
        })()
      }
    })

    es.addEventListener('error', () => {
      Sentry.captureException(new Error('Location load SSE connection lost'))
      es.close()
      esRef.current = null
      useUIStore.getState().setLocationLoading(false)
      useUIStore.getState().appendLocationLog('Error: connection lost')
    })
  }

  const handleCancel = () => {
    esRef.current?.close()
    esRef.current = null
    cancelLocation()
    useUIStore.getState().setLocationLoading(false)
    useUIStore.getState().appendLocationLog('Cancelled.')
  }

  const inputClass = "w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground"
  const labelClass = "text-xs text-muted-foreground block mt-2 mb-1"

  return (
    <div>
      {hasScenes && <SionnaSceneSelector />}

      {(hasLocation || hasApiKey) && (
        <>
          <label className={labelClass}>Location</label>
          <input type="text" className={inputClass} value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="e.g. Ghent, Belgium" disabled={locationLoading} />

          <label className={labelClass}>Radius (m)</label>
          <input type="number" className={inputClass} value={radius}
            min={10} max={500} step={10}
            onChange={e => setRadius(Number(e.target.value))} disabled={locationLoading} />

          <label className={labelClass}>Voxel size (m)</label>
          <input type="number" className={inputClass} value={voxelSize}
            min={0.1} max={5} step={0.1}
            onChange={e => setVoxelSize(Number(e.target.value))} disabled={locationLoading} />
          {actualVoxelSize != null && (
            <span className="text-[10px] text-muted-foreground mt-0.5 block">
              Actual: {actualVoxelSize.toFixed(2)} m (median)
            </span>
          )}

          <label className="flex items-center gap-2 text-xs text-muted-foreground mt-2">
            <input type="checkbox" checked={force} onChange={e => setForce(e.target.checked)} />
            Force re-download
          </label>

          <label className="flex items-center gap-2 text-xs cursor-pointer select-none mt-2">
            <input
              type="checkbox"
              className="rounded border-border accent-primary h-3.5 w-3.5"
              checked={alsoLoadBS}
              onChange={e => setAlsoLoadBS(e.target.checked)}
            />
            <span className="text-foreground/70">Also load base stations</span>
          </label>

          <div className="flex gap-2 mt-3">
            {!locationLoading ? (
              <button onClick={handleLoad}
                className="px-3 py-1.5 rounded text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90">
                Load
              </button>
            ) : (
              <button onClick={handleCancel}
                className="px-3 py-1.5 rounded text-xs font-medium bg-destructive text-white hover:bg-destructive/90">
                Cancel
              </button>
            )}
          </div>

          {locationLog.length > 0 && (
            <div className="mt-3 max-h-[120px] overflow-y-auto bg-background rounded p-2 text-[10px] text-muted-foreground font-mono whitespace-pre-wrap">
              {locationLog.join('\n')}
            </div>
          )}
        </>
      )}

      <div className="mt-4 pt-3 border-t border-border">
        <button
          onClick={() => {
            fetch('/api/clear-cache', { method: 'POST' }).catch(() => {})
            useSceneStore.getState().clearScene()
            useSimulationStore.getState().clearResults()
            useSimulationStore.getState().setBodyOffset([0, 0, 0])
            useSimulationStore.getState().setBodyRotationY(0)
          }}
          className="w-full px-3 py-1.5 rounded text-xs font-medium bg-destructive text-white hover:bg-destructive/90"
        >
          Clear Scene
        </button>
      </div>
    </div>
  )
}
