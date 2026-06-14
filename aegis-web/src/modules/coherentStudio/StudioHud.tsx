import { useMemo } from 'react'
import GradientBar, { type GradientBarTick } from '@/components/hud/GradientBar'
import ProvenanceDot from '@/components/panels/ProvenanceDot'
import { useStudioStore } from './store'
import { colormapRgb, resolveSliceDisplay } from './scene/studioHelpers'
import { frameProvenance } from './panels/controls'

const CARD = {
  background: 'rgba(13, 13, 18, 0.85)',
  border: '1px solid #1e1e26',
  borderRadius: 8,
  color: '#ddd',
} as const

function fmt(value: number | null | undefined, unit = ''): string {
  if (value == null || !isFinite(value)) return '--'
  const a = Math.abs(value)
  if (a !== 0 && (a < 1e-2 || a >= 1e4)) return `${value.toExponential(2)}${unit}`
  return `${value.toPrecision(3)}${unit}`
}

// CSS gradient sampled from the active colormap, high value at the top to match
// the GradientBar tick layout (pct 0 = top = vmax).
function colormapGradient(name: string): string {
  const N = 8
  const stops: string[] = []
  for (let i = 0; i <= N; i++) {
    const pct = i / N
    const t = 1 - pct // top (pct 0) is the colormap max
    const [r, g, b] = colormapRgb(name, t)
    stops.push(`rgb(${r},${g},${b}) ${(pct * 100).toFixed(0)}%`)
  }
  return `linear-gradient(to bottom, ${stops.join(', ')})`
}

function buildTicks(vmin: number, vmax: number, logMode: boolean): GradientBarTick[] {
  const N = 5
  return Array.from({ length: N }, (_, i) => {
    const frac = i / (N - 1) // 0 = top = vmax
    let value: number
    if (logMode && vmin > 0 && vmax > 0) {
      const lo = Math.log10(vmin)
      const hi = Math.log10(vmax)
      value = 10 ** (hi - frac * (hi - lo))
    } else {
      value = vmax - frac * (vmax - vmin)
    }
    return { label: fmt(value), pct: frac }
  })
}

// --- Local computing pill: shimmer while computing, else last-slice summary ---
function ComputingPill() {
  const computing = useStudioStore((s) => s.computing)
  const sliceResult = useStudioStore((s) => s.sliceResult)

  if (computing) {
    return (
      <div style={{ ...CARD, padding: '6px 12px', fontSize: 13 }}>
        <span className="shimmer-text" style={{ fontWeight: 500 }}>
          Computing slice...
        </span>
      </div>
    )
  }
  if (!sliceResult) return null
  return (
    <div style={{ ...CARD, padding: '6px 12px', fontSize: 12, color: '#9aa' }}>
      <span style={{ color: '#8fa' }}>{sliceResult.quantity}</span>
      <span style={{ opacity: 0.7 }}> in {sliceResult.units || '--'}</span>
    </div>
  )
}

// --- Provenance + peak readout -------------------------------------------------
function ProvenanceCard() {
  const sliceResult = useStudioStore((s) => s.sliceResult)
  const bodyMap = useStudioStore((s) => s.bodyMap)
  const bodyMapNotPrecomputed = useStudioStore((s) => s.bodyMapNotPrecomputed)
  if (!sliceResult) return null

  const prov = frameProvenance({
    sliceProvenance: sliceResult.provenance,
    hasBodyMap: bodyMap != null,
    bodyMapNotPrecomputed,
  })
  const [px, py, pz] = sliceResult.peakXyz

  return (
    <div style={{ ...CARD, padding: 12, fontSize: 12, minWidth: 160 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={{ color: '#aab' }}>Source</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', color: '#ccd' }}>
          {prov.label}
          <ProvenanceDot confidence={prov.confidence} title={prov.title} />
        </span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginTop: 6 }}>
        <span style={{ color: '#aab' }}>Peak</span>
        <span style={{ fontFamily: 'monospace', color: '#dde' }}>
          {fmt(sliceResult.peakValue, ` ${sliceResult.units}`)}
        </span>
      </div>
      <div style={{ marginTop: 4, fontSize: 11, color: '#778', fontFamily: 'monospace', textAlign: 'right' }}>
        at [{px.toFixed(2)}, {py.toFixed(2)}, {pz.toFixed(2)}]
      </div>
    </div>
  )
}

// --- Colour bar for the active slice colour scale ------------------------------
function StudioColorBar() {
  const sliceResult = useStudioStore((s) => s.sliceResult)
  const colormap = useStudioStore((s) => s.colormap)
  const scaleMode = useStudioStore((s) => s.scaleMode)
  const fieldQuantity = useStudioStore((s) => s.fieldQuantity)

  // Mirror the slice plane's colour scale so the legend never lies: signed
  // components get the diverging map over the symmetric range.
  const display = resolveSliceDisplay({
    quantity: fieldQuantity,
    vmin: sliceResult?.vmin ?? 0,
    vmax: sliceResult?.vmax ?? 1,
    colormap,
    logMode: scaleMode === 'log',
  })
  const gradient = useMemo(() => colormapGradient(display.colormap), [display.colormap])
  if (!sliceResult) return null

  const ticks = buildTicks(display.vmin, display.vmax, display.logMode)
  const title = (
    <span style={{ fontSize: 12, color: '#cdd' }}>
      {sliceResult.quantity} ({sliceResult.units || '--'})
    </span>
  )

  return <GradientBar gradient={gradient} ticks={ticks} title={title} />
}

// Overlay container, mounted inside the scene column of StudioModule.
export default function StudioHud() {
  return (
    <>
      <div
        style={{
          position: 'absolute',
          top: 16,
          right: 16,
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-end',
          gap: 8,
        }}
      >
        <ComputingPill />
        <ProvenanceCard />
      </div>
      <div style={{ position: 'absolute', bottom: 16, left: 16, zIndex: 10 }}>
        <StudioColorBar />
      </div>
    </>
  )
}
