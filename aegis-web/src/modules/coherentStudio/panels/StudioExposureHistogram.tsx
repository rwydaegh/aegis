import { useMemo } from 'react'
import {
  Bar,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { computeHistogram } from '@/components/panels/analysis/utils'
import { useStudioStore } from '../store'
import { useStudioScales } from '../useStudioScales'
import { colormapRgb } from '../scene/studioHelpers'
import { percentileRange, scaleNormalise } from '../scene/colorScale'
import { FieldLabel } from './widgets'

function fmt(v: number): string {
  if (!isFinite(v)) return '--'
  const a = Math.abs(v)
  if (a !== 0 && (a < 1e-2 || a >= 1e4)) return v.toExponential(1)
  return v.toPrecision(3)
}

/**
 * Distribution of the deposited body map across illuminated triangles: a
 * log-binned histogram coloured by the active colormap, with the cumulative
 * fraction overlaid and the median / p95 / peak marked. Reuses the viewer's
 * computeHistogram; all client-side from the body map already in the store.
 */
export default function StudioExposureHistogram() {
  const bodyMap = useStudioStore((s) => s.bodyMap)
  const { body: scale } = useStudioScales()

  const data = useMemo(() => {
    if (!bodyMap || bodyMap.values.length === 0) return null
    const arr = Float32Array.from(bodyMap.values)
    const hist = computeHistogram(arr, 24)
    if (hist.bins.length === 0) return null
    const total = hist.bins.reduce((a, b) => a + b.count, 0)
    let run = 0
    const rows = hist.bins.map((b) => {
      run += b.count
      return {
        label: b.label,
        count: b.count,
        cdf: total > 0 ? (100 * run) / total : 0,
        center: 0.5 * (b.x0 + b.x1),
      }
    })
    const pct = percentileRange(arr, 0.5, 0.95)
    let peak = -Infinity
    for (let i = 0; i < arr.length; i++) if (arr[i] > peak) peak = arr[i]
    return {
      rows,
      p50: pct?.vmin ?? 0,
      p95: pct?.vmax ?? 0,
      peak,
      units: bodyMap.units || 'W/m^2',
      nTris: bodyMap.values.length,
    }
  }, [bodyMap])

  if (!data) {
    return <span style={{ fontSize: 10, color: '#667' }}>No body map yet.</span>
  }

  // Map a bin centre to a reference-line x by its label (XAxis is categorical).
  const labelAtLeast = (v: number) => data.rows.find((r) => r.center >= v)?.label

  return (
    <div>
      <FieldLabel title="How the deposited S_ab is distributed over the illuminated body triangles. Bars are log-binned and coloured by the active colormap; the line is the cumulative fraction of triangles.">
        Exposure distribution
      </FieldLabel>
      <ResponsiveContainer width="100%" height={150}>
        <ComposedChart data={data.rows} margin={{ top: 6, right: 6, bottom: 4, left: -8 }}>
          <XAxis dataKey="label" tick={{ fontSize: 7, fill: '#889' }} interval={4} />
          <YAxis yAxisId="count" tick={{ fontSize: 8, fill: '#889' }} width={28} />
          <YAxis yAxisId="cdf" orientation="right" domain={[0, 100]} tick={{ fontSize: 8, fill: '#7a8' }} width={26} unit="%" />
          <Tooltip
            contentStyle={{ background: 'rgba(10,10,15,0.9)', border: '1px solid #283', borderRadius: 4, fontSize: 11 }}
            labelStyle={{ color: '#9aa' }}
            formatter={(value, name) =>
              name === 'cdf' ? [`${Number(value).toFixed(0)}%`, 'cumulative'] : [value, 'triangles']
            }
          />
          <Bar yAxisId="count" dataKey="count" isAnimationActive={false}>
            {data.rows.map((r, i) => {
              const [red, g, b] = colormapRgb(scale.colormap, scaleNormalise(r.center, scale))
              return <Cell key={i} fill={`rgb(${red},${g},${b})`} />
            })}
          </Bar>
          <Line yAxisId="cdf" dataKey="cdf" stroke="#7fe3b0" strokeWidth={1.5} dot={false} isAnimationActive={false} />
          {labelAtLeast(data.p95) && (
            <ReferenceLine
              yAxisId="count"
              x={labelAtLeast(data.p95)}
              stroke="#e0b050"
              strokeDasharray="3 3"
              label={{ value: 'p95', fontSize: 8, fill: '#e0b050', position: 'top' }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#9aa', marginTop: 2 }}>
        <span>median {fmt(data.p50)}</span>
        <span style={{ color: '#e0b050' }}>p95 {fmt(data.p95)}</span>
        <span style={{ color: '#dde' }}>peak {fmt(data.peak)}</span>
      </div>
      <p style={{ fontSize: 10, color: '#667', margin: '4px 2px 0' }}>
        S_ab in {data.units} over {data.nTris.toLocaleString()} triangles
      </p>
    </div>
  )
}
