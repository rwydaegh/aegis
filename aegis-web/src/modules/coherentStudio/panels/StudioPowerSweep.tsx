import { useMemo } from 'react'
import { Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ComplianceResult } from '../api'
import { useStudioStore } from '../store'
import { FieldLabel } from './widgets'

// Compact watts label (pW .. kW) for the absorbed-power axis and tooltip.
function fmtW(v: number | null | undefined): string {
  if (v == null || !isFinite(v) || v <= 0) return '--'
  if (v >= 1e3) return `${(v / 1e3).toPrecision(3)} kW`
  if (v >= 1) return `${v.toPrecision(3)} W`
  if (v >= 1e-3) return `${(v * 1e3).toPrecision(3)} mW`
  if (v >= 1e-6) return `${(v * 1e6).toPrecision(3)} µW`
  return `${v.toExponential(2)} W`
}

// Human label for the binding regime, echoing the HUD badge wording.
const REGIME_LABEL: Record<NonNullable<ComplianceResult['regime']>, string> = {
  free: 'free (power-limited)',
  sar_wb: 'SAR_wb-bound',
  peak_sab: 'peak S_ab-bound',
  both: 'both bound',
  infeasible: 'infeasible',
}

/**
 * The headline of absolute mode: total absorbed power P_abs as the transmit power
 * sweeps the dBm range, for the absolute-ICNIRP ECBF beam (solid) against the
 * matched filter (MRT, dashed). MRT is linear in power, so on the log axis it is a
 * straight diagonal that climbs without bound (it "diverges" through the limit);
 * ECBF tracks it until a basic restriction binds and then flattens against the
 * fixed ICNIRP whole-body limit (the dotted line). The dashed vertical marks the
 * live transmit power. When the peak 4 cm^2 S_ab restriction binds first, the
 * ECBF curve flattens just below the whole-body line (hover for the binding
 * regime). Only shown for the absolute ECBF beam.
 */
export default function StudioPowerSweep() {
  const sweep = useStudioStore((s) => s.powerSweep)
  const notAvailable = useStudioStore((s) => s.powerSweepNotAvailable)
  const showCompliance = useStudioStore((s) => s.showCompliance)
  const txPowerDbm = useStudioStore((s) => s.txPowerDbm)

  const { data, yDomain, wbLimit } = useMemo(() => {
    if (!sweep || sweep.power_dbm.length === 0) {
      return { data: null as null | Record<string, number | string>[], yDomain: [1, 1] as [number, number], wbLimit: null as number | null }
    }
    const rows = sweep.power_dbm.map((dbm, i) => ({
      dbm,
      w: sweep.power_w[i],
      ecbf: sweep.ecbf.p_abs_w[i],
      mrt: sweep.mrt.p_abs_w[i],
      regime: sweep.ecbf.regime[i] ?? 'free',
    }))
    const wb = sweep.limits.p_abs_wb_w
    const pos: number[] = []
    for (const r of rows) {
      if (isFinite(r.ecbf) && r.ecbf > 0) pos.push(r.ecbf)
      if (isFinite(r.mrt) && r.mrt > 0) pos.push(r.mrt)
    }
    if (wb && wb > 0) pos.push(wb)
    const lo = pos.length ? Math.min(...pos) : 1e-9
    const hi = pos.length ? Math.max(...pos) : 1
    // Pad the log span by a decade each side so the flat plateau and the limit
    // line are not glued to the frame.
    const domain: [number, number] = [Math.pow(10, Math.floor(Math.log10(lo)) - 1), Math.pow(10, Math.ceil(Math.log10(hi)) + 1)]
    return { data: rows, yDomain: domain, wbLimit: wb ?? null }
  }, [sweep])

  if (!showCompliance) {
    return <span style={{ fontSize: 10, color: '#667' }}>Enable the Compliance panel to chart the power sweep.</span>
  }
  if (notAvailable) {
    return <span style={{ fontSize: 10, color: '#667' }}>Power sweep needs the precomputed field-channel pack.</span>
  }
  if (!data) {
    return <span style={{ fontSize: 10, color: '#667' }}>Computing power sweep...</span>
  }

  return (
    <div>
      <FieldLabel title="Total absorbed power P_abs as the array transmit power sweeps 0 to 100 dBm. The absolute ECBF beam (orange) tracks the matched filter (MRT, grey dashed) until an ICNIRP basic restriction binds, then flattens against the fixed limit; MRT keeps rising (diverges). Both axes are logarithmic, so MRT is a straight line. The dotted line is the ICNIRP whole-body P_abs limit; the dashed vertical is the live transmit power.">
        P_abs vs transmit power
      </FieldLabel>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 6, right: 8, bottom: 4, left: -4 }}>
          <XAxis
            dataKey="dbm"
            type="number"
            domain={['dataMin', 'dataMax']}
            ticks={[0, 20, 40, 60, 80, 100]}
            tickFormatter={(v) => `${v}`}
            tick={{ fontSize: 8, fill: '#889' }}
            label={{ value: 'dBm', position: 'insideBottomRight', offset: -2, fontSize: 8, fill: '#778' }}
          />
          <YAxis
            scale="log"
            domain={yDomain}
            tick={{ fontSize: 8, fill: '#889' }}
            width={46}
            tickFormatter={(v) => fmtW(v)}
            allowDataOverflow
          />
          <Tooltip
            contentStyle={{ background: 'rgba(10,10,15,0.92)', border: '1px solid #283', borderRadius: 4, fontSize: 11 }}
            labelStyle={{ color: '#9aa' }}
            labelFormatter={(v, payload) => {
              const w = (payload?.[0]?.payload as { w?: number })?.w
              return `${Math.round(Number(v))} dBm${w != null ? ` (${fmtW(w)})` : ''}`
            }}
            formatter={(value, name, item) => {
              if (name === 'ECBF') {
                const regime = (item?.payload as { regime?: NonNullable<ComplianceResult['regime']> })?.regime
                const tag = regime ? `  [${REGIME_LABEL[regime]}]` : ''
                return [`${fmtW(Number(value))}${tag}`, name]
              }
              return [fmtW(Number(value)), name]
            }}
          />
          {wbLimit != null && (
            <ReferenceLine
              y={wbLimit}
              stroke="#7fe08a"
              strokeDasharray="2 2"
              strokeWidth={1}
              label={{ value: 'ICNIRP SAR_wb', position: 'insideTopLeft', fontSize: 8, fill: '#7fe08a' }}
            />
          )}
          <ReferenceLine x={txPowerDbm} stroke="#ddd" strokeDasharray="3 3" />
          <Line type="monotone" dataKey="mrt" name="MRT" stroke="#9aa3b2" strokeWidth={1.3} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="ecbf" name="ECBF" stroke="#f87f6a" strokeWidth={1.8} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px 10px', fontSize: 9, color: '#9aa', marginTop: 2 }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
          <span style={{ width: 10, height: 2, background: '#f87f6a', display: 'inline-block' }} /> ECBF (flattens)
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
          <span style={{ width: 10, height: 2, background: '#9aa3b2', display: 'inline-block' }} /> MRT (diverges)
        </span>
      </div>
      <p style={{ fontSize: 10, color: '#667', margin: '4px 2px 0' }}>
        ECBF rises with MRT while the power constraint binds, then flattens once a basic restriction binds. MRT keeps
        climbing past the limit (a violation an unconstrained beam would incur).
      </p>
    </div>
  )
}
