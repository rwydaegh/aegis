import { useMemo } from 'react'
import GradientBar, { type GradientBarTick } from '@/components/hud/GradientBar'
import ProvenanceDot from '@/components/panels/ProvenanceDot'
import { useStudioStore } from './store'
import { useStudioScales } from './useStudioScales'
import { colormapRgb } from './scene/studioHelpers'
import { logFloor, type ResolvedScale } from './scene/colorScale'
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

function buildTicks(scale: ResolvedScale): GradientBarTick[] {
  const N = 5
  // In log/dB mode the bar spans the dynamic-range window [logFloor, vmax]; in
  // linear mode it spans [vmin, vmax]. pct 0 = top = vmax.
  const useLog = scale.logMode && scale.vmax > 0
  const lo = useLog ? Math.log10(logFloor(scale)) : scale.vmin
  const hi = useLog ? Math.log10(scale.vmax) : scale.vmax
  return Array.from({ length: N }, (_, i) => {
    const frac = i / (N - 1)
    const at = hi - frac * (hi - lo)
    return { label: fmt(useLog ? 10 ** at : at), pct: frac }
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
  const showVolume = useStudioStore((s) => s.showVolume)
  const volumeResult = useStudioStore((s) => s.volumeResult)
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
      {showVolume && volumeResult && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginTop: 6, borderTop: '1px solid #1e1e26', paddingTop: 6 }}>
          <span style={{ color: '#aab' }}>Volume peak</span>
          <span style={{ fontFamily: 'monospace', color: '#dde' }}>
            {fmt(volumeResult.peakValue, ` ${volumeResult.units}`)}
          </span>
        </div>
      )}
    </div>
  )
}

// --- Colour bar for the active colour scale ------------------------------------
function StudioColorBar() {
  const sliceResult = useStudioStore((s) => s.sliceResult)
  const bodyMap = useStudioStore((s) => s.bodyMap)
  const scaleScope = useStudioStore((s) => s.scaleScope)
  const scaleMode = useStudioStore((s) => s.scaleMode)
  const robustClip = useStudioStore((s) => s.robustClip)
  const scales = useStudioScales()

  // The legend follows the slice scale when a slice is present (its diverging map
  // for signed components, its dB window in log); otherwise it falls back to the
  // body-map scale so a coloured body is never legend-less.
  const scale = sliceResult ? scales.slice : bodyMap ? scales.body : null
  const gradient = useMemo(() => (scale ? colormapGradient(scale.colormap) : ''), [scale])
  if (!scale) return null

  const quantity = sliceResult ? sliceResult.quantity : 'S_ab (deposited)'
  const units = sliceResult ? sliceResult.units || '--' : 'W/m^2 per W'
  const ticks = buildTicks(scale)

  // Honest footer: what the scale actually is (scope / robust / log dynamic range).
  const tags = [
    scaleScope === 'shared' ? 'shared' : 'per-surface',
    robustClip ? 'robust' : null,
    scaleMode === 'log' ? `${Math.round(scale.dynamicRangeDb)} dB` : scaleMode === 'fixed' ? 'fixed' : null,
  ].filter(Boolean)

  const title = (
    <span style={{ fontSize: 12, color: '#cdd' }}>
      {quantity} ({units})
    </span>
  )
  const footer = (
    <span style={{ fontSize: 10, color: '#8a93a6', letterSpacing: 0.3 }}>{tags.join(' · ')}</span>
  )

  return <GradientBar gradient={gradient} ticks={ticks} title={title} footer={footer} />
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
