import { useCallback, useEffect, useRef, useState } from 'react'
import * as Sentry from '@sentry/react'
import { useBaseStationsStore } from '@/stores/basestations'
import { loadBasestations } from '@/api/basestations'
import { useBaseStationsDosimetry } from '@/hooks/useBaseStationsDosimetry'
import { useNotificationStore } from '@/stores/notifications'
import AntennaDetailPanel from './AntennaDetailPanel'

export default function BaseStationsPanel() {
  const [location, setLocation] = useState('Brussels, Belgium')
  const [radius, setRadius] = useState(500)
  const [autoLoad, setAutoLoad] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const basestations = useBaseStationsStore(s => s.basestations)
  const isLoading = useBaseStationsStore(s => s.isLoading)
  const isComputing = useBaseStationsStore(s => s.isComputing)
  const operators = useBaseStationsStore(s => s.operators)
  const technologies = useBaseStationsStore(s => s.technologies)
  const frequencyBands = useBaseStationsStore(s => s.frequencyBands)
  const enabledOperators = useBaseStationsStore(s => s.enabledOperators)
  const enabledTechnologies = useBaseStationsStore(s => s.enabledTechnologies)
  const enabledFrequencyBands = useBaseStationsStore(s => s.enabledFrequencyBands)
  const activeCount = useBaseStationsStore(s => s.activeCount)
  const toggleOperator = useBaseStationsStore(s => s.toggleOperator)
  const toggleTechnology = useBaseStationsStore(s => s.toggleTechnology)
  const toggleFrequencyBand = useBaseStationsStore(s => s.toggleFrequencyBand)
  const setBasestations = useBaseStationsStore(s => s.setBasestations)
  const setLoading = useBaseStationsStore(s => s.setLoading)
  const clear = useBaseStationsStore(s => s.clear)

  const showCoverage = useBaseStationsStore(s => s.showCoverage)
  const setShowCoverage = useBaseStationsStore(s => s.setShowCoverage)
  const setCoverageUrl = useBaseStationsStore(s => s.setCoverageUrl)

  const computeExposure = useBaseStationsDosimetry()

  const fetchCoverage = useCallback(async () => {
    if (basestations.length === 0) return
    const bs = basestations[0]
    try {
      const resp = await fetch('/api/environment/coverage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stations: [{
            lat: bs.latitude,
            lon: bs.longitude,
            alt: bs.height_m,
            freq_mhz: bs.freq_mhz,
            power_w: Math.pow(10, (bs.eirp_dbm - bs.gain_dbi) / 10) / 1000,
            gain_dbi: bs.gain_dbi,
            azimuth: bs.azimuth_deg,
            tilt: bs.total_tilt_deg,
            hbw: bs.horizontal_beamwidth_deg,
            vbw: bs.vertical_beamwidth_deg,
          }],
          radius_km: 1,
        }),
      })
      if (resp.ok) {
        const blob = await resp.blob()
        setCoverageUrl(URL.createObjectURL(blob))
      }
    } catch {
      // Coverage fetch failed silently -- not critical
    }
  }, [basestations, setCoverageUrl])

  const handleCoverageToggle = useCallback((checked: boolean) => {
    setShowCoverage(checked)
    if (checked && basestations.length > 0) {
      void fetchCoverage()
    }
  }, [setShowCoverage, basestations.length, fetchCoverage])

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

          {frequencyBands.length > 0 && (
            <>
              <label className={labelClass}>Frequency bands</label>
              <div className="flex flex-col gap-1 pl-0.5">
                {frequencyBands.map(band => (
                  <label key={band} className="flex items-center gap-2 text-xs cursor-pointer select-none">
                    <input
                      type="checkbox"
                      className="rounded border-border accent-primary h-3.5 w-3.5"
                      checked={enabledFrequencyBands.has(band)}
                      onChange={() => toggleFrequencyBand(band)}
                    />
                    <span className="text-foreground">{band}</span>
                  </label>
                ))}
              </div>
            </>
          )}

          <div className="mt-3 flex items-center gap-2 text-[10px] text-muted-foreground">
            <span className="w-2 h-2 rounded-full bg-[#22c55e] inline-block" /> Gov
            <span className="w-2 h-2 rounded-full bg-[#eab308] inline-block" /> Mixed
            <span className="w-2 h-2 rounded-full bg-[#f97316] inline-block" /> Est.
            <span className="w-2 h-2 rounded-full bg-[#ef4444] inline-block" /> Low
          </div>

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

          <label className="flex items-center gap-2 mt-3 text-xs cursor-pointer select-none">
            <input
              type="checkbox"
              className="rounded border-border accent-primary h-3.5 w-3.5"
              checked={showCoverage}
              onChange={e => handleCoverageToggle(e.target.checked)}
            />
            <span className="text-foreground">Show coverage map (CloudRF)</span>
          </label>

          <AntennaDetailPanel />
        </>
      )}
    </div>
  )
}
