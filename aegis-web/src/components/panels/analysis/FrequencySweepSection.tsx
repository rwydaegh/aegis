import { useState, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import { fetchFrequencySweep } from '@/api/client'
import type { FrequencySweepResult } from '@/api/client'
import { MarginChart, type PerCheckSeries } from './MarginChart'
import { btnClass, btnPrimaryClass, checkValue } from './utils'

const PER_CHECK_SERIES: PerCheckSeries[] = [
  { key: 'sab_4cm2', label: 'S_ab (4 cm²)', color: '#60a5fa' },
  { key: 'sab_1cm2', label: 'S_ab (1 cm²)', color: '#a78bfa' },
  { key: 'sar_wb', label: 'SAR_wb', color: '#fbbf24' },
  { key: 'sinc_local', label: 'S_inc (local)', color: '#34d399' },
  { key: 'sinc_whole_body', label: 'S_inc (wb)', color: '#f472b6' },
]

// ---------------------------------------------------------------------------
// Frequency sweep section
// ---------------------------------------------------------------------------

export function FrequencySweepSection() {
  const { stats } = useActiveSimulation()
  const freqGhz = useSimulationStore((s) => s.freqGhz)
  const scenario = useUIStore((s) => s.exposureScenario)

  const [result, setResult] = useState<FrequencySweepResult | null>(null)
  const [loading, setLoading] = useState(false)

  // Clear stale sweep results when underlying dosimetry stats change
  const statsRef = useRef(stats)
  if (stats !== statsRef.current) {
    statsRef.current = stats
    if (result) setResult(null)
  }

  const peakSab = stats?.peak_sab_averaged ?? stats?.peak_sab
  const sincLocal = stats?.peaks?.sinc_local
  const sab1cm2 = stats?.peaks?.sab_1cm2
  const sarWb = checkValue(stats, 'SAR_wb')
  const sincWb = checkValue(stats, 'S_inc (whole-body)')

  const hasComplianceData = stats?.compliance != null
  const canSweep = hasComplianceData && (peakSab != null && peakSab > 0 || sarWb != null)

  async function runSweep() {
    if (!canSweep) return
    setLoading(true)
    try {
      const data = await fetchFrequencySweep({
        sab_4cm2: peakSab ?? undefined,
        scenario,
        sinc_local: sincLocal,
        sab_1cm2: sab1cm2,
        sar_wb: sarWb,
        sinc_wb: sincWb,
      })
      setResult(data)
    } catch (err) {
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', 'Frequency sweep failed')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const chartData = result
    ? result.freq_ghz.map((f, i) => ({
        x: f,
        margin: result.margin_db[i],
        compliant: result.compliant[i],
        sab_4cm2: result.per_check_margin_db?.sab_4cm2?.[i] ?? null,
        sab_1cm2: result.per_check_margin_db?.sab_1cm2?.[i] ?? null,
        sar_wb: result.per_check_margin_db?.sar_wb?.[i] ?? null,
        sinc_local: result.per_check_margin_db?.sinc_local?.[i] ?? null,
        sinc_whole_body: result.per_check_margin_db?.sinc_whole_body?.[i] ?? null,
      }))
    : []

  const activeSeries = result
    ? PER_CHECK_SERIES.filter((s) =>
        chartData.some((row) => row[s.key as keyof typeof row] != null),
      )
    : []

  return (
    <div>
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        See how compliance margin changes across the frequency spectrum at
        current exposure level.
      </p>
      <button
        onClick={runSweep}
        disabled={!canSweep || loading}
        className={canSweep && !loading ? btnPrimaryClass : `${btnClass} opacity-50 cursor-not-allowed`}
      >
        {loading ? 'Sweeping...' : 'Sweep frequencies'}
      </button>
      {!canSweep && (
        <span className="text-[10px] text-muted-foreground/50 ml-2">
          Run a compute first
        </span>
      )}

      {result && (
        <MarginChart
          data={chartData}
          xLabel="Frequency"
          xUnit="GHz"
          currentX={freqGhz}
          onChartClick={(v) => useSimulationStore.getState().setFreqGhz(parseFloat(v.toFixed(1)))}
          perCheck={activeSeries}
        />
      )}
    </div>
  )
}
