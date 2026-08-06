import { useMemo } from 'react'
import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { computeHistogram } from '@/components/panels/analysis/utils'
import { useStudioStore } from '../store'
import { colormapRgb } from '../scene/studioHelpers'
import { compareMaps } from './studioCompare'
import { beamOptions } from './controls'

function fmt(v: number): string {
  if (!isFinite(v)) return '--'
  const a = Math.abs(v)
  if (a !== 0 && (a < 1e-2 || a >= 1e4)) return v.toExponential(1)
  return v.toPrecision(3)
}

function fmtPct(v: number): string {
  if (!isFinite(v)) return '--'
  return `${v >= 0 ? '+' : ''}${v.toFixed(0)}%`
}

const btnStyle: React.CSSProperties = {
  width: '100%',
  padding: '6px 8px',
  fontSize: 11,
  color: '#bcd',
  background: '#161922',
  border: '1px solid #2a2f3a',
  borderRadius: 5,
  cursor: 'pointer',
}

/** One stat row: A -> B with the percent change, green when B is lower than A. */
function StatRow({ name, a, b, pct }: { name: string; a: number; b: number; pct: number }) {
  const better = pct < 0
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#9aa', margin: '2px 0' }}>
      <span style={{ color: '#7a8' }}>{name}</span>
      <span style={{ fontVariantNumeric: 'tabular-nums' }}>
        {fmt(a)} {'->'} {fmt(b)}{' '}
        <span style={{ color: better ? '#7fe3b0' : '#e08a8a' }}>{fmtPct(pct)}</span>
      </span>
    </div>
  )
}

/**
 * A/B beam comparison. Capture the current body map as a reference (A), then read
 * how the live map (B) compares: peak / p95 / mean change and a diverging
 * histogram of the per-triangle delta B - A (blue = exposure reduced, red =
 * increased). The intended workflow is to set the reference on MRT, switch the
 * beam to ECBF, and read the reduction.
 */
export default function StudioCompare() {
  const bodyMap = useStudioStore((s) => s.bodyMap)
  const reference = useStudioStore((s) => s.referenceMap)
  const setReference = useStudioStore((s) => s.setReferenceMap)
  const beam = useStudioStore((s) => s.beam)
  const mesh = useStudioStore((s) => s.mesh)
  const bodyMapQuantity = useStudioStore((s) => s.bodyMapQuantity)
  const frequencyGhz = useStudioStore((s) => s.frequencyGhz)
  const manifest = useStudioStore((s) => s.manifest)

  const beamLabel = useMemo(() => {
    const o = beamOptions(manifest).find((b) => b.value === beam)
    return o ? o.label : beam || bodyMapQuantity
  }, [manifest, beam, bodyMapQuantity])

  const capture = () => {
    if (!bodyMap) return
    setReference({ values: bodyMap.values.slice(), label: `${beamLabel} · ${mesh} · ${frequencyGhz}GHz` })
  }

  const stats = useMemo(() => {
    if (!reference || !bodyMap) return null
    return compareMaps(reference.values, bodyMap.values)
  }, [reference, bodyMap])

  const hist = useMemo(() => {
    if (!stats) return null
    const bins = computeHistogram(stats.delta, 25).bins
    if (bins.length === 0) return null
    const m = Math.max(stats.maxAbsDelta, 1e-30)
    return bins.map((bn) => {
      const center = 0.5 * (bn.x0 + bn.x1)
      const [r, g, b] = colormapRgb('coolwarm', 0.5 * (center / m) + 0.5)
      return { label: bn.label, count: bn.count, center, fill: `rgb(${r},${g},${b})` }
    })
  }, [stats])

  return (
    <div>
      <button type="button" onClick={capture} disabled={!bodyMap} style={{ ...btnStyle, opacity: bodyMap ? 1 : 0.4 }}>
        Set current map as reference (A)
      </button>

      {!reference ? (
        <p style={{ fontSize: 10, color: '#667', margin: '6px 2px 0' }}>
          Capture a reference beam, then switch beam to see the per-triangle change.
        </p>
      ) : (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '8px 0 4px' }}>
            <span style={{ fontSize: 11, color: '#9cf' }}>
              A: {reference.label}
            </span>
            <button
              type="button"
              onClick={() => setReference(null)}
              style={{ ...btnStyle, width: 'auto', padding: '2px 8px' }}
            >
              clear
            </button>
          </div>

          {!stats ? (
            <p style={{ fontSize: 10, color: '#e0b050', margin: '4px 2px' }}>
              Reference has a different triangle count (different mesh / array). Re-capture.
            </p>
          ) : (
            <>
              <div style={{ fontSize: 10, color: '#667', margin: '2px 0 4px' }}>B: {beamLabel} (live)</div>
              <StatRow name="peak" a={stats.peakA} b={stats.peakB} pct={stats.peakPct} />
              <StatRow name="p95" a={stats.p95A} b={stats.p95B} pct={stats.p95Pct} />
              <StatRow name="mean" a={stats.meanA} b={stats.meanB} pct={stats.meanPct} />
              <div style={{ fontSize: 10, color: '#9aa', margin: '4px 0 2px' }}>
                B lower than A on {(stats.reducedFrac * 100).toFixed(0)}% of triangles
              </div>

              {hist && (
                <ResponsiveContainer width="100%" height={120}>
                  <BarChart data={hist} margin={{ top: 6, right: 6, bottom: 4, left: -8 }}>
                    <XAxis dataKey="label" tick={{ fontSize: 7, fill: '#889' }} interval={5} />
                    <YAxis tick={{ fontSize: 8, fill: '#889' }} width={28} />
                    <Tooltip
                      contentStyle={{ background: 'rgba(10,10,15,0.9)', border: '1px solid #283', borderRadius: 4, fontSize: 11 }}
                      labelStyle={{ color: '#9aa' }}
                      formatter={(value) => [Number(value), 'triangles']}
                    />
                    <ReferenceLine x={hist.find((d) => d.center >= 0)?.label} stroke="#556" strokeDasharray="2 2" />
                    <Bar dataKey="count" isAnimationActive={false}>
                      {hist.map((d, i) => (
                        <Cell key={i} fill={d.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
              <p style={{ fontSize: 10, color: '#667', margin: '2px 2px 0' }}>
                delta B - A per triangle (blue lower, red higher)
              </p>
            </>
          )}
        </>
      )}
    </div>
  )
}
