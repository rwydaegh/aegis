import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import * as Sentry from '@sentry/react'
import { AnalysisEmptyState } from './AnalysisEmptyState'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  Area,
  Cell,
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
  onChartClick,
}: {
  data: { x: number; margin: number; compliant: boolean }[]
  xLabel: string
  xUnit: string
  currentX?: number
  maxCompliantX?: number | null
  onChartClick?: (xValue: number) => void
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
          onClick={onChartClick ? (state) => {
            const idx = typeof state.activeTooltipIndex === 'number' ? state.activeTooltipIndex : -1
            if (idx >= 0 && idx < data.length) {
              onChartClick(data[idx].x)
            }
          } : undefined}
          style={onChartClick ? { cursor: 'pointer' } : undefined}
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

  const hasComplianceData = stats?.compliance != null
  const canSweep = hasComplianceData && (peakSab != null && peakSab > 0 || sarWb != null)

  async function runSweep() {
    if (!canSweep) return
    setLoading(true)
    try {
      const data = await fetchPowerSweep({
        sab_4cm2: peakSab ?? undefined,
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
          Run a compute first
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
            onChartClick={(v) => setPowerDbm(parseFloat(v.toFixed(1)))}
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

  const marginDb = stats?.compliance?.margin_db
  const distanceM = stats?.distance_m
  const canSweep = marginDb != null && distanceM != null && distanceM > 0

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
          Run a compute first
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
  onCellClick,
}: {
  result: HeatmapResult
  currentFreqGhz: number
  currentPowerDbm: number
  onCellClick?: (freqGhz: number, powerDbm: number) => void
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
    const clickHint = onCellClick ? '  (click to apply)' : ''
    tip.textContent = `${freq_ghz[fi].toFixed(1)} GHz, ${power_dbm[pi].toFixed(0)} dBm: ${m > 0 ? '+' : ''}${m.toFixed(1)} dB${clickHint}`
  }, [result, n_freq, n_power, freq_ghz, power_dbm, margin_db, onCellClick])

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onCellClick) return
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mx = (e.clientX - rect.left) * (canvas.width / rect.width)
    const my = (e.clientY - rect.top) * (canvas.height / rect.height)
    const W = canvas.width, H = canvas.height
    const ml = 40, mr = 10, mt = 10, mb = 28
    const pw = (W - ml - mr) / n_freq
    const ph = (H - mt - mb) / n_power
    const fi = Math.floor((mx - ml) / pw)
    const pi = n_power - 1 - Math.floor((my - mt) / ph)
    if (fi < 0 || fi >= n_freq || pi < 0 || pi >= n_power) return
    onCellClick(freq_ghz[fi], power_dbm[pi])
  }, [onCellClick, n_freq, n_power, freq_ghz, power_dbm])

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
        onClick={handleClick}
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
  const hasComplianceData = stats?.compliance != null
  const canSweep = hasComplianceData && (peakSab != null && peakSab > 0)

  async function runHeatmap() {
    if (!canSweep) return
    setLoading(true)
    try {
      const data = await fetchComplianceHeatmap({
        sab_4cm2: peakSab ?? undefined,
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

// ---------------------------------------------------------------------------
// Exposure distribution section
// ---------------------------------------------------------------------------

function formatSab(v: number): string {
  if (v === 0) return '0'
  if (v < 0.01) return v.toExponential(1)
  if (v < 1) return v.toFixed(3)
  if (v < 100) return v.toFixed(2)
  return v.toFixed(1)
}

function ExposureDistributionSection() {
  const { stats, sabArray } = useActiveSimulation()
  const dist = stats?.distribution

  if (!dist || !sabArray || sabArray.length === 0) {
    return (
      <span className="text-[10px] text-muted-foreground/50">
        Run a compute first
      </span>
    )
  }

  const illumPct = (dist.illuminated_fraction * 100).toFixed(1)

  return (
    <div className="space-y-2">
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        Distribution of absorbed power density across the body mesh.
      </p>

      {/* Illumination coverage */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-muted-foreground">Illuminated</span>
          <span className="font-mono text-foreground">
            {illumPct}%
            <span className="text-muted-foreground ml-1">
              ({stats.n_illuminated.toLocaleString()} / {stats.n_triangles.toLocaleString()})
            </span>
          </span>
        </div>
        <div className="h-1.5 bg-muted/50 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary/70 rounded-full transition-all"
            style={{ width: `${Math.min(dist.illuminated_fraction * 100, 100)}%` }}
          />
        </div>
      </div>

      {dist.illuminated_area_cm2 != null && (
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-muted-foreground">Illuminated area</span>
          <span className="font-mono text-foreground">{dist.illuminated_area_cm2.toFixed(1)} cm&sup2;</span>
        </div>
      )}

      {/* Distribution table */}
      <div className="border border-border/40 rounded overflow-hidden">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="bg-muted/30 text-muted-foreground">
              <th className="text-left py-1 px-2 font-medium">Statistic</th>
              <th className="text-right py-1 px-2 font-medium">W/m&sup2;</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">Peak</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSab(stats.peak_sab)}</td>
            </tr>
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">P99</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSab(dist.p99)}</td>
            </tr>
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">P95</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSab(dist.p95)}</td>
            </tr>
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">Mean (all)</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSab(dist.mean)}</td>
            </tr>
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">Mean (illuminated)</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSab(dist.illuminated_mean)}</td>
            </tr>
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">Median (illuminated)</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSab(dist.illuminated_p50)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// SAB histogram section (client-side)
// ---------------------------------------------------------------------------

function computeHistogram(arr: Float32Array, nBins: number): { bins: { x0: number; x1: number; count: number; label: string }[]; maxCount: number } {
  // Only histogram positive values (exposed triangles)
  const positive: number[] = []
  for (let i = 0; i < arr.length; i++) {
    if (arr[i] > 0) positive.push(arr[i])
  }
  if (positive.length === 0) return { bins: [], maxCount: 0 }

  // Use log-scale bins for better visualization of power density distributions
  const minVal = Math.min(...positive)
  const maxVal = Math.max(...positive)

  if (minVal === maxVal) {
    return {
      bins: [{ x0: minVal * 0.9, x1: maxVal * 1.1, count: positive.length, label: formatSab(minVal) }],
      maxCount: positive.length,
    }
  }

  const logMin = Math.log10(Math.max(minVal, 1e-12))
  const logMax = Math.log10(maxVal)
  const binWidth = (logMax - logMin) / nBins

  const bins: { x0: number; x1: number; count: number; label: string }[] = []
  for (let i = 0; i < nBins; i++) {
    const x0 = Math.pow(10, logMin + i * binWidth)
    const x1 = Math.pow(10, logMin + (i + 1) * binWidth)
    bins.push({ x0, x1, count: 0, label: formatSab(x0) })
  }

  for (const v of positive) {
    let idx = Math.floor((Math.log10(v) - logMin) / binWidth)
    if (idx < 0) idx = 0
    if (idx >= nBins) idx = nBins - 1
    bins[idx].count++
  }

  const maxCount = Math.max(...bins.map(b => b.count))
  return { bins, maxCount }
}

function SabHistogramSection() {
  const { sabArray, stats } = useActiveSimulation()

  const histogram = useMemo(() => {
    if (!sabArray || sabArray.length === 0) return null
    return computeHistogram(sabArray, 24)
  }, [sabArray])

  if (!histogram || histogram.bins.length === 0 || !stats) {
    return (
      <span className="text-[10px] text-muted-foreground/50">
        Run a compute first
      </span>
    )
  }

  const limit = stats.compliance?.checks.find(c => c.label.includes('4 cm'))?.limit
  const chartData = histogram.bins.map((b, i) => ({
    idx: i,
    count: b.count,
    label: b.label,
    x0: b.x0,
    x1: b.x1,
    aboveLimit: limit != null && b.x0 >= limit,
  }))

  return (
    <div>
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        Distribution of S_ab across illuminated triangles (log-scale bins).
      </p>
      <ResponsiveContainer width="100%" height={130}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 16, left: 0 }}>
          <XAxis
            dataKey="label"
            tick={{ fontSize: 8, fill: '#888' }}
            interval={Math.max(0, Math.floor(chartData.length / 5) - 1)}
            label={{
              value: 'S_ab (W/m\u00B2)',
              position: 'bottom',
              fontSize: 9,
              fill: '#666',
              offset: 0,
            }}
          />
          <YAxis
            tick={{ fontSize: 9, fill: '#888' }}
            width={35}
            label={{
              value: 'triangles',
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
            formatter={(value) => [Number(value).toLocaleString(), 'Triangles']}
            labelFormatter={(_label, payload) => {
              const d = (payload as unknown as Array<{ payload?: { x0: number; x1: number } }>)?.[0]?.payload
              if (!d) return ''
              return `${formatSab(d.x0)} - ${formatSab(d.x1)} W/m\u00B2`
            }}
          />
          {limit != null && (
            <ReferenceLine
              x={chartData.findIndex(d => d.x0 >= limit)}
              stroke="#f87171"
              strokeDasharray="4 2"
              strokeWidth={1.5}
              label={{ value: 'limit', position: 'top', fontSize: 8, fill: '#f87171' }}
            />
          )}
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {chartData.map((entry, idx) => (
              <Cell
                key={idx}
                fill={entry.aboveLimit ? '#f87171' : '#4ade80'}
                fillOpacity={0.7}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: 'rgba(74,222,128,0.7)' }} />
          Below limit
        </span>
        {limit != null && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: 'rgba(248,113,113,0.7)' }} />
            Above limit
          </span>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export default function AnalysisPanel() {
  const [openSection, setOpenSection] = useState<string | null>('distribution')

  function toggle(key: string) {
    setOpenSection((prev) => (prev === key ? null : key))
  }

  return (
    <div>
      <AnalysisEmptyState />
      <Section
        title="Exposure distribution"
        open={openSection === 'distribution'}
        onToggle={() => toggle('distribution')}
      >
        <ExposureDistributionSection />
      </Section>
      <Section
        title="SAB histogram"
        open={openSection === 'histogram'}
        onToggle={() => toggle('histogram')}
      >
        <SabHistogramSection />
      </Section>
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
