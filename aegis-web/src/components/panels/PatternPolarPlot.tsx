// aegis-web/src/components/panels/PatternPolarPlot.tsx
import { useMemo } from 'react'
import { InlineMath } from 'react-katex'

interface Props {
  data: Float32Array
  maxGainDbi: number
  dynamicRangeDb?: number
}

const SIZE = 140
const CX = SIZE / 2
const CY = SIZE / 2
const R_MAX = SIZE / 2 - 18

function dbToRadius(dbi: number, peakDbi: number, dynRange: number): number {
  const rel = dbi - peakDbi
  const clamped = Math.max(rel, -dynRange)
  return R_MAX * (1 + clamped / dynRange)
}

function polarPath(
  angles: number[],
  gains: number[],
  peakDbi: number,
  dynRange: number,
): string {
  const pts = angles.map((a, i) => {
    const r = dbToRadius(gains[i], peakDbi, dynRange)
    const x = CX + r * Math.sin(a)
    const y = CY - r * Math.cos(a)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return `M${pts.join('L')}Z`
}

function PolarGrid({ dynRange }: { dynRange: number }) {
  const rings = [0, -10, -20, -30].filter(d => d >= -dynRange)
  const spokes = Array.from({ length: 12 }, (_, i) => (i * 30 * Math.PI) / 180)
  return (
    <g>
      {rings.map(d => {
        const r = R_MAX * (1 + d / dynRange)
        return (
          <g key={d}>
            <circle cx={CX} cy={CY} r={r} fill="none" stroke="#555" strokeWidth={0.5}
              strokeDasharray={d === 0 ? 'none' : '2,2'} />
            <text x={CX + 2} y={CY - r - 1} fontSize={7} fill="#888" fontFamily="serif">
              {d} dB
            </text>
          </g>
        )
      })}
      {spokes.map((a, i) => {
        const x2 = CX + R_MAX * Math.sin(a)
        const y2 = CY - R_MAX * Math.cos(a)
        const lx = CX + (R_MAX + 8) * Math.sin(a)
        const ly = CY - (R_MAX + 8) * Math.cos(a)
        const deg = i * 30
        return (
          <g key={deg}>
            <line x1={CX} y1={CY} x2={x2} y2={y2} stroke="#444" strokeWidth={0.3} />
            <text x={lx} y={ly} fontSize={7} fill="#777" textAnchor="middle"
              dominantBaseline="central" fontFamily="serif">
              {deg}°
            </text>
          </g>
        )
      })}
    </g>
  )
}

export default function PatternPolarPlot({ data, maxGainDbi, dynamicRangeDb = 30 }: Props) {
  const { hPath, vPath } = useMemo(() => {
    const nAz = 360
    // H-plane: row 90 (elevation = 0°), all 360 azimuth cols
    const hGains: number[] = []
    const hAngles: number[] = []
    for (let az = 0; az < nAz; az++) {
      hGains.push(data[90 * nAz + az])
      const azDeg = az - 180
      hAngles.push((azDeg * Math.PI) / 180)
    }

    // V-plane: col 180 (azimuth = 0° boresight) for front, col 0 (azimuth = -180°) for back
    // Sweep monotonically 0 -> 2*PI so the SVG path traces cleanly
    const vGains: number[] = []
    const vAngles: number[] = []
    const boresightCol = 180
    const backCol = 0

    // Front half: zenith (row 180) -> nadir (row 0), plotAngle 0 -> PI
    for (let el = 180; el >= 0; el--) {
      const elDeg = el - 90
      const plotAngle = ((90 - elDeg) * Math.PI) / 180
      vGains.push(data[el * nAz + boresightCol])
      vAngles.push(plotAngle)
    }
    // Back half: nadir (row 0) -> zenith (row 180), plotAngle PI -> ~2*PI
    // Include zenith point so Z closure meets the front-half start cleanly
    for (let el = 1; el <= 180; el++) {
      const elDeg = el - 90
      const plotAngle = Math.PI + ((90 + elDeg) * Math.PI) / 180
      vGains.push(data[el * nAz + backCol])
      vAngles.push(plotAngle)
    }

    return {
      hPath: polarPath(hAngles, hGains, maxGainDbi, dynamicRangeDb),
      vPath: polarPath(vAngles, vGains, maxGainDbi, dynamicRangeDb),
    }
  }, [data, maxGainDbi, dynamicRangeDb])

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-3 justify-center">
        <div className="flex flex-col items-center">
          <span className="text-[10px] text-muted-foreground mb-0.5">
            <InlineMath math="G(\varphi)" /> <span className="text-[9px]">H-plane</span>
          </span>
          <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}
            className="bg-background/50 rounded border border-border/50">
            <PolarGrid dynRange={dynamicRangeDb} />
            <path d={hPath} fill="rgba(59,130,246,0.15)" stroke="#3b82f6" strokeWidth={1.2} />
          </svg>
        </div>
        <div className="flex flex-col items-center">
          <span className="text-[10px] text-muted-foreground mb-0.5">
            <InlineMath math="G(\theta)" /> <span className="text-[9px]">V-plane</span>
          </span>
          <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}
            className="bg-background/50 rounded border border-border/50">
            <PolarGrid dynRange={dynamicRangeDb} />
            <path d={vPath} fill="rgba(59,130,246,0.15)" stroke="#3b82f6" strokeWidth={1.2} />
          </svg>
        </div>
      </div>
      <p className="text-[10px] text-muted-foreground text-center font-serif">
        <InlineMath math={`G_{\\max} = ${maxGainDbi.toFixed(1)}\\;\\text{dBi}`} />
      </p>
    </div>
  )
}
