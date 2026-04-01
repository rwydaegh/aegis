import { useState, useRef, useEffect, useCallback } from 'react'
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
  fetchComplianceHeatmap,
} from '@/api/client'
import type {
  PowerSweepResult,
  FrequencySweepResult,
  HeatmapResult,
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
// Compliance heatmap (2D: frequency x power)
// ---------------------------------------------------------------------------

/** Map margin_db to a color. Green = compliant, red = exceeded, white = boundary. */
function marginColor(margin: number): [number, number, number] {
  if (margin >= 0) {
    // Compliant: green, brighter with more margin
    const t = Math.min(margin / 20, 1)
    return [30 + 40 * (1 - t), 160 + 80 * t, 60 + 40 * (1 - t)]
  }
  // Exceeded: red, deeper with larger exceedance
  const t = Math.min(-margin / 20, 1)
  return [180 + 75 * t, 50 * (1 - t), 50 * (1 - t)]
}

function HeatmapCanvas({
  result,
  currentFreqGhz,
  currentPowerDbm,
}: {
  result: HeatmapResult
  currentFreqGhz: number
  currentPowerDbm: number
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const { n_freq, n_power, freq_ghz, power_dbm, margin_db } = result

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = canvas.width
    const H = canvas.height
    const ml = 40, mr = 10, mt = 10, mb = 28
    const pw = (W - ml - mr) / n_freq
    const ph = (H - mt - mb) / n_power

    ctx.clearRect(0, 0, W, H)

    // Draw heatmap cells
    for (let pi = 0; pi < n_power; pi++) {
      const row = margin_db[pi]
      for (let fi = 0; fi < n_freq; fi++) {
        const [r, g, b] = marginColor(row[fi])
        ctx.fillStyle = `rgb(${r},${g},${b})`
        // Y axis: power increases upward, so flip
        ctx.fillRect(ml + fi * pw, mt + (n_power - 1 - pi) * ph, Math.ceil(pw), Math.ceil(ph))
      }
    }

    // Draw compliance boundary (margin = 0 line)
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1.5
    ctx.beginPath()
    let started = false
    for (let fi = 0; fi < n_freq; fi++) {
      const pMaxDbm = result.p_max_dbm_per_freq[fi]
      if (!Number.isFinite(pMaxDbm)) continue
      const pMin = power_dbm[0]
      const pMax = power_dbm[n_power - 1]
      const yFrac = 1 - (pMaxDbm - pMin) / (pMax - pMin)
      if (yFrac < 0 || yFrac > 1) continue
      const x = ml + (fi + 0.5) * pw
      const y = mt + yFrac * (H - mt - mb)
      if (!started) { ctx.moveTo(x, y); started = true }
      else ctx.lineTo(x, y)
    }
    ctx.stroke()

    // Draw crosshairs for current position
    const fMin = freq_ghz[0], fMax = freq_ghz[n_freq - 1]
    const pMin = power_dbm[0], pMax = power_dbm[n_power - 1]
    const cx = ml + ((currentFreqGhz - fMin) / (fMax - fMin)) * (W - ml - mr)
    const cy = mt + (1 - (currentPowerDbm - pMin) / (pMax - pMin)) * (H - mt - mb)

    if (cx >= ml && cx <= W - mr && cy >= mt && cy <= H - mb) {
      ctx.strokeStyle = 'rgba(147,197,253,0.7)'
      ctx.lineWidth = 1
      ctx.setLineDash([3, 3])
      ctx.beginPath(); ctx.moveTo(cx, mt); ctx.lineTo(cx, H - mb); ctx.stroke()
      ctx.beginPath(); ctx.moveTo(ml, cy); ctx.lineTo(W - mr, cy); ctx.stroke()
      ctx.setLineDash([])
      ctx.fillStyle = '#93c5fd'
      ctx.beginPath(); ctx.arc(cx, cy, 3, 0, Math.PI * 2); ctx.fill()
    }

    // Axes
    ctx.fillStyle = '#888'
    ctx.font = '9px monospace'
    ctx.textAlign = 'center'
    // X axis: frequency labels
    const xTicks = 5
    for (let i = 0; i <= xTicks; i++) {
      const fi = Math.round((i / xTicks) * (n_freq - 1))
      const x = ml + (fi + 0.5) * pw
      ctx.fillText(freq_ghz[fi].toFixed(0), x, H - 4)
    }
    ctx.fillText('GHz', W - mr - 8, H - 4)
    // Y axis: power labels
    ctx.textAlign = 'right'
    const yTicks = 4
    for (let i = 0; i <= yTicks; i++) {
      const pi = Math.round((i / yTicks) * (n_power - 1))
      const y = mt + (n_power - 1 - pi) * ph + ph / 2
      ctx.fillText(power_dbm[pi].toFixed(0), ml - 4, y + 3)
    }
    ctx.save()
    ctx.translate(8, mt + (H - mt - mb) / 2)
    ctx.rotate(-Math.PI / 2)
    ctx.textAlign = 'center'
    ctx.fillText('dBm', 0, 0)
    ctx.restore()
  }, [result, n_freq, n_power, freq_ghz, power_dbm, margin_db, currentFreqGhz, currentPowerDbm])

  useEffect(() => { draw() }, [draw])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    const tip = tooltipRef.current
    if (!canvas || !tip) return
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const W = canvas.width, H = canvas.height
    const ml = 40, mr = 10, mt = 10, mb = 28
    const pw = (W - ml - mr) / n_freq
    const ph = (H - mt - mb) / n_power
    const fi = Math.floor((mx - ml) / pw)
    const pi = n_power - 1 - Math.floor((my - mt) / ph)
    if (fi < 0 || fi >= n_freq || pi < 0 || pi >= n_power) {
      tip.style.display = 'none'
      return
    }
    const m = margin_db[pi][fi]
    tip.style.display = 'block'
    tip.style.left = `${mx + 12}px`
    tip.style.top = `${my - 10}px`
    tip.textContent = `${freq_ghz[fi].toFixed(1)} GHz, ${power_dbm[pi].toFixed(0)} dBm: ${m > 0 ? '+' : ''}${m.toFixed(1)} dB`
  }, [result, n_freq, n_power, freq_ghz, power_dbm, margin_db])

  return (
    <div className="relative mt-2">
      <canvas
        ref={canvasRef}
        width={280}
        height={180}
        className="w-full rounded border border-border/30 cursor-crosshair"
        style={{ imageRendering: 'pixelated' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => { if (tooltipRef.current) tooltipRef.current.style.display = 'none' }}
      />
      <div
        ref={tooltipRef}
        className="absolute hidden bg-black/85 border border-border/50 rounded px-2 py-1 text-[10px] font-mono text-foreground/90 pointer-events-none whitespace-nowrap z-10"
      />
    </div>
  )
}

function ComplianceHeatmapSection() {
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
  const isAbove6GHz = freqGhz > 6
  const canSweep = peakSab != null && peakSab > 0 && isAbove6GHz

  async function runHeatmap() {
    if (!canSweep) return
    setLoading(true)
    try {
      const data = await fetchComplianceHeatmap({
        sab_4cm2: peakSab!,
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
        2D map showing compliant (green) and non-compliant (red) regions across
        frequency and TX power. White line marks the compliance boundary.
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
          {!isAbove6GHz ? 'Requires frequency > 6 GHz' : 'Run a compute first'}
        </span>
      )}
      {result && (
        <>
          <HeatmapCanvas result={result} currentFreqGhz={freqGhz} currentPowerDbm={powerDbm} />
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
      <Section
        title="Compliance heatmap"
        open={openSection === 'heatmap'}
        onToggle={() => toggle('heatmap')}
      >
        <ComplianceHeatmapSection />
      </Section>
    </div>
  )
}
