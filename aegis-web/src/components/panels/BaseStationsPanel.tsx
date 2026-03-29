import { useState } from 'react'
import * as Sentry from '@sentry/react'
import { useBaseStationsStore } from '@/stores/basestations'
import { loadBasestations } from '@/api/basestations'
import { useBaseStationsDosimetry } from '@/hooks/useBaseStationsDosimetry'
import { useNotificationStore } from '@/stores/notifications'

export default function BaseStationsPanel() {
  const [location, setLocation] = useState('Brussels, Belgium')
  const [radius, setRadius] = useState(500)

  const basestations = useBaseStationsStore(s => s.basestations)
  const isLoading = useBaseStationsStore(s => s.isLoading)
  const isComputing = useBaseStationsStore(s => s.isComputing)
  const operators = useBaseStationsStore(s => s.operators)
  const technologies = useBaseStationsStore(s => s.technologies)
  const enabledOperators = useBaseStationsStore(s => s.enabledOperators)
  const enabledTechnologies = useBaseStationsStore(s => s.enabledTechnologies)
  const activeCount = useBaseStationsStore(s => s.activeCount)
  const toggleOperator = useBaseStationsStore(s => s.toggleOperator)
  const toggleTechnology = useBaseStationsStore(s => s.toggleTechnology)
  const setBasestations = useBaseStationsStore(s => s.setBasestations)
  const setLoading = useBaseStationsStore(s => s.setLoading)
  const clear = useBaseStationsStore(s => s.clear)

  const computeExposure = useBaseStationsDosimetry()

  const selectClass =
    'w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring'
  const inputClass = selectClass
  const labelClass = 'text-xs text-muted-foreground block mt-3 mb-1'

  async function handleLoad() {
    setLoading(true)
    try {
      const res = await loadBasestations({ location, radius_m: radius })
      if (res.basestations.length > 0) {
        const first = res.basestations[0]
        setBasestations(res.basestations, { lat: first.latitude, lon: first.longitude })
      }
      useNotificationStore.getState().addNotification(
        'info',
        `Loaded ${res.count} antennas`,
      )
    } catch (err) {
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification(
        'error',
        `Load failed: ${(err as Error).message}`,
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <label className={labelClass}>Location</label>
      <input
        type="text"
        className={inputClass}
        value={location}
        onChange={e => setLocation(e.target.value)}
        placeholder="e.g. Brussels, Belgium or 50.85, 4.35"
        onKeyDown={e => e.key === 'Enter' && !isLoading && handleLoad()}
      />

      <label className={labelClass}>Radius: {radius} m</label>
      <input
        type="range"
        className="w-full accent-primary"
        min={100}
        max={2000}
        step={50}
        value={radius}
        onChange={e => setRadius(Number(e.target.value))}
      />

      <div className="flex gap-2 mt-3">
        <button
          className="flex-1 px-3 py-1.5 text-xs rounded border border-primary/40 bg-primary/15 text-primary hover:bg-primary/25 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          onClick={handleLoad}
          disabled={isLoading}
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-1.5">
              <span className="w-3 h-3 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              Loading...
            </span>
          ) : 'Load'}
        </button>
        {basestations.length > 0 && (
          <button
            className="px-3 py-1.5 text-xs rounded border border-border bg-muted/50 text-foreground hover:bg-muted transition-colors cursor-pointer"
            onClick={clear}
          >
            Clear
          </button>
        )}
      </div>

      {basestations.length > 0 && (
        <>
          <p className="text-xs text-muted-foreground mt-3">
            {basestations.length} antennas loaded ({activeCount} active)
          </p>

          {operators.length > 0 && (
            <>
              <label className={labelClass}>Operators</label>
              <div className="flex flex-col gap-1 pl-0.5">
                {operators.map(op => (
                  <label key={op} className="flex items-center gap-2 text-xs cursor-pointer select-none">
                    <input
                      type="checkbox"
                      className="rounded border-border accent-primary h-3.5 w-3.5"
                      checked={enabledOperators.has(op)}
                      onChange={() => toggleOperator(op)}
                    />
                    <span className="text-foreground">{op}</span>
                  </label>
                ))}
              </div>
            </>
          )}

          {technologies.length > 0 && (
            <>
              <label className={labelClass}>Technologies</label>
              <div className="flex flex-col gap-1 pl-0.5">
                {technologies.map(tech => (
                  <label key={tech} className="flex items-center gap-2 text-xs cursor-pointer select-none">
                    <input
                      type="checkbox"
                      className="rounded border-border accent-primary h-3.5 w-3.5"
                      checked={enabledTechnologies.has(tech)}
                      onChange={() => toggleTechnology(tech)}
                    />
                    <span className="text-foreground">{tech}</span>
                  </label>
                ))}
              </div>
            </>
          )}

          <button
            className="w-full mt-3 px-3 py-1.5 text-xs rounded border border-primary/40 bg-primary/15 text-primary hover:bg-primary/25 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={computeExposure}
            disabled={isComputing || activeCount === 0}
          >
            {isComputing ? (
              <span className="flex items-center justify-center gap-1.5">
                <span className="w-3 h-3 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                Computing...
              </span>
            ) : 'Compute exposure'}
          </button>
        </>
      )}
    </div>
  )
}
