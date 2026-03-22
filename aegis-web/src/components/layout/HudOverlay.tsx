import { useState, useEffect, useRef } from 'react'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { fetchSystemInfo } from '@/api/client'
import { formatSab, formatPower, formatDistance } from '@/lib/format'
import { PHANTOM_META } from '@/components/panels/PhantomPanel'

// ---------------------------------------------------------------------------
// Server info hook
// ---------------------------------------------------------------------------

interface ServerInfo {
  hostname: string
  cpuPct: number | null
  cpuCores: number | null
  ramPct: number | null
  ramTotalGb: number | null
  gpuPct: number | null
  gpuName: string | null
}

function shortenGpuName(name: string): string {
  // "NVIDIA RTX A4000" -> "A4000", "NVIDIA GeForce RTX 4090" -> "4090"
  return name
    .replace(/NVIDIA\s*/i, '')
    .replace(/GeForce\s*/i, '')
    .replace(/RTX\s*/i, '')
    .replace(/Quadro\s*/i, '')
    .trim()
}

function useServerInfo(): ServerInfo | null {
  const [info, setInfo] = useState<ServerInfo | null>(null)

  useEffect(() => {
    const poll = () => {
      fetchSystemInfo()
        .then(data => {
          const d = data as any
          setInfo({
            hostname: data.hostname,
            cpuPct: d.cpu_pct ?? null,
            cpuCores: d.cpu_cores ?? null,
            ramPct: d.ram_pct ?? null,
            ramTotalGb: d.ram_total_gb ?? null,
            gpuPct: d.gpu?.utilization_pct ?? null,
            gpuName: d.gpu?.name ? shortenGpuName(d.gpu.name) : null,
          })
        })
        .catch(() => {})
    }
    poll()
    const interval = setInterval(poll, 5000)
    return () => clearInterval(interval)
  }, [])

  return info
}

// ---------------------------------------------------------------------------
// Stats card
// ---------------------------------------------------------------------------

function StatsCard() {
  const { stats } = useSimulationStore()
  const bodyName = useSceneStore(s => s.bodyName)
  const meta = PHANTOM_META[bodyName.toLowerCase()]
  const massKg = meta?.mass_kg

  // SAR = P_abs (W) / mass (kg)
  const sarValue = (stats && massKg) ? (stats.p_abs_mw / 1000) / massKg : null
  const formatSar = (sar: number) => {
    if (sar >= 0.01) return `${sar.toFixed(3)} W/kg`
    return `${sar.toExponential(1)} W/kg`
  }

  const rows: Array<{ label: string; value: string; highlight?: 'pass' | 'fail' }> = [
    {
      label: 'SAR_wb',
      value: sarValue != null ? formatSar(sarValue) : '--',
    },
    {
      label: 'P_abs',
      value: stats ? formatPower(stats.p_abs_mw) : '--',
    },
    {
      label: 'Peak S_ab',
      value: stats ? formatSab(stats.peak_sab) : '--',
    },
    {
      label: 'Distance',
      value: stats ? formatDistance(stats.distance_m) : '--',
    },
    {
      label: 'Illuminated',
      value: stats ? `${stats.n_illuminated} / ${stats.n_triangles}` : '--',
    },
    {
      label: 'Compliance',
      value: stats ? (stats.compliant ? 'PASS' : 'FAIL') : '--',
      highlight: stats ? (stats.compliant ? 'pass' : 'fail') : undefined,
    },
  ]

  return (
    <div className="bg-card/80 backdrop-blur-md rounded-lg border border-border p-3 min-w-[180px]">
      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
        Dosimetry
      </p>
      <dl className="space-y-1">
        {rows.map(({ label, value, highlight }) => (
          <div key={label} className="flex items-baseline justify-between gap-3">
            <dt className="text-xs text-muted-foreground shrink-0">{label}</dt>
            <dd
              className={
                'text-xs font-mono tabular-nums font-medium ' +
                (highlight === 'pass'
                  ? 'text-success'
                  : highlight === 'fail'
                    ? 'text-destructive'
                    : 'text-foreground')
              }
            >
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Status bar (computing spinner + elapsed timer)
// ---------------------------------------------------------------------------

function StatusBar() {
  const { isComputing, statusMessage, setComputeElapsed } = useUIStore()
  const [elapsed, setElapsed] = useState(0)
  const startRef = useRef<number | null>(null)

  useEffect(() => {
    if (isComputing) {
      startRef.current = Date.now()
      setElapsed(0)
      setComputeElapsed(0)
      const interval = setInterval(() => {
        const ms = Date.now() - (startRef.current ?? Date.now())
        setElapsed(ms)
        setComputeElapsed(ms)
      }, 100)
      return () => clearInterval(interval)
    } else {
      startRef.current = null
    }
  }, [isComputing, setComputeElapsed])

  if (!isComputing && !statusMessage) return null

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2
      bg-card/90 backdrop-blur-md rounded-full border border-border px-4 py-2">
      {isComputing && (
        <>
          <div className="w-3 h-3 border-2 border-muted border-t-primary rounded-full animate-spin" />
          <span className="text-xs text-muted-foreground">
            Computing{elapsed > 0 ? ` (${(elapsed / 1000).toFixed(1)}s)` : '...'}
          </span>
        </>
      )}
      {!isComputing && statusMessage && (
        <span className="text-xs text-muted-foreground">{statusMessage}</span>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Color legend
// ---------------------------------------------------------------------------

/** Format a value for the legend: use scientific notation for very small/large values. */
function formatLegendValue(value: number): string {
  if (value === 0) return '0'
  const abs = Math.abs(value)
  if (abs >= 100) return value.toFixed(0)
  if (abs >= 1) return value.toFixed(1)
  if (abs >= 0.01) return value.toFixed(3)
  return value.toExponential(1)
}

const BAR_HEIGHT = 240
const BAR_WIDTH = 16

/**
 * Compute a smart default dynamic range from the S_ab distribution.
 * Finds the dB level at which ~95% of non-zero faces fall within range,
 * then rounds to the nearest 5 dB. Clamped to [10, 60].
 */
function computeSmartDynamicRange(sabArray: Float32Array): number {
  const max = Math.max(...Array.from(sabArray))
  if (max <= 0) return 30

  // Collect dB values for non-zero faces
  const dbValues: number[] = []
  for (let i = 0; i < sabArray.length; i++) {
    if (sabArray[i] > 0) {
      dbValues.push(10 * Math.log10(sabArray[i] / max))
    }
  }
  if (dbValues.length === 0) return 30

  dbValues.sort((a, b) => a - b)

  // 5th percentile: the dB level below which only 5% of faces fall
  const p5idx = Math.floor(dbValues.length * 0.05)
  const p5 = Math.abs(dbValues[p5idx])

  // Round up to nearest 5 dB, clamp to [10, 60]
  const rounded = Math.ceil(p5 / 5) * 5
  return Math.max(10, Math.min(60, rounded))
}

function ColorLegend() {
  const stats = useSimulationStore(s => s.stats)
  const config = useSceneStore(s => s.viewerConfig)
  const sabArray = useSimulationStore(s => s.sabArray)
  const legendScale = useUIStore(s => s.legendScale)
  const toggleLegendScale = useUIStore(s => s.toggleLegendScale)
  const dynamicRangeDb = useUIStore(s => s.dynamicRangeDb)
  const setDynamicRangeDb = useUIStore(s => s.setDynamicRangeDb)

  // Compute smart default when sabArray first arrives
  const hasAutoSet = useRef(false)
  useEffect(() => {
    if (sabArray && !hasAutoSet.current) {
      hasAutoSet.current = true
      const smart = computeSmartDynamicRange(sabArray)
      setDynamicRangeDb(smart)
    }
  }, [sabArray, setDynamicRangeDb])

  if (!sabArray || !stats || !config) return null

  const maxSab = stats.peak_sab
  // Jet colormap gradient: red (top/max) -> yellow -> green -> cyan -> blue (bottom/min)
  const gradientCss =
    'linear-gradient(to bottom, rgb(128,0,0), rgb(255,0,0), rgb(255,128,0), rgb(255,255,0), rgb(128,255,128), rgb(0,255,255), rgb(0,128,255), rgb(0,0,255), rgb(0,0,128))'

  // Both scales use 5 uniformly spaced ticks (top to bottom)
  const N = 5
  type Tick = { label: string; pct: number }
  const ticks: Tick[] = []

  for (let i = 0; i < N; i++) {
    const frac = i / (N - 1) // 0 = top (max), 1 = bottom (min)
    if (legendScale === 'linear') {
      const value = maxSab * (1 - frac)
      ticks.push({ label: formatLegendValue(value), pct: frac })
    } else {
      const db = -dynamicRangeDb * frac
      ticks.push({ label: `${db.toFixed(0)} dB`, pct: frac })
    }
  }

  return (
    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-auto">
      <div className="bg-card/80 backdrop-blur-md rounded-lg border border-border px-3 py-2.5">
        {/* Title and scale toggle */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-medium text-foreground">
            S<sub>ab</sub>{legendScale === 'linear' ? ' (W/m\u00b2)' : ' (dB re peak)'}
          </span>
          <button
            onClick={toggleLegendScale}
            className="text-[11px] px-2 py-0.5 rounded border border-border bg-muted/50 text-foreground hover:bg-muted transition-colors cursor-pointer"
            title={legendScale === 'linear' ? 'Switch to dB scale' : 'Switch to linear scale'}
          >
            {legendScale === 'linear' ? 'dB' : 'Lin'}
          </button>
        </div>

        {/* Gradient bar with tick labels side by side */}
        <div className="flex gap-2">
          {/* Labels column */}
          <div className="relative" style={{ height: BAR_HEIGHT, width: 60 }}>
            {ticks.map(({ label, pct }, i) => (
              <span
                key={i}
                className="absolute right-0 text-xs font-mono tabular-nums text-foreground whitespace-nowrap"
                style={{ top: pct * BAR_HEIGHT - 7 }}
              >
                {label}
              </span>
            ))}
          </div>

          {/* Tick marks + gradient bar */}
          <div className="relative" style={{ height: BAR_HEIGHT }}>
            <div
              className="rounded-sm border border-border/60"
              style={{ background: gradientCss, height: BAR_HEIGHT, width: BAR_WIDTH }}
            />
            {ticks.map(({ pct }, i) => (
              <div
                key={i}
                className="absolute bg-foreground/40"
                style={{ top: pct * BAR_HEIGHT, left: -4, width: 4, height: 1 }}
              />
            ))}
          </div>
        </div>

        {/* dB floor input (only in dB mode) */}
        {legendScale === 'dB' && (
          <div className="flex items-center gap-1.5 mt-2">
            <span className="text-[10px] text-muted-foreground">Floor</span>
            <input
              type="number"
              className="w-12 bg-background border border-border rounded px-1 py-0.5 text-[11px] font-mono text-foreground text-center"
              value={-dynamicRangeDb}
              step={5}
              max={-5}
              min={-80}
              onChange={e => {
                const v = Number(e.target.value)
                if (v < 0 && v >= -80) setDynamicRangeDb(-v)
              }}
            />
            <span className="text-[10px] text-muted-foreground">dB</span>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Server info badge
// ---------------------------------------------------------------------------

function ServerInfoBadge() {
  const info = useServerInfo()
  if (!info) return null

  const items: Array<{ label: string; pct: number; spec: string }> = []

  if (info.cpuPct != null) {
    const spec = info.cpuCores ? `${info.cpuCores} cores` : ''
    items.push({ label: 'CPU', pct: info.cpuPct, spec })
  }
  if (info.ramPct != null) {
    const spec = info.ramTotalGb ? `${info.ramTotalGb} GB` : ''
    items.push({ label: 'RAM', pct: info.ramPct, spec })
  }
  if (info.gpuPct != null) {
    items.push({ label: 'GPU', pct: info.gpuPct, spec: info.gpuName ?? '' })
  }

  return (
    <div className="absolute bottom-3 right-3 pointer-events-none">
      <div className="flex items-center gap-3">
        {items.map(({ label, pct, spec }) => (
          <span key={label} className="text-[10px] text-muted-foreground/70 font-mono select-none">
            {label} {pct}%{spec && ` (${spec})`}
          </span>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Root overlay
// ---------------------------------------------------------------------------

export default function HudOverlay() {
  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      {/* Stats card - top right */}
      <div className="absolute top-3 right-3 pointer-events-auto">
        <StatsCard />
      </div>

      {/* Color legend - right edge, vertically centered */}
      <ColorLegend />

      {/* Status bar - bottom center */}
      <div className="pointer-events-auto">
        <StatusBar />
      </div>

      {/* Server info - bottom right */}
      <ServerInfoBadge />
    </div>
  )
}
