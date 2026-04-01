import { useState, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { AnalysisEmptyState } from './AnalysisEmptyState'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  Area,
} from 'recharts'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import {
  fetchPowerSweep,
  fetchFrequencySweep,
} from '@/api/client'
import type {
  PowerSweepResult,
  FrequencySweepResult,
} from '@/api/client'

const btnClass =
  'text-xs px-3 py-1.5 rounded border border-border transition-colors cursor-pointer hover:bg-muted'
const btnPrimaryClass =
  'text-xs px-3 py-1.5 rounded border border-primary/40 bg-primary/15 text-primary transition-colors cursor-pointer hover:bg-primary/25'

// ---------------------------------------------------------------------------
// Collapsible section
// ---------------------------------------------------------------------------

function Section({
  title,
  open,
  onToggle,
  children,
}: {
  title: string
  open: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="border-b border-border/50 pb-2 mb-2 last:border-b-0">
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full text-xs font-medium py-1 cursor-pointer text-foreground"
      >
        <span>{title}</span>
        <span className="text-muted-foreground">{open ? '−' : '+'}</span>
      </button>
      {open && <div className="mt-1">{children}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Margin chart (shared between power sweep and frequency sweep)
// ---------------------------------------------------------------------------

function MarginChart({
  data,
  xLabel,
  xUnit,
  currentX,
  maxCompliantX,
}: {
  data: { x: number; margin: number; compliant: boolean }[]
  xLabel: string
  xUnit: string
  currentX?: number
  maxCompliantX?: number | null
}) {
  if (data.length === 0) return null

  const minMargin = Math.min(...data.map((d) => d.margin))
  const maxMargin = Math.max(...data.map((d) => d.margin))
  const yMin = Math.min(minMargin, -5)
  const yMax = Math.max(maxMargin, 5)

  return (
    <div className="mt-2">
      <ResponsiveContainer width="100%" height={140}>
        <LineChart
          data={data}
          margin={{ top: 4, right: 8, bottom: 16, left: 0 }}
        >
          <defs>
            <linearGradient id="marginFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4ade80" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#4ade80" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="x"
            type="number"
            domain={['dataMin', 'dataMax']}
            tick={{ fontSize: 9, fill: '#888' }}
            tickFormatter={(v) => v.toFixed(0)}
            label={{
              value: `${xLabel} (${xUnit})`,
              position: 'bottom',
              fontSize: 9,
              fill: '#666',
              offset: 0,
            }}
          />
          <YAxis
            domain={[yMin, yMax]}
            tick={{ fontSize: 9, fill: '#888' }}
            tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v.toFixed(0)}`}
            width={35}
            label={{
              value: 'dB',
              angle: -90,
              position: 'insideLeft',
              fontSize: 9,
              fill: '#666',
              offset: 10,
            }}
          />
          <Tooltip
            contentStyle={{
              background: 'rgba(0,0,0,0.85)',
              border: '1px solid #333',
              borderRadius: 4,
              fontSize: 11,
            }}
            formatter={(value) => {
              const v = Number(value)
              return [`${v > 0 ? '+' : ''}${v.toFixed(1)} dB`, 'Margin']
            }}
            labelFormatter={(label) => {
              const v = Number(label)
              return `${xLabel}: ${v.toFixed(1)} ${xUnit}`
            }}
          />
          <ReferenceLine y={0} stroke="#f87171" strokeDasharray="4 2" strokeWidth={1.5} />
          {currentX != null && (
            <ReferenceLine
              x={currentX}
              stroke="#93c5fd"
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{
                value: 'current',
                position: 'top',
                fontSize: 8,
                fill: '#93c5fd',
              }}
            />
          )}
          {maxCompliantX != null && (
            <ReferenceLine
              x={maxCompliantX}
              stroke="#fbbf24"
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{
                value: 'max',
                position: 'top',
                fontSize: 8,
                fill: '#fbbf24',
              }}
            />
          )}
          <Area
            type="monotone"
            dataKey="margin"
            fill="url(#marginFill)"
            stroke="none"
            baseLine={0}
          />
          <Line
            type="monotone"
            dataKey="margin"
            stroke="#4ade80"
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3, fill: '#4ade80' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Power sweep section
// ---------------------------------------------------------------------------

/** Extract a compliance check value by label from stats. */
function checkValue(stats: { compliance?: { checks: Array<{ label: string; value: number }> } | null } | null, label: string): number | undefined {
  return stats?.compliance?.checks.find(c => c.label === label)?.value
}

function PowerSweepSection() {
  const { stats } = useActiveSimulation()
  const powerDbm = useSimulationStore((s) => s.powerDbm)
  const freqGhz = useSimulationStore((s) => s.freqGhz)
  const scenario = useUIStore((s) => s.exposureScenario)
  const setPowerDbm = useSimulationStore((s) => s.setPowerDbm)

  const [result, setResult] = useState<PowerSweepResult | null>(null)
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

  const isAbove6GHz = freqGhz > 6
  const canSweep = peakSab != null && peakSab > 0 && isAbove6GHz

  async function runSweep() {
    if (!canSweep) return
    setLoading(true)
    try {
      const data = await fetchPowerSweep({
        sab_4cm2: peakSab!,
        freq_hz: freqGhz * 1e9,
        ref_power_dbm: powerDbm,
        scenario,
        sinc_local: sincLocal,
        sab_1cm2: sab1cm2,
        sar_wb: sarWb,
        sinc_wb: sincWb,
      })
      setResult(data)
    } catch (err) {
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', 'Power sweep failed')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const chartData = result
    ? result.power_dbm.map((p, i) => ({
        x: p,
        margin: result.margin_db[i],
        compliant: result.compliant[i],
      }))
    : []

  return (
    <div>
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        Find the maximum TX power that keeps all ICNIRP checks compliant.
      </p>
      <button
        onClick={runSweep}
        disabled={!canSweep || loading}
        className={canSweep && !loading ? btnPrimaryClass : `${btnClass} opacity-50 cursor-not-allowed`}
      >
        {loading ? 'Sweeping...' : 'Sweep power'}
      </button>
      {!canSweep && (
        <span className="text-[10px] text-muted-foreground/50 ml-2">
          {!isAbove6GHz ? 'Compliance sweep requires frequency > 6 GHz' : 'Run a compute first'}
        </span>
      )}

      {result && (
        <>
          <MarginChart
            data={chartData}

            xLabel="TX Power"
            xUnit="dBm"
            currentX={powerDbm}
            maxCompliantX={result.p_max_compliant_dbm}
          />
          {result.p_max_compliant_dbm != null && (
            <div className="flex items-center justify-between mt-2 text-xs">
              <span className="text-muted-foreground">
                Max compliant: <span className="text-foreground font-medium">{result.p_max_compliant_dbm.toFixed(1)} dBm</span>
              </span>
              <button
                onClick={() =>
                  setPowerDbm(
                    parseFloat(result.p_max_compliant_dbm!.toFixed(1)),
                  )
                }
                className={btnClass}
              >
                Set
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Frequency sweep section
// ---------------------------------------------------------------------------

function FrequencySweepSection() {
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

  const isAbove6GHz = freqGhz > 6
  const canSweep = peakSab != null && peakSab > 0 && isAbove6GHz

  async function runSweep() {
    if (!canSweep) return
    setLoading(true)
    try {
      const data = await fetchFrequencySweep({
        sab_4cm2: peakSab!,
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
      }))
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
          {!isAbove6GHz ? 'Compliance sweep requires frequency > 6 GHz' : 'Run a compute first'}
        </span>
      )}

      {result && (
        <MarginChart
          data={chartData}

          xLabel="Frequency"
          xUnit="GHz"
          currentX={freqGhz}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Distance sweep section (client-side 1/r^2 approximation)
// ---------------------------------------------------------------------------

function DistanceSweepSection() {
  const { stats } = useActiveSimulation()
  const freqGhz = useSimulationStore((s) => s.freqGhz)

  const isAbove6GHz = freqGhz > 6
  const marginDb = stats?.compliance?.margin_db
  const distanceM = stats?.distance_m
  const canSweep = marginDb != null && distanceM != null && distanceM > 0 && isAbove6GHz

  // Compute distance sweep data from current compliance margin
  // using far-field 1/r^2 scaling: margin(d) = margin(d0) + 20*log10(d/d0)
  const chartData = (() => {
    if (!canSweep) return []
    const d0 = distanceM!
    const margin0 = marginDb!
    // Range: 0.5m to max(5*d0, 50m), at least 100 points
    const dMax = Math.max(5 * d0, 50)
    const dMin = Math.max(0.5, d0 * 0.1)
    const n = 120
    const data: { x: number; margin: number; compliant: boolean }[] = []
    for (let i = 0; i < n; i++) {
      const d = dMin + (dMax - dMin) * (i / (n - 1))
      const margin = margin0 + 20 * Math.log10(d / d0)
      data.push({ x: parseFloat(d.toFixed(1)), margin: parseFloat(margin.toFixed(2)), compliant: margin >= 0 })
    }
    return data
  })()

  // Find minimum compliant distance (margin = 0 crossing)
  const minCompliantDist = (() => {
    if (!canSweep) return null
    const d0 = distanceM!
    const margin0 = marginDb!
    if (margin0 >= 0) {
      // Already compliant: find where margin = 0
      // margin0 + 20*log10(d/d0) = 0  =>  d = d0 * 10^(-margin0/20)
      const d = d0 * Math.pow(10, -margin0 / 20)
      return d >= 0.1 ? d : null
    }
    // Not compliant: need to move further away
    const d = d0 * Math.pow(10, -margin0 / 20)
    return d
  })()

  return (
    <div>
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        Estimate how compliance margin changes with antenna-body distance
        (far-field 1/r&#178; approximation).
      </p>
      {!canSweep && (
        <span className="text-[10px] text-muted-foreground/50">
          {!isAbove6GHz ? 'Compliance sweep requires frequency > 6 GHz' : 'Run a compute first'}
        </span>
      )}
      {canSweep && chartData.length > 0 && (
        <>
          <MarginChart
            data={chartData}
            xLabel="Distance"
            xUnit="m"
            currentX={parseFloat(distanceM!.toFixed(1))}
            maxCompliantX={minCompliantDist != null ? parseFloat(minCompliantDist.toFixed(1)) : null}
          />
          <div className="mt-2 text-xs space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">
                Current distance: <span className="text-foreground font-medium">{distanceM!.toFixed(1)} m</span>
              </span>
            </div>
            {minCompliantDist != null && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">
                  Min. compliant distance: <span className="text-foreground font-medium">{minCompliantDist.toFixed(1)} m</span>
                </span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export default function AnalysisPanel() {
  const [openSection, setOpenSection] = useState<string | null>('power')

  function toggle(key: string) {
    setOpenSection((prev) => (prev === key ? null : key))
  }

  return (
    <div>
      <AnalysisEmptyState />
      <Section
        title="Power sweep"
        open={openSection === 'power'}
        onToggle={() => toggle('power')}
      >
        <PowerSweepSection />
      </Section>
      <Section
        title="Frequency sweep"
        open={openSection === 'freq'}
        onToggle={() => toggle('freq')}
      >
        <FrequencySweepSection />
      </Section>
      <Section
        title="Distance sweep"
        open={openSection === 'distance'}
        onToggle={() => toggle('distance')}
      >
        <DistanceSweepSection />
      </Section>
    </div>
  )
}
