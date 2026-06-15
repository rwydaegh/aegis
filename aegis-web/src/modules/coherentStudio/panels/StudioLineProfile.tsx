import { useMemo, useState } from 'react'
import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useStudioStore } from '../store'
import { centerLineProfile, type CutAxis } from './studioLineProfile'
import { FieldLabel, Segmented, type Option } from './widgets'

const AXIS_OPTIONS: Option<CutAxis>[] = [
  { value: 'e1', label: 'Horizontal' },
  { value: 'e2', label: 'Vertical' },
]

function fmt(v: number): string {
  if (!isFinite(v)) return '--'
  const a = Math.abs(v)
  if (a !== 0 && (a < 1e-2 || a >= 1e4)) return v.toExponential(1)
  return v.toPrecision(3)
}

function fmtOffset(t: number): string {
  const cm = t * 100
  return `${cm >= 0 ? '+' : ''}${cm.toFixed(1)}cm`
}

/**
 * 1D line probe through the centre of the slice: the field along the horizontal
 * (e1) or vertical (e2) centre line, with the peak marked and the full-width at
 * half maximum reported. A faithful 1D companion to the 2D slice, useful for
 * reading the focal-spot width straight off the curve.
 */
export default function StudioLineProfile() {
  const slice = useStudioStore((s) => s.sliceResult)
  const [axis, setAxis] = useState<CutAxis>('e1')

  const data = useMemo(() => {
    if (!slice || slice.scalar.length === 0) return null
    const prof = centerLineProfile(
      { scalar: slice.scalar, shape: slice.shape, world: { extent: slice.world.extent } },
      axis,
    )
    if (prof.points.length < 2) return null
    return { ...prof, units: slice.units || '', quantity: slice.quantity }
  }, [slice, axis])

  return (
    <div>
      <FieldLabel title="A 1D cut of the field through the centre of the slice plane. Horizontal runs along e1, vertical along e2.">
        Line probe
      </FieldLabel>
      <Segmented<CutAxis> value={axis} options={AXIS_OPTIONS} onChange={setAxis} />
      {!data ? (
        <span style={{ fontSize: 10, color: '#667', display: 'block', marginTop: 6 }}>No slice yet.</span>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={data.points} margin={{ top: 8, right: 6, bottom: 4, left: -8 }}>
              <XAxis
                dataKey="t"
                type="number"
                domain={['dataMin', 'dataMax']}
                tickFormatter={fmtOffset}
                tick={{ fontSize: 7, fill: '#889' }}
              />
              <YAxis tick={{ fontSize: 8, fill: '#889' }} width={34} tickFormatter={(v) => fmt(Number(v))} />
              <Tooltip
                contentStyle={{ background: 'rgba(10,10,15,0.9)', border: '1px solid #283', borderRadius: 4, fontSize: 11 }}
                labelStyle={{ color: '#9aa' }}
                labelFormatter={(v) => `offset ${fmtOffset(Number(v))}`}
                formatter={(value) => [fmt(Number(value)), data.quantity]}
              />
              <ReferenceLine x={0} stroke="#445" strokeDasharray="2 2" />
              <ReferenceLine
                x={data.peakOffset}
                stroke="#e0b050"
                strokeDasharray="3 3"
                label={{ value: 'peak', fontSize: 8, fill: '#e0b050', position: 'top' }}
              />
              <Line type="monotone" dataKey="value" stroke="#9cf" strokeWidth={1.6} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#9aa', marginTop: 2 }}>
            <span title="Field value at the cut peak.">peak {fmt(data.peakValue)}</span>
            <span title="Full-width at half maximum of the cut: the focal-spot width along this axis.">
              FWHM {isFinite(data.fwhm) ? fmtOffset(data.fwhm).replace('+', '') : '--'}
            </span>
          </div>
        </>
      )}
    </div>
  )
}
