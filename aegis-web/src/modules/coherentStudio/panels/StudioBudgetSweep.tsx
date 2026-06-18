import { useMemo } from 'react'
import { Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { spectralEfficiency } from '../api'
import { useStudioStore } from '../store'
import { FieldLabel } from './widgets'

function fmt(v: number): string {
  if (!isFinite(v)) return '--'
  const a = Math.abs(v)
  if (a !== 0 && (a < 1e-2 || a >= 1e4)) return v.toExponential(2)
  return v.toPrecision(3)
}

// One line per compliance metric. Units differ wildly (W vs W/m^2 vs bit/s/Hz),
// so each curve is normalised to its own sweep maximum to share one [0,1] axis;
// the tooltip carries the real values. Colours echo nothing else in the panel.
const SERIES = [
  { key: 'p_abs', label: 'P_abs', color: '#f87f6a', unit: ' W/W' },
  { key: 'signal', label: 'Signal', color: '#7ab8ff', unit: '%' },
  { key: 'se', label: 'Rate', color: '#7fe08a', unit: ' bit/s/Hz' },
  { key: 'peak', label: 'S_ab peak', color: '#ffc857', unit: ' W/m²' },
  { key: 'pssar', label: 'S_ab 4cm²', color: '#c9a0ff', unit: ' W/m²' },
  { key: 'eta', label: 'η', color: '#9aa3b2', unit: '' },
] as const

/**
 * ECBF compliance metrics swept across the absorbed-power budget: the Pareto
 * front the budget slider rides. Each metric is normalised to its own sweep
 * maximum so the shapes (P_abs ramps then plateaus once the budget exceeds MRT's
 * own absorption; signal and rate climb with diminishing returns) sit on one
 * axis. The dashed line marks the live budget. Spectral efficiency is recomputed
 * client-side from signal_rel + the SNR knob, so the SNR slider reshapes its
 * curve instantly. Only meaningful for the ECBF beam.
 */
export default function StudioBudgetSweep() {
  const sweep = useStudioStore((s) => s.complianceSweep)
  const notAvailable = useStudioStore((s) => s.complianceSweepNotAvailable)
  const showCompliance = useStudioStore((s) => s.showCompliance)
  const snrMrtDb = useStudioStore((s) => s.snrMrtDb)
  const budgetFrac = useStudioStore((s) => s.ecbfBudgetFrac)

  const data = useMemo(() => {
    if (!sweep || sweep.budget_frac.length === 0) return null
    const s = sweep.series
    const se = s.signal_rel.map((r) => spectralEfficiency(r, snrMrtDb))
    const raw = {
      p_abs: s.p_abs_w,
      signal: s.signal_rel.map((r) => r * 100),
      se,
      peak: s.peak_sab,
      pssar: s.pssar_4cm2,
      eta: s.eta_4cm2,
    }
    const maxOf = (xs: number[]) => xs.reduce((m, v) => (isFinite(v) && Math.abs(v) > m ? Math.abs(v) : m), 0)
    const maxes = Object.fromEntries(SERIES.map((ser) => [ser.key, maxOf(raw[ser.key])])) as Record<string, number>
    return sweep.budget_frac.map((f, i) => {
      const point: Record<string, number> = { pct: f * 100 }
      for (const ser of SERIES) {
        const r = raw[ser.key][i]
        point[ser.key] = maxes[ser.key] > 0 ? r / maxes[ser.key] : 0
        point[`${ser.key}_raw`] = r
      }
      return point
    })
  }, [sweep, snrMrtDb])

  if (!showCompliance) {
    return <span style={{ fontSize: 10, color: '#667' }}>Enable the Compliance panel to chart the budget sweep.</span>
  }
  if (notAvailable) {
    return <span style={{ fontSize: 10, color: '#667' }}>Budget sweep needs the precomputed channel + Q pack.</span>
  }
  if (!data) {
    return <span style={{ fontSize: 10, color: '#667' }}>Computing budget sweep...</span>
  }

  return (
    <div>
      <FieldLabel title="Every compliance metric as the ECBF budget sweeps 5% to 100% of the MRT absorption. Each curve is normalised to its own maximum (so shapes are comparable, not magnitudes); hover for real values. The dashed line is the live budget.">
        Budget sweep (normalised)
      </FieldLabel>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 6, right: 6, bottom: 4, left: -18 }}>
          <XAxis
            dataKey="pct"
            type="number"
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 7, fill: '#889' }}
          />
          <YAxis domain={[0, 1]} tick={{ fontSize: 8, fill: '#889' }} width={28} tickFormatter={(v) => `${v}`} />
          <Tooltip
            contentStyle={{ background: 'rgba(10,10,15,0.92)', border: '1px solid #283', borderRadius: 4, fontSize: 11 }}
            labelStyle={{ color: '#9aa' }}
            labelFormatter={(v) => `budget = ${Math.round(Number(v))}%`}
            formatter={(_value, name, item) => {
              const ser = SERIES.find((x) => x.label === name)
              const raw = ser ? Number((item?.payload as Record<string, number>)?.[`${ser.key}_raw`]) : NaN
              return [`${fmt(raw)}${ser?.unit ?? ''}`, name]
            }}
          />
          {SERIES.map((ser) => (
            <Line
              key={ser.key}
              type="monotone"
              dataKey={ser.key}
              name={ser.label}
              stroke={ser.color}
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          ))}
          <ReferenceLine x={budgetFrac * 100} stroke="#ddd" strokeDasharray="3 3" />
        </LineChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px 10px', fontSize: 9, color: '#9aa', marginTop: 2 }}>
        {SERIES.map((ser) => (
          <span key={ser.key} style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
            <span style={{ width: 8, height: 2, background: ser.color, display: 'inline-block' }} />
            {ser.label}
          </span>
        ))}
      </div>
      <p style={{ fontSize: 10, color: '#667', margin: '4px 2px 0' }}>
        P_abs is linear in the budget while the cap binds, then flat once it exceeds MRT.
      </p>
    </div>
  )
}
