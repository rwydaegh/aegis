import { useEffect, useRef } from 'react'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { arrayMax } from '@/lib/colormap'
import Tex from '@/components/ui/Tex'

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
  const max = arrayMax(sabArray)
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

function legendLabel(qty: string, ratio: boolean, scale: string): string {
  if (ratio && qty !== 'sab') return '\\text{Ratio to limit}'
  const labels: Record<string, string> = {
    sab: 'S_\\text{ab}',
    sab_4cm2: 'S_\\text{ab}\\;(4\\,\\text{cm}^2)',
    sab_1cm2: 'S_\\text{ab}\\;(1\\,\\text{cm}^2)',
    sinc_local: 'S_\\text{inc}\\;\\text{local}',
  }
  const base = labels[qty] ?? 'S_\\text{ab}'
  const unit = scale === 'linear' ? '\\;(\\text{W/m}^2)' : '\\;(\\text{dB re peak})'
  return base + unit
}

export default function ColorLegend() {
  const stats = useSimulationStore(s => s.stats)
  const config = useSceneStore(s => s.viewerConfig)
  const sabArray = useSimulationStore(s => s.sabArray)
  const legendScale = useUIStore(s => s.legendScale)
  const toggleLegendScale = useUIStore(s => s.toggleLegendScale)
  const dynamicRangeDb = useUIStore(s => s.dynamicRangeDb)
  const setDynamicRangeDb = useUIStore(s => s.setDynamicRangeDb)
  const colormapLocked = useUIStore(s => s.colormapLocked)
  const colormapLockedMax = useUIStore(s => s.colormapLockedMax)
  const toggleColormapLock = useUIStore(s => s.toggleColormapLock)
  const displayQuantity = useSimulationStore(s => s.displayQuantity)
  const ratioMode = useUIStore(s => s.ratioMode)
  const isComputing = useUIStore(s => s.isComputing)

  // Compute smart default when sabArray first arrives
  const hasAutoSet = useRef(false)
  useEffect(() => {
    if (sabArray && !hasAutoSet.current) {
      hasAutoSet.current = true
      const smart = computeSmartDynamicRange(sabArray)
      setDynamicRangeDb(smart)
    }
  }, [sabArray, setDynamicRangeDb])

  if (!stats || !config) return null

  const peakForQty = stats.peaks?.[displayQuantity] ?? stats.peak_sab
  const maxSab = (colormapLocked && colormapLockedMax != null) ? colormapLockedMax : peakForQty
  // Jet colormap gradient: red (top/max) -> yellow -> green -> cyan -> blue (bottom/min)
  const gradientCss =
    'linear-gradient(to bottom, rgb(128,0,0), rgb(255,0,0), rgb(255,128,0), rgb(255,255,0), rgb(128,255,128), rgb(0,255,255), rgb(0,128,255), rgb(0,0,255), rgb(0,0,128))'

  const isRatioMode = ratioMode && displayQuantity !== 'sab'

  // Find ratio limit from compliance checks
  let ratioLimit = 1.0
  if (isRatioMode && stats.compliance?.checks) {
    const limitMap: Record<string, (c: { label: string }) => boolean> = {
      sab_4cm2: (c) => c.label.includes('4 cm'),
      sab_1cm2: (c) => c.label.includes('1 cm'),
      sinc_local: (c) => c.label.includes('S_inc') && c.label.includes('local'),
    }
    const finder = limitMap[displayQuantity]
    if (finder) {
      ratioLimit = (stats.compliance.checks as Array<{ label: string; limit: number }>).find(finder)?.limit ?? 20.0
    }
  }

  // Compute max ratio for the legend
  const maxRatio = isRatioMode && ratioLimit > 0 ? peakForQty / ratioLimit : 1.0

  // Both scales use 5 uniformly spaced ticks (top to bottom)
  const N = 5
  type Tick = { label: string; pct: number }
  const ticks: Tick[] = []

  for (let i = 0; i < N; i++) {
    const frac = i / (N - 1) // 0 = top (max), 1 = bottom (min)
    if (isRatioMode) {
      const value = maxRatio * (1 - frac)
      ticks.push({ label: value.toFixed(2), pct: frac })
    } else if (legendScale === 'linear') {
      const value = maxSab * (1 - frac)
      ticks.push({ label: formatLegendValue(value), pct: frac })
    } else {
      const db = -dynamicRangeDb * frac
      ticks.push({ label: `${db.toFixed(0)} dB`, pct: frac })
    }
  }

  return (
    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-auto">
      <div className={`bg-card/80 backdrop-blur-md rounded-lg border border-border px-3 py-2.5 ${isComputing ? 'shimmer-panel' : ''}`}>
        {/* Title, lock, and scale toggle */}
        <div className="flex items-center justify-between gap-1.5 mb-2">
          <span className="text-xs font-medium text-foreground">
            <Tex math={legendLabel(displayQuantity, ratioMode, legendScale)} />
          </span>
          {!isRatioMode && (
            <div className="flex items-center gap-1">
              <button
                onClick={toggleColormapLock}
                className={`text-[11px] px-1.5 py-0.5 rounded border transition-colors cursor-pointer ${
                  colormapLocked
                    ? 'border-primary/40 bg-primary/15 text-primary'
                    : 'border-border bg-muted/50 text-foreground hover:bg-muted'
                }`}
                title={colormapLocked ? 'Unlock colormap (auto-normalize)' : 'Lock colormap to current max'}
              >
                {colormapLocked ? '\u{1F512}' : '\u{1F513}'}
              </button>
              <button
                onClick={toggleLegendScale}
                className="text-[11px] px-2 py-0.5 rounded border border-border bg-muted/50 text-foreground hover:bg-muted transition-colors cursor-pointer"
                title={legendScale === 'linear' ? 'Switch to dB scale' : 'Switch to linear scale'}
              >
                {legendScale === 'linear' ? 'dB' : 'Lin'}
              </button>
            </div>
          )}
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

        {/* dB floor input (only in dB mode and not ratio mode) */}
        {!isRatioMode && legendScale === 'dB' && (
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
