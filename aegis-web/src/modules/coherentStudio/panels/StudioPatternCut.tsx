import { useMemo } from 'react'
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
import { arrayFactorCut } from './studioArrayFactor'
import { FieldLabel } from './widgets'

/**
 * Antenna-pattern cut: the principal-plane array factor of the steered URA in dB.
 * The base station is an N x N uniform array at half-wavelength spacing pointed
 * broadside at the focus, so the cut is the Dirichlet-kernel pattern with a patch
 * element factor. Reports the half-power beamwidth and first sidelobe level. This
 * is the geometric array factor (the uniform-amplitude / MRT beam); the realised
 * ECBF beam is amplitude-tapered to dodge the body and differs.
 */
export default function StudioPatternCut() {
  const arrayN = useStudioStore((s) => s.arrayN)

  const cut = useMemo(() => arrayFactorCut(arrayN, 0.5, 361, true), [arrayN])

  return (
    <div>
      <FieldLabel title="Principal-plane array factor of the steered N x N uniform array, in dB relative to boresight. The geometric (uniform-amplitude) beam; the realised ECBF beam differs.">
        Array pattern cut
      </FieldLabel>
      <ResponsiveContainer width="100%" height={150}>
        <LineChart data={cut.points} margin={{ top: 8, right: 6, bottom: 4, left: -12 }}>
          <XAxis
            dataKey="angleDeg"
            type="number"
            domain={[-90, 90]}
            ticks={[-90, -45, 0, 45, 90]}
            tickFormatter={(v) => `${v}°`}
            tick={{ fontSize: 7, fill: '#889' }}
          />
          <YAxis
            domain={[cut.floorDb, 0]}
            ticks={[0, -10, -20, -30, -40]}
            tick={{ fontSize: 8, fill: '#889' }}
            width={28}
            tickFormatter={(v) => `${v}`}
          />
          <Tooltip
            contentStyle={{ background: 'rgba(10,10,15,0.9)', border: '1px solid #283', borderRadius: 4, fontSize: 11 }}
            labelStyle={{ color: '#9aa' }}
            labelFormatter={(v) => `${Number(v).toFixed(0)}° off boresight`}
            formatter={(value) => [`${Number(value).toFixed(1)} dB`, 'gain']}
          />
          <ReferenceLine y={-3} stroke="#445" strokeDasharray="2 2" />
          {isFinite(cut.sidelobeDb) && (
            <ReferenceLine
              y={cut.sidelobeDb}
              stroke="#a86"
              strokeDasharray="2 2"
              label={{ value: 'SLL', fontSize: 8, fill: '#a86', position: 'insideBottomRight' }}
            />
          )}
          <Line type="monotone" dataKey="db" stroke="#9cf" strokeWidth={1.4} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#9aa', marginTop: 2 }}>
        <span title="Number of elements per array axis.">{arrayN}x{arrayN} URA</span>
        <span title="Half-power (-3 dB) beamwidth.">HPBW {isFinite(cut.hpbwDeg) ? `${cut.hpbwDeg.toFixed(1)}°` : '--'}</span>
        <span title="First sidelobe level relative to the main lobe.">
          SLL {isFinite(cut.sidelobeDb) ? `${cut.sidelobeDb.toFixed(1)} dB` : '--'}
        </span>
      </div>
    </div>
  )
}
