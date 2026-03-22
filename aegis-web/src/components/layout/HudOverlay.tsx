import { useState, useEffect, useRef } from 'react'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { fetchSystemInfo } from '@/api/client'
import { formatSab, formatPower, formatDistance } from '@/lib/format'

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

  const rows: Array<{ label: string; value: string; highlight?: 'pass' | 'fail' }> = [
    {
      label: 'P_abs',
      value: stats ? formatPower(stats.p_abs_mw) : '--',
    },
    {
      label: 'Peak S_ab',
      value: stats ? formatSab(stats.peak_sab) : '--',
    },
    {
      label: 'S_inc',
      value: stats ? formatSab(stats.S_inc) : '--',
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

function ColorLegend() {
  const stats = useSimulationStore(s => s.stats)
  const config = useSceneStore(s => s.viewerConfig)
  const sabArray = useSimulationStore(s => s.sabArray)
  const legendScale = useUIStore(s => s.legendScale)
  const toggleLegendScale = useUIStore(s => s.toggleLegendScale)

  if (!sabArray || !stats || !config) return null

  const maxSab = stats.peak_sab
  const dynamicRangeDb = (config.colormap as any).dynamic_range_db ?? 40
  const gradientCss =
    config.colormap.legend?.gradient_css ??
    'linear-gradient(to bottom, rgb(252,255,164), rgb(249,142,9), rgb(188,55,84), rgb(87,16,110), rgb(0,4,18))'

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
      // Uniform in colormap space => uniform dB ticks
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
