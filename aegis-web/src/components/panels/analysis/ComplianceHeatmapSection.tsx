import { useState, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import { fetchComplianceHeatmap } from '@/api/client'
import type { HeatmapResult } from '@/api/client'
import { HeatmapCanvas } from './HeatmapCanvas'
import { btnClass, btnPrimaryClass } from './utils'

// ---------------------------------------------------------------------------
// Compliance heatmap section
// ---------------------------------------------------------------------------

export function ComplianceHeatmapSection() {
  const { stats } = useActiveSimulation()
  const freqGhz = useSimulationStore((s) => s.freqGhz)
  const powerDbm = useSimulationStore((s) => s.powerDbm)
  const scenario = useUIStore((s) => s.exposureScenario)

  const [result, setResult] = useState<HeatmapResult | null>(null)
  const [loading, setLoading] = useState(false)

  const statsRef = useRef(stats)
  if (stats !== statsRef.current) {
    statsRef.current = stats
    if (result) setResult(null)
  }

  const peakSab = stats?.peak_sab_averaged ?? stats?.peak_sab
  const sincLocal = stats?.peaks?.sinc_local
  const sab1cm2 = stats?.peaks?.sab_1cm2
  const hasComplianceData = stats?.compliance != null
  const canSweep = hasComplianceData && (peakSab != null && peakSab > 0 || sab1cm2 != null && sab1cm2 > 0)

  async function runHeatmap() {
    if (!canSweep) return
    setLoading(true)
    try {
      const data = await fetchComplianceHeatmap({
        sab_4cm2: peakSab ?? undefined,
        sab_1cm2: sab1cm2,
        freq_hz: freqGhz * 1e9,
        ref_power_dbm: powerDbm,
        scenario,
        sinc_local: sincLocal,
      })
      setResult(data)
    } catch (err) {
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', 'Compliance heatmap failed')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        2D map of compliance margin across frequency and TX power. Click any cell
        to jump to that operating point. White line marks the compliance boundary.
      </p>
      <button
        onClick={runHeatmap}
        disabled={!canSweep || loading}
        className={canSweep && !loading ? btnPrimaryClass : `${btnClass} opacity-50 cursor-not-allowed`}
      >
        {loading ? 'Computing...' : 'Generate heatmap'}
      </button>
      {!canSweep && (
        <span className="text-[10px] text-muted-foreground/50 ml-2">
          Run a compute first
        </span>
      )}
      {result && (
        <>
          <HeatmapCanvas
            result={result}
            currentFreqGhz={freqGhz}
            currentPowerDbm={powerDbm}
            onCellClick={(f, p) => {
              useSimulationStore.getState().setFreqGhz(f)
              useSimulationStore.getState().setPowerDbm(parseFloat(p.toFixed(1)))
            }}
          />
          <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: 'rgb(70,240,100)' }} />
              Compliant
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: 'rgb(255,0,0)' }} />
              Exceeded
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-2.5 h-2.5 border border-white/50 rounded-sm" style={{ background: 'transparent' }} />
              Boundary
            </span>
          </div>
        </>
      )}
    </div>
  )
}
