import { useCallback, useEffect, useRef, useState } from 'react'
import * as Sentry from '@sentry/react'
import { useBaseStationsStore } from '@/stores/basestations'
import { loadBasestations } from '@/api/basestations'
import { searchPatterns } from '@/api/patterns'
import type { PatternSearchResult } from '@/api/patterns'
import { useBaseStationsDosimetry } from '@/hooks/useBaseStationsDosimetry'
import { useNotificationStore } from '@/stores/notifications'

export default function BaseStationsPanel() {
  const [location, setLocation] = useState('Brussels, Belgium')
  const [radius, setRadius] = useState(500)
  const [autoLoad, setAutoLoad] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [patternQuery, setPatternQuery] = useState('')
  const [patternResults, setPatternResults] = useState<PatternSearchResult[]>([])
  const [patternTotal, setPatternTotal] = useState(0)
  const [showPatterns, setShowPatterns] = useState(false)

  const exposureMode = useBaseStationsStore(s => s.exposureMode)
  const setExposureMode = useBaseStationsStore(s => s.setExposureMode)

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

  const handleLoad = useCallback(async () => {
    setLoading(true)
    try {
      const res = await loadBasestations({ location, radius_m: radius })
      if (res.basestations.length > 0) {
        const first = res.basestations[0]
        setBasestations(res.basestations, { lat: first.latitude, lon: first.longitude })
      } else {
        clear()
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
  }, [location, radius, setLoading, setBasestations])

  const handlePatternSearch = useCallback(async () => {
    if (!patternQuery.trim()) return
    try {
      const res = await searchPatterns(patternQuery)
      setPatternResults(res.results)
      setPatternTotal(res.total)
    } catch { /* silent */ }
  }, [patternQuery])

  useEffect(() => {
    if (!autoLoad) return
    if (location.trim().length < 2) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      handleLoad()
    }, 800)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [autoLoad, location, radius, handleLoad])

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

      <label className="flex items-center gap-2 mt-3 text-xs cursor-pointer select-none">
        <input
          type="checkbox"
          className="rounded border-border accent-primary h-3.5 w-3.5"
          checked={autoLoad}
          onChange={e => setAutoLoad(e.target.checked)}
        />
        <span className="text-foreground">Auto-load when location changes</span>
      </label>

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

          <label className={labelClass}>Exposure mode</label>
          <select
            className={selectClass}
            value={exposureMode}
            onChange={e => setExposureMode(e.target.value as typeof exposureMode)}
          >
            <option value="theoretical_max">Theoretical maximum (IEC 62232)</option>
            <option value="actual_max">Actual maximum (IEC TR 62669)</option>
            <option value="typical">Typical (50% traffic load)</option>
          </select>

          <button
            className="w-full mt-3 px-2 py-1 text-xs text-left text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            onClick={() => setShowPatterns(!showPatterns)}
          >
            {showPatterns ? '- ' : '+ '}Antenna pattern library
          </button>

          {showPatterns && (
            <div className="mt-1 space-y-1">
              <div className="flex gap-1">
                <input
                  type="text"
                  className={inputClass}
                  value={patternQuery}
                  onChange={e => setPatternQuery(e.target.value)}
                  placeholder="Search model (e.g. 742215)"
                  onKeyDown={e => e.key === 'Enter' && handlePatternSearch()}
                />
                <button
                  className="px-2 py-1 text-xs rounded border border-border bg-muted/50 hover:bg-muted transition-colors cursor-pointer whitespace-nowrap"
                  onClick={handlePatternSearch}
                >
                  Search
                </button>
              </div>
              {patternResults.length > 0 && (
                <div className="max-h-32 overflow-y-auto text-xs space-y-0.5">
                  <p className="text-muted-foreground">{patternTotal} results</p>
                  {patternResults.map((r, i) => (
                    <div key={i} className="flex justify-between px-1 py-0.5 rounded hover:bg-muted/50">
                      <span className="text-foreground truncate">{r.model}</span>
                      <span className="text-muted-foreground ml-2 shrink-0">
                        {r.frequency_mhz > 0 ? `${r.frequency_mhz} MHz` : ''} {r.manufacturer}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
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
