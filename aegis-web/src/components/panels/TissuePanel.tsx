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
  const h = 48
  const pad = 2
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  const fMin = freqs[0]
  const fMax = freqs[freqs.length - 1]
  const fRange = fMax - fMin || 1

  const points = data.map((v, i) => {
    const x = pad + ((freqs[i] - fMin) / fRange) * (w - 2 * pad)
    const y = h - pad - ((v - min) / range) * (h - 2 * pad)
    return `${x},${y}`
  }).join(' ')

  // Current frequency marker
  const curX = pad + ((currentFreqHz - fMin) / fRange) * (w - 2 * pad)
  const curIdx = freqs.reduce((best, f, i) => Math.abs(f - currentFreqHz) < Math.abs(freqs[best] - currentFreqHz) ? i : best, 0)
  const curVal = data[curIdx]

  return (
    <div className="mb-2">
      <div className="flex justify-between text-[10px] text-muted-foreground mb-0.5">
        <span>{label}</span>
        <span className="tabular-nums">{curVal?.toFixed(2)} {unit}</span>
      </div>
      <svg width={w} height={h} className="block">
        <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
        {curX >= pad && curX <= w - pad && (
          <>
            <line x1={curX} y1={0} x2={curX} y2={h} stroke="#fff" strokeWidth={0.5} strokeDasharray="2,2" opacity={0.4} />
            <circle cx={curX} cy={h - pad - ((curVal - min) / range) * (h - 2 * pad)} r={2.5} fill={color} />
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
      .catch(() => {})
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
