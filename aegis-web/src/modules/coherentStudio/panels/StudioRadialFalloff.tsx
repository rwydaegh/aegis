import { useMemo } from 'react'
import {
  Area,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useStudioStore } from '../store'
import { radialProfile } from './studioRadial'
import { FieldLabel } from './widgets'

function fmt(v: number): string {
  if (!isFinite(v)) return '--'
  const a = Math.abs(v)
  if (a !== 0 && (a < 1e-2 || a >= 1e4)) return v.toExponential(1)
  return v.toPrecision(3)
}

/** Radius in metres -> a compact cm / m label for the distance axis. */
function fmtRadius(r: number): string {
  if (r < 0.1) return `${Math.round(r * 1000)}mm`
  if (r < 1) return `${Math.round(r * 100)}cm`
  return `${r.toFixed(2)}m`
}

/**
 * Radial falloff of the reconstructed field around the hotspot: median value vs
 * distance from the field peak, with the 25..75 inter-quartile band shaded and a
 * "reliable radius" cutoff beyond which the cubic sample box no longer fully
 * surrounds the focus. A faithful port of the paper fork's
 * plot_radial_probability_density_function, computed client-side from the field
 * volume already in the store. Needs the 3D field volume to be enabled.
 */
export default function StudioRadialFalloff() {
  const volume = useStudioStore((s) => s.volumeResult)
  const showVolume = useStudioStore((s) => s.showVolume)

  const data = useMemo(() => {
    if (!volume || volume.scalar.length === 0) return null
    const prof = radialProfile(
      { scalar: volume.scalar, shape: volume.shape, origin: volume.origin, spacing: volume.spacing },
      volume.peakXyz,
      36,
    )
    if (prof.bins.length < 2) return null
    // -3 dB radius: where the median first drops below half the peak median.
    const peakMedian = prof.bins[0].median
    const half = 0.5 * peakMedian
    let halfRadius = NaN
    for (let i = 1; i < prof.bins.length; i++) {
      if (prof.bins[i].median <= half) {
        const a = prof.bins[i - 1]
        const b = prof.bins[i]
        const t = (a.median - half) / Math.max(a.median - b.median, 1e-30)
        halfRadius = a.r + t * (b.r - a.r)
        break
      }
    }
    return {
      bins: prof.bins,
      reliableRadius: prof.reliableRadius,
      halfRadius,
      units: volume.units || 'W/m^2',
    }
  }, [volume])

  if (!showVolume) {
    return (
      <span style={{ fontSize: 10, color: '#667' }}>
        Enable the 3D field volume to chart the radial falloff.
      </span>
    )
  }
  if (!data) {
    return <span style={{ fontSize: 10, color: '#667' }}>No field volume yet.</span>
  }

  return (
    <div>
      <FieldLabel title="How the field decays with distance from the hotspot. The line is the median over each spherical shell; the band is the 25th..75th percentile spread. Past the dashed reliable radius the sample box no longer fully surrounds the focus.">
        Radial falloff
      </FieldLabel>
      <ResponsiveContainer width="100%" height={150}>
        <ComposedChart data={data.bins} margin={{ top: 6, right: 6, bottom: 4, left: -8 }}>
          <XAxis
            dataKey="r"
            type="number"
            domain={[0, 'dataMax']}
            tickFormatter={fmtRadius}
            tick={{ fontSize: 7, fill: '#889' }}
          />
          <YAxis tick={{ fontSize: 8, fill: '#889' }} width={34} tickFormatter={(v) => fmt(Number(v))} />
          <Tooltip
            contentStyle={{ background: 'rgba(10,10,15,0.9)', border: '1px solid #283', borderRadius: 4, fontSize: 11 }}
            labelStyle={{ color: '#9aa' }}
            labelFormatter={(v) => `r = ${fmtRadius(Number(v))}`}
            formatter={(value, name) => [fmt(Number(value)), name === 'median' ? 'median' : name]}
          />
          {/* IQR band: an invisible p25 base with the (p75 - p25) band stacked on top. */}
          <Area
            type="monotone"
            dataKey="p25"
            stackId="iqr"
            stroke="none"
            fill="none"
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="band"
            stackId="iqr"
            stroke="none"
            fill="#5a7fb0"
            fillOpacity={0.28}
            isAnimationActive={false}
          />
          <Line type="monotone" dataKey="median" stroke="#9cf" strokeWidth={1.6} dot={false} isAnimationActive={false} />
          {data.reliableRadius > 0 && (
            <ReferenceLine
              x={data.reliableRadius}
              stroke="#888"
              strokeDasharray="3 3"
              label={{ value: 'reliable', fontSize: 8, fill: '#888', position: 'insideTopRight' }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#9aa', marginTop: 2 }}>
        <span title="Radius at which the median field drops to half its peak.">
          half-peak {isFinite(data.halfRadius) ? fmtRadius(data.halfRadius) : '--'}
        </span>
        <span title="Largest radius fully enclosed by the sample box.">
          reliable to {fmtRadius(data.reliableRadius)}
        </span>
      </div>
      <p style={{ fontSize: 10, color: '#667', margin: '4px 2px 0' }}>
        median {data.units} vs distance from the field peak
      </p>
    </div>
  )
}
