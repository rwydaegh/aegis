import { useMemo } from 'react'
import Tex from '@/components/ui/Tex'
import ProvenanceDot from '@/components/panels/ProvenanceDot'
import { useStudioStore } from './store'
import { spectralEfficiency } from './api'
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

// CSS gradient sampled from the active colormap, high value at the top (pct 0 =
// top = vmax), so the bar reads like a printed colour scale.
function colormapGradient(name: string): string {
  const N = 16
  const stops: string[] = []
  for (let i = 0; i <= N; i++) {
    const pct = i / N
    const t = 1 - pct // top (pct 0) is the colormap max
    const [r, g, b] = colormapRgb(name, t)
    stops.push(`rgb(${r},${g},${b}) ${(pct * 100).toFixed(0)}%`)
  }
  return `linear-gradient(to bottom, ${stops.join(', ')})`
}

interface BarTick {
  label: string
  pct: number
}

function buildTicks(scale: ResolvedScale): BarTick[] {
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

// Fractional position (0 = top = vmax, 1 = bottom) of the zero level, or null
// when zero is off a linear scale's span (log scales have no zero). A signed
// (diverging) scale puts zero at its centre; a non-negative scale pins its floor
// to zero so it lands at the bottom. The user asked for zero always marked.
function zeroPct(scale: ResolvedScale): number | null {
  if (scale.logMode) return null
  const { vmin, vmax } = scale
  if (vmax <= vmin || vmin > 0 || vmax < 0) return null
  return (vmax - 0) / (vmax - vmin)
}

// LaTeX symbol for a slice / body quantity. Falls back to the raw key.
const QUANTITY_TEX: Record<string, string> = {
  S: 'S',
  poynting: '|\\langle\\mathbf{S}\\rangle|',
  absE: '|E|',
  ReEx: '\\mathrm{Re}\\,E_x',
  ReEy: '\\mathrm{Re}\\,E_y',
  ReEz: '\\mathrm{Re}\\,E_z',
}

function quantityTex(quantity: string): string {
  return QUANTITY_TEX[quantity] ?? quantity
}

// Body-map symbol. Every map is absorbed power density S_ab except 'amp', which
// is the dimensionless amplification ratio.
function bodyTitleTex(quantity: string): string {
  return quantity === 'amp' ? 'A' : 'S_{\\mathrm{ab}}'
}

// Render a units string as upright LaTeX, e.g. "W/m^2 per W" -> roman with a
// squared exponent and thin spaces. Tex has throwOnError off, so an odd unit
// string degrades gracefully rather than breaking the HUD.
function unitsTex(units: string): string {
  const u = units.replace(/\^(\d+)/g, '^{$1}').replace(/ /g, '\\,')
  return `\\left[\\mathrm{${u}}\\right]`
}

const BAR_H = 188
const BAR_W = 14

// One scientific colour scale: a white box with a square black border, a
// LaTeX-set definition, evenly spaced ticks, and an explicit zero marker (centre
// for a diverging scale, bottom for a non-negative one).
function ScientificColorBar({ scale, titleTex, units }: { scale: ResolvedScale; titleTex: string; units: string }) {
  const gradient = useMemo(() => colormapGradient(scale.colormap), [scale.colormap])
  const ticks = buildTicks(scale)
  const z = zeroPct(scale)
  return (
    <div style={{ background: '#ffffff', border: '1px solid #000000', padding: '8px 10px', color: '#000000', fontFamily: 'serif' }}>
      <div style={{ fontSize: 13, marginBottom: 6, whiteSpace: 'nowrap' }}>
        <Tex math={units && units !== '-' ? `${titleTex}\\;${unitsTex(units)}` : titleTex} />
      </div>
      <div style={{ display: 'flex', gap: 6 }}>
        <div style={{ position: 'relative', height: BAR_H, width: 54 }}>
          {ticks.map(({ label, pct }, i) => (
            <span
              key={i}
              style={{
                position: 'absolute',
                right: 0,
                top: pct * BAR_H - 7,
                fontSize: 11,
                fontFamily: 'monospace',
                fontVariantNumeric: 'tabular-nums',
                whiteSpace: 'nowrap',
              }}
            >
              {label}
            </span>
          ))}
        </div>
        <div style={{ position: 'relative', height: BAR_H, width: BAR_W }}>
          <div style={{ background: gradient, height: BAR_H, width: BAR_W, border: '1px solid #000000' }} />
          {ticks.map(({ pct }, i) => (
            <div key={i} style={{ position: 'absolute', top: pct * BAR_H, left: -3, width: 3, height: 1, background: '#000000' }} />
          ))}
          {z != null && (
            <>
              <div style={{ position: 'absolute', top: z * BAR_H, left: -5, width: BAR_W + 7, height: 2, background: '#000000' }} />
              <span style={{ position: 'absolute', top: z * BAR_H - 7, left: BAR_W + 5, fontSize: 11, fontFamily: 'monospace', fontWeight: 700 }}>
                0
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  )
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

// --- ICNIRP compliance scalars (opt-in) ----------------------------------------
function ComplianceRow({ label, value, title }: { label: string; value: string; title?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginTop: 5 }} title={title}>
      <span style={{ color: '#aab' }}>{label}</span>
      <span style={{ fontFamily: 'monospace', color: '#dde' }}>{value}</span>
    </div>
  )
}

function ComplianceCard() {
  const showCompliance = useStudioStore((s) => s.showCompliance)
  const compliance = useStudioStore((s) => s.compliance)
  const notAvailable = useStudioStore((s) => s.complianceNotAvailable)
  const snrMrtDb = useStudioStore((s) => s.snrMrtDb)
  if (!showCompliance) return null

  if (!compliance) {
    return (
      <div style={{ ...CARD, padding: 12, fontSize: 12, minWidth: 200 }}>
        <div style={{ color: '#aab', marginBottom: 2 }}>Compliance</div>
        <div style={{ fontSize: 11, color: '#778' }}>
          {notAvailable ? 'Not available for this beam / scenario' : 'Computing...'}
        </div>
      </div>
    )
  }

  // signal_rel is a fraction of the MRT served signal; show it as a percentage.
  const signalPct = isFinite(compliance.signal_rel) ? `${(compliance.signal_rel * 100).toPrecision(3)}%` : '--'
  // Spectral efficiency is recomputed live from signal_rel + the SNR knob, so the
  // SNR slider updates this with no server round-trip.
  const se = isFinite(compliance.signal_rel) ? spectralEfficiency(compliance.signal_rel, snrMrtDb) : null
  return (
    <div style={{ ...CARD, padding: 12, fontSize: 12, minWidth: 200 }}>
      <div style={{ color: '#aab', marginBottom: 2, display: 'flex', justifyContent: 'space-between' }}>
        <span>Compliance</span>
        <span style={{ fontSize: 10, color: '#667' }}>per W tx</span>
      </div>
      <ComplianceRow label="Signal vs MRT" value={signalPct} title="Served signal |h.x|^2 relative to the matched-filter beam (100% = MRT)" />
      <ComplianceRow
        label="Rate"
        value={se == null ? '--' : fmt(se, ' bit/s/Hz')}
        title={`Single-user spectral efficiency log2(1 + SNR_mrt * signal), anchored at SNR_mrt = ${snrMrtDb} dB`}
      />
      <ComplianceRow label="P_abs" value={fmt(compliance.p_abs_w, ' W')} title="Total absorbed power per watt transmitted (the absorption fraction)" />
      <ComplianceRow
        label="SAR_wb"
        value={compliance.sar_wb == null ? '--' : fmt(compliance.sar_wb, ' W/kg')}
        title={
          compliance.body_mass_kg == null
            ? 'Whole-body SAR (body mass unknown)'
            : `Whole-body SAR = P_abs / ${compliance.body_mass_kg} kg`
        }
      />
      <ComplianceRow
        label="S_ab (peak)"
        value={fmt(compliance.peak_sab, ' W/m²')}
        title="Peak per-triangle absorbed power density (the unaveraged hotspot, ICNIRP basic-restriction quantity above 6 GHz)"
      />
      <ComplianceRow
        label={`S_ab,${compliance.averaging_area_cm2}cm² (peak)`}
        value={fmt(compliance.pssar_4cm2, ' W/m²')}
        title="Peak absorbed power density spatially averaged over the ICNIRP 4 cm^2 area (the >6 GHz basic restriction; this is the W/m^2 S_ab, not a mass-averaged SAR)"
      />
      <ComplianceRow label="η (peak/mean)" value={fmt(compliance.eta_4cm2)} title="Peak 4 cm^2 S_ab over the area-mean absorbed power density (localisation factor)" />
    </div>
  )
}

// --- Colour bars: one for the field slice, one for the deposited body map ------
// They can carry different quantities and (in per-surface scope) different
// ranges, so each gets its own scale; shown side by side.
function StudioColorBar() {
  const sliceResult = useStudioStore((s) => s.sliceResult)
  const bodyMap = useStudioStore((s) => s.bodyMap)
  const bodyMapQuantity = useStudioStore((s) => s.bodyMapQuantity)
  const scales = useStudioScales()

  if (!sliceResult && !bodyMap) return null

  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
      {sliceResult && (
        <ScientificColorBar
          scale={scales.slice}
          titleTex={quantityTex(sliceResult.quantity)}
          units={sliceResult.units || '-'}
        />
      )}
      {bodyMap && (
        <ScientificColorBar scale={scales.body} titleTex={bodyTitleTex(bodyMapQuantity)} units={bodyMap.units || 'W/m^2 per W'} />
      )}
    </div>
  )
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
        <ComplianceCard />
      </div>
      <div style={{ position: 'absolute', bottom: 16, left: 16, zIndex: 10 }}>
        <StudioColorBar />
      </div>
    </>
  )
}
