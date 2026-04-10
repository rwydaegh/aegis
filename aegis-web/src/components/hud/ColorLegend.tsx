import { useEffect, useRef } from 'react'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { arrayMax } from '@/lib/colormap'
import Tex from '@/components/ui/Tex'
import GradientBar from '@/components/hud/GradientBar'

/** Format a value for the legend: use scientific notation for very small/large values. */
function formatLegendValue(value: number): string {
  if (value === 0) return '0'
  const abs = Math.abs(value)
  if (abs >= 100) return value.toFixed(0)
  if (abs >= 1) return value.toFixed(1)
  if (abs >= 0.01) return value.toFixed(3)
  return value.toExponential(1)
}

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

const JET_GRADIENT_CSS =
  'linear-gradient(to bottom, rgb(128,0,0), rgb(255,0,0), rgb(255,128,0), rgb(255,255,0), rgb(128,255,128), rgb(0,255,255), rgb(0,128,255), rgb(0,0,255), rgb(0,0,128))'

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

  // Recompute smart dynamic range on every new simulation result
  const prevArrayRef = useRef<Float32Array | null>(null)
  useEffect(() => {
    if (sabArray && sabArray !== prevArrayRef.current) {
      prevArrayRef.current = sabArray
      const smart = computeSmartDynamicRange(sabArray)
      setDynamicRangeDb(smart)
    }
  }, [sabArray, setDynamicRangeDb])

  if (!stats || !config) return null

  const peakForQty = stats.peaks?.[displayQuantity] ?? stats.peak_sab
  const maxSab = (colormapLocked && colormapLockedMax != null) ? colormapLockedMax : peakForQty
  const isRatioMode = ratioMode && displayQuantity !== 'sab'

  // Find ratio limit from compliance checks
  let ratioLimit = 1.0
  if (isRatioMode && stats.compliance?.checks) {
    const limitMap: Record<string, (c: { label: string }) => boolean> = {
      sab_4cm2: (c) => c.label.includes('4 cm'),
      sab_1cm2: (c) => c.label.includes('1 cm'),
      sinc_local: (c) => c.label.includes('S_inc') && c.label.includes('local'),
      sinc_wb: (c) => c.label.includes('S_inc') && c.label.includes('whole-body'),
    }
    const finder = limitMap[displayQuantity]
    if (finder) {
      ratioLimit = (stats.compliance.checks as Array<{ label: string; limit: number }>).find(finder)?.limit ?? 20.0
    }
  }

  const maxRatio = isRatioMode && ratioLimit > 0 ? peakForQty / ratioLimit : 1.0

  // Both scales use 5 uniformly spaced ticks (top to bottom)
  const N = 5
  const ticks = Array.from({ length: N }, (_, i) => {
    const frac = i / (N - 1)
    if (isRatioMode) {
      const value = maxRatio * (1 - frac)
      return { label: value.toFixed(2), pct: frac }
    } else if (legendScale === 'linear') {
      const value = maxSab * (1 - frac)
      return { label: formatLegendValue(value), pct: frac }
    } else {
      const db = -dynamicRangeDb * frac
      return { label: `${db.toFixed(0)} dB`, pct: frac }
    }
  })

  const titleNode = (
    <>
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
    </>
  )

  const footerNode = (!isRatioMode && legendScale === 'dB') ? (
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
  ) : undefined

  return (
    <GradientBar
      gradient={JET_GRADIENT_CSS}
      ticks={ticks}
      title={titleNode}
      shimmer={isComputing}
      footer={footerNode}
    />
  )
}
