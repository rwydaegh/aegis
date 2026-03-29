import { useEffect, useState } from 'react'
import { useSimulationStore } from '@/stores/simulation'
import { fetchTissueSpectrum } from '@/api/client'
import type { TissueSpectrum } from '@/api/types'

/** Tiny SVG sparkline for a data series. */
function Sparkline({ data, freqs, currentFreqHz, color, label, unit }: {
  data: number[]
  freqs: number[]
  currentFreqHz: number
  color: string
  label: string
  unit: string
}) {
  if (data.length === 0) return null

  const w = 260
  const h = 56
  const padL = 36  // space for y-axis labels
  const padR = 4
  const padT = 4
  const padB = 4
  const plotW = w - padL - padR
  const plotH = h - padT - padB

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  // Log scale for frequency axis
  const logFreqs = freqs.map(f => Math.log10(f))
  const logMin = logFreqs[0]
  const logMax = logFreqs[logFreqs.length - 1]
  const logRange = logMax - logMin || 1

  const toX = (logF: number) => padL + ((logF - logMin) / logRange) * plotW
  const toY = (v: number) => h - padB - ((v - min) / range) * plotH

  const points = data.map((v, i) => `${toX(logFreqs[i])},${toY(v)}`).join(' ')

  // Current frequency marker
  const logCur = Math.log10(currentFreqHz)
  const curX = toX(logCur)
  const curIdx = freqs.reduce((best, f, i) =>
    Math.abs(f - currentFreqHz) < Math.abs(freqs[best] - currentFreqHz) ? i : best, 0)
  const curVal = data[curIdx]
  const curY = toY(curVal)

  // Grid lines (3 horizontal)
  const gridLines = [0.25, 0.5, 0.75].map(frac => {
    const val = min + frac * range
    const y = toY(val)
    return { y, val }
  })

  // Smart number formatting
  const fmt = (v: number) => {
    if (Math.abs(v) >= 100) return v.toFixed(0)
    if (Math.abs(v) >= 10) return v.toFixed(1)
    if (Math.abs(v) >= 1) return v.toFixed(2)
    return v.toPrecision(2)
  }

  return (
    <div className="mb-2">
      <div className="flex justify-between text-[10px] text-muted-foreground mb-0.5">
        <span>{label}</span>
        <span className="tabular-nums font-medium text-foreground">{fmt(curVal)} {unit}</span>
      </div>
      <svg width={w} height={h} className="block">
        {/* Y-axis labels */}
        <text x={padL - 3} y={padT + 3} textAnchor="end" fontSize={7} fill="rgba(255,255,255,0.3)">{fmt(max)}</text>
        <text x={padL - 3} y={h - padB} textAnchor="end" fontSize={7} fill="rgba(255,255,255,0.3)">{fmt(min)}</text>

        {/* Horizontal grid lines */}
        {gridLines.map(({ y }, i) => (
          <line key={i} x1={padL} y1={y} x2={w - padR} y2={y}
            stroke="rgba(255,255,255,0.06)" strokeWidth={0.5} />
        ))}

        {/* Plot area border (bottom) */}
        <line x1={padL} y1={h - padB} x2={w - padR} y2={h - padB}
          stroke="rgba(255,255,255,0.1)" strokeWidth={0.5} />

        {/* Data line */}
        <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" opacity={0.8} />

        {/* Current frequency marker */}
        {curX >= padL && curX <= w - padR && (
          <>
            <line x1={curX} y1={padT} x2={curX} y2={h - padB}
              stroke="rgba(255,255,255,0.3)" strokeWidth={0.5} strokeDasharray="2,2" />
            <circle cx={curX} cy={curY} r={3.5} fill={color} stroke="rgba(0,0,0,0.5)" strokeWidth={1} />
          </>
        )}
      </svg>
    </div>
  )
}

export default function TissuePanel() {
  const freqGhz = useSimulationStore(s => s.freqGhz)
  const skinModel = useSimulationStore(s => s.skinModel)
  const [spectrum, setSpectrum] = useState<TissueSpectrum | null>(null)

  useEffect(() => {
    fetchTissueSpectrum('Skin', 1e9, 100e9, 100)
      .then(setSpectrum)
      .catch(() => { /* tissue spectrum is supplementary, not critical */ })
  }, [skinModel])

  if (!spectrum) return null

  const currentFreqHz = freqGhz * 1e9

  return (
    <div>
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        Tissue dielectric properties vs frequency. Vertical line = current operating frequency.
      </p>
      <Sparkline
        data={spectrum.eps_r}
        freqs={spectrum.freqs_hz}
        currentFreqHz={currentFreqHz}
        color="#60a5fa"
        label="Relative permittivity"
        unit=""
      />
      <Sparkline
        data={spectrum.sigma}
        freqs={spectrum.freqs_hz}
        currentFreqHz={currentFreqHz}
        color="#f59e0b"
        label="Conductivity"
        unit="S/m"
      />
      <Sparkline
        data={spectrum.T0}
        freqs={spectrum.freqs_hz}
        currentFreqHz={currentFreqHz}
        color="#4ade80"
        label="Transmission coeff T₀"
        unit=""
      />
      <div className="flex justify-between text-[10px] text-muted-foreground/40 mt-1">
        <span>{(spectrum.freqs_hz[0] / 1e9).toFixed(0)} GHz</span>
        <span>{(spectrum.freqs_hz[spectrum.freqs_hz.length - 1] / 1e9).toFixed(0)} GHz</span>
      </div>
    </div>
  )
}
