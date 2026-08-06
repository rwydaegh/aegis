import { useMemo } from 'react'
import Tex from '@/components/ui/Tex'
import ProvenanceDot from '@/components/panels/ProvenanceDot'
import { useStudioStore } from './store'
import { icnirpLimits, spectralEfficiency, type ComplianceResult, type PerConstraint } from './api'
import { useStudioScales } from './useStudioScales'
import { colormapRgb, powerDisplayFactor } from './scene/studioHelpers'
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

// Multiplier on absolute (power-class) readouts when the chosen Tx power differs
// from the calibration power the packs were traced at: powerScale = chosen/calib
// = 10^((txPowerDbm - calibDbm)/10). Field amplitudes use sqrt of this (see
// powerDisplayFactor). 1 at the default, so the baseline is unchanged.
function usePowerScale(): number {
  const txPowerDbm = useStudioStore((s) => s.txPowerDbm)
  const calibDbm = useStudioStore((s) => s.manifest?.calibration_tx_power_dbm ?? 25)
  return 10 ** ((txPowerDbm - calibDbm) / 10)
}

// "25 dBm (0.32 W)" style label for the chosen total transmit power.
function txPowerLabel(txPowerDbm: number): string {
  const w = 10 ** ((txPowerDbm - 30) / 10)
  const wStr = w >= 1 ? `${w.toPrecision(3)} W` : w >= 1e-3 ? `${(w * 1e3).toPrecision(3)} mW` : `${w.toExponential(1)} W`
  return `${txPowerDbm.toFixed(0)} dBm (${wStr})`
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

function buildTicks(scale: ResolvedScale, factor = 1): BarTick[] {
  const N = 5
  // In log/dB mode the bar spans the dynamic-range window [logFloor, vmax]; in
  // linear mode it spans [vmin, vmax]. pct 0 = top = vmax. `factor` rescales the
  // tick *labels* to the chosen Tx power (the colours come from raw data, so the
  // bar is unchanged; only the numbers move).
  const useLog = scale.logMode && scale.vmax > 0
  const lo = useLog ? Math.log10(logFloor(scale)) : scale.vmin
  const hi = useLog ? Math.log10(scale.vmax) : scale.vmax
  return Array.from({ length: N }, (_, i) => {
    const frac = i / (N - 1)
    const at = hi - frac * (hi - lo)
    return { label: fmt((useLog ? 10 ** at : at) * factor), pct: frac }
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
function ScientificColorBar({
  scale,
  titleTex,
  units,
  factor = 1,
}: {
  scale: ResolvedScale
  titleTex: string
  units: string
  factor?: number
}) {
  const gradient = useMemo(() => colormapGradient(scale.colormap), [scale.colormap])
  const ticks = buildTicks(scale, factor)
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
  const powerScale = usePowerScale()
  if (!sliceResult) return null

  const prov = frameProvenance({
    sliceProvenance: sliceResult.provenance,
    hasBodyMap: bodyMap != null,
    bodyMapNotPrecomputed,
  })
  const [px, py, pz] = sliceResult.peakXyz
  // Slice peak follows its quantity (field vs power); volume is always S (power).
  const slicePeak = sliceResult.peakValue * powerDisplayFactor(sliceResult.quantity, powerScale)
  const volumePeak = volumeResult ? volumeResult.peakValue * powerScale : 0

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
          {fmt(slicePeak, ` ${sliceResult.units}`)}
        </span>
      </div>
      <div style={{ marginTop: 4, fontSize: 11, color: '#778', fontFamily: 'monospace', textAlign: 'right' }}>
        at [{px.toFixed(2)}, {py.toFixed(2)}, {pz.toFixed(2)}]
      </div>
      {showVolume && volumeResult && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginTop: 6, borderTop: '1px solid #1e1e26', paddingTop: 6 }}>
          <span style={{ color: '#aab' }}>Volume peak</span>
          <span style={{ fontFamily: 'monospace', color: '#dde' }}>
            {fmt(volumePeak, ` ${volumeResult.units}`)}
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

// Regime badge: which ICNIRP restriction binds the absolute ECBF solution.
const REGIME_INFO: Record<NonNullable<ComplianceResult['regime']>, { label: string; color: string }> = {
  free: { label: 'Free', color: '#5c8' },
  sar_wb: { label: 'SAR_wb-bound', color: '#fb3' },
  peak_sab: { label: 'Peak S_ab-bound', color: '#fb3' },
  both: { label: 'Both bound', color: '#f93' },
  infeasible: { label: 'Infeasible', color: '#f55' },
}

function RegimeBadge({ regime }: { regime: NonNullable<ComplianceResult['regime']> }) {
  const info = REGIME_INFO[regime]
  return (
    <span
      title="The ICNIRP basic restriction that limits the absolute ECBF beam at this transmit power. 'Free' means the power constraint binds (no restriction is active yet)."
      style={{
        fontFamily: 'monospace',
        fontSize: 11,
        fontWeight: 600,
        color: '#111',
        background: info.color,
        borderRadius: 4,
        padding: '1px 6px',
      }}
    >
      {info.label}
    </span>
  )
}

// Utilisation bar: fraction of the ICNIRP limit a restriction reaches. Green
// under 80%, amber approaching the limit, red at or over it (a violation in
// relative mode, where nothing enforces the limit).
function utilColor(util: number): string {
  if (util >= 1.0) return '#f55'
  if (util >= 0.8) return '#fb3'
  return '#5c8'
}

function UtilisationBar({
  label,
  util,
  detail,
  active,
}: {
  label: string
  util: number | null
  detail: string
  active?: boolean
}) {
  const u = util == null || !isFinite(util) ? 0 : util
  const pct = Math.min(100, Math.max(0, u * 100))
  return (
    <div style={{ marginTop: 6 }} title={detail}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, fontSize: 11 }}>
        <span style={{ color: active ? '#dde' : '#aab' }}>
          {label}
          {active ? ' •' : ''}
        </span>
        <span style={{ fontFamily: 'monospace', color: '#dde' }}>{(u * 100).toPrecision(3)}%</span>
      </div>
      <div style={{ marginTop: 3, height: 5, background: '#1e1e26', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: utilColor(u) }} />
      </div>
    </div>
  )
}

// Absolute mode: regime badge + a utilisation bar per enforced restriction, read
// straight from the backend (the solve ran at the chosen transmit power, so the
// utilisation is already absolute).
function AbsoluteComplianceBars({ compliance }: { compliance: ComplianceResult }) {
  const per = compliance.per_constraint ?? []
  const labelOf = (c: PerConstraint) =>
    c.name === 'sar_wb' ? 'SAR_wb' : `S_ab,4cm² (≤ ${c.limit} ${c.unit})`
  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 }}>
        <span style={{ color: '#aab', fontSize: 11 }}>Regime</span>
        {compliance.regime && <RegimeBadge regime={compliance.regime} />}
      </div>
      {per.map((c) => (
        <UtilisationBar
          key={c.name}
          label={labelOf(c)}
          util={c.utilisation}
          active={c.active}
          detail={`${c.name === 'sar_wb' ? 'Whole-body SAR' : 'Peak 4 cm² S_ab'}: ${fmt(c.value, ' ' + c.unit)} of the ${c.limit} ${c.unit} ICNIRP limit`}
        />
      ))}
    </>
  )
}

// Relative mode: the scalars are per-watt, so the utilisation compares the
// dBm-scaled dose to the ICNIRP limit. Nothing enforces it here, so > 100% is a
// genuine (flagged) violation, not a binding regime.
function RelativeComplianceBars({
  compliance,
  powerScale,
  freqGhz,
}: {
  compliance: ComplianceResult
  powerScale: number
  freqGhz: number
}) {
  const limits = icnirpLimits(freqGhz)
  const sarWb = compliance.sar_wb == null ? null : compliance.sar_wb * powerScale
  const peak = compliance.pssar_4cm2 * powerScale
  return (
    <div style={{ marginTop: 6, borderTop: '1px solid #1e1e26', paddingTop: 4 }}>
      <UtilisationBar
        label={`SAR_wb (≤ ${limits.sarWb} W/kg)`}
        util={sarWb == null ? null : sarWb / limits.sarWb}
        detail="Whole-body SAR at the chosen transmit power as a fraction of the ICNIRP limit. Relative mode does not enforce it, so over 100% is a violation."
      />
      {limits.sab4cm2 != null && (
        <UtilisationBar
          label={`S_ab,4cm² (≤ ${limits.sab4cm2} W/m²)`}
          util={peak / limits.sab4cm2}
          detail="Peak 4 cm² S_ab at the chosen transmit power as a fraction of the ICNIRP limit. Relative mode does not enforce it, so over 100% is a violation."
        />
      )}
    </div>
  )
}

function ComplianceCard() {
  const showCompliance = useStudioStore((s) => s.showCompliance)
  const compliance = useStudioStore((s) => s.compliance)
  const notAvailable = useStudioStore((s) => s.complianceNotAvailable)
  const snrMrtDb = useStudioStore((s) => s.snrMrtDb)
  const txPowerDbm = useStudioStore((s) => s.txPowerDbm)
  const frequencyGhz = useStudioStore((s) => s.frequencyGhz)
  const powerScale = usePowerScale()
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
  // Absolute mode already ran the solve at the chosen transmit power, so its
  // densities are absolute (no rescale). Relative mode is per-watt, so the
  // dBm-scaled display multiplies by powerScale. signal_rel, eta and the
  // SNR-anchored rate are ratios and stay invariant either way.
  const absolute = compliance.constraint_mode === 'absolute'
  const scale = absolute ? 1 : powerScale
  const sarWb = compliance.sar_wb == null ? null : compliance.sar_wb * scale
  return (
    <div style={{ ...CARD, padding: 12, fontSize: 12, minWidth: 210 }}>
      <div style={{ color: '#aab', marginBottom: 2, display: 'flex', justifyContent: 'space-between' }}>
        <span>Compliance</span>
        <span style={{ fontSize: 10, color: '#667' }} title="Absolute dose / field at the chosen total transmit power">
          at {txPowerLabel(txPowerDbm)}
        </span>
      </div>
      <ComplianceRow label="Signal vs MRT" value={signalPct} title="Served signal |h.x|^2 relative to the matched-filter beam (100% = MRT)" />
      <ComplianceRow
        label="Rate"
        value={se == null ? '--' : fmt(se, ' bit/s/Hz')}
        title={`Single-user spectral efficiency log2(1 + SNR_mrt * signal), anchored at SNR_mrt = ${snrMrtDb} dB. Independent of transmit power (set by the SNR knob).`}
      />
      <ComplianceRow label="P_abs" value={fmt(compliance.p_abs_w * scale, ' W')} title="Total absorbed power at the chosen transmit power" />
      <ComplianceRow
        label="SAR_wb"
        value={sarWb == null ? '--' : fmt(sarWb, ' W/kg')}
        title={
          compliance.body_mass_kg == null
            ? 'Whole-body SAR (body mass unknown)'
            : `Whole-body SAR = P_abs / ${compliance.body_mass_kg} kg`
        }
      />
      <ComplianceRow
        label="S_ab (peak)"
        value={fmt(compliance.peak_sab * scale, ' W/m²')}
        title="Peak per-triangle absorbed power density (the unaveraged hotspot, ICNIRP basic-restriction quantity above 6 GHz)"
      />
      <ComplianceRow
        label={`S_ab,${compliance.averaging_area_cm2}cm² (peak)`}
        value={fmt(compliance.pssar_4cm2 * scale, ' W/m²')}
        title="Peak absorbed power density spatially averaged over the ICNIRP 4 cm^2 area (the >6 GHz basic restriction; this is the W/m^2 S_ab, not a mass-averaged SAR)"
      />
      <ComplianceRow label="η (peak/mean)" value={fmt(compliance.eta_4cm2)} title="Peak 4 cm^2 S_ab over the area-mean absorbed power density (localisation factor)" />
      {absolute ? (
        <AbsoluteComplianceBars compliance={compliance} />
      ) : (
        <RelativeComplianceBars compliance={compliance} powerScale={powerScale} freqGhz={frequencyGhz} />
      )}
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
  const powerScale = usePowerScale()

  if (!sliceResult && !bodyMap) return null

  // The slice carries S / field components; the body map is S_ab (power-class)
  // except 'amp', which is a dimensionless ratio and must not be rescaled.
  const sliceFactor = sliceResult ? powerDisplayFactor(sliceResult.quantity, powerScale) : 1
  const bodyFactor = bodyMapQuantity === 'amp' ? 1 : powerScale

  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
      {sliceResult && (
        <ScientificColorBar
          scale={scales.slice}
          titleTex={quantityTex(sliceResult.quantity)}
          units={sliceResult.units || '-'}
          factor={sliceFactor}
        />
      )}
      {bodyMap && (
        <ScientificColorBar
          scale={scales.body}
          titleTex={bodyTitleTex(bodyMapQuantity)}
          units={bodyMap.units || 'W/m^2 per W'}
          factor={bodyFactor}
        />
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
