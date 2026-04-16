import { useRef, useEffect, useCallback } from 'react'
import type { HeatmapResult } from '@/api/client'
import { marginColor } from './utils'

// ---------------------------------------------------------------------------
// Compliance heatmap canvas (2D: frequency x power)
// ---------------------------------------------------------------------------

export function HeatmapCanvas({
  result,
  currentFreqGhz,
  currentPowerDbm,
  onCellClick,
}: {
  result: HeatmapResult
  currentFreqGhz: number
  currentPowerDbm: number
  onCellClick?: (freqGhz: number, powerDbm: number) => void
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const { n_freq, n_power, freq_ghz, power_dbm, margin_db } = result

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = canvas.width
    const H = canvas.height
    const ml = 40, mr = 10, mt = 10, mb = 28
    const pw = (W - ml - mr) / n_freq
    const ph = (H - mt - mb) / n_power

    ctx.clearRect(0, 0, W, H)

    // Draw heatmap cells
    for (let pi = 0; pi < n_power; pi++) {
      const row = margin_db[pi]
      for (let fi = 0; fi < n_freq; fi++) {
        const [r, g, b] = marginColor(row[fi])
        ctx.fillStyle = `rgb(${r},${g},${b})`
        // Y axis: power increases upward, so flip
        ctx.fillRect(ml + fi * pw, mt + (n_power - 1 - pi) * ph, Math.ceil(pw), Math.ceil(ph))
      }
    }

    // Draw compliance boundary (margin = 0 line)
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1.5
    ctx.beginPath()
    let started = false
    for (let fi = 0; fi < n_freq; fi++) {
      const pMaxDbm = result.p_max_dbm_per_freq[fi]
      if (!Number.isFinite(pMaxDbm)) continue
      const pMin = power_dbm[0]
      const pMax = power_dbm[n_power - 1]
      const yFrac = 1 - (pMaxDbm - pMin) / (pMax - pMin)
      if (yFrac < 0 || yFrac > 1) continue
      const x = ml + (fi + 0.5) * pw
      const y = mt + yFrac * (H - mt - mb)
      if (!started) { ctx.moveTo(x, y); started = true }
      else ctx.lineTo(x, y)
    }
    ctx.stroke()

    // Draw crosshairs for current position
    const fMin = freq_ghz[0], fMax = freq_ghz[n_freq - 1]
    const pMin = power_dbm[0], pMax = power_dbm[n_power - 1]
    const cx = ml + ((currentFreqGhz - fMin) / (fMax - fMin)) * (W - ml - mr)
    const cy = mt + (1 - (currentPowerDbm - pMin) / (pMax - pMin)) * (H - mt - mb)

    if (cx >= ml && cx <= W - mr && cy >= mt && cy <= H - mb) {
      ctx.strokeStyle = 'rgba(147,197,253,0.7)'
      ctx.lineWidth = 1
      ctx.setLineDash([3, 3])
      ctx.beginPath(); ctx.moveTo(cx, mt); ctx.lineTo(cx, H - mb); ctx.stroke()
      ctx.beginPath(); ctx.moveTo(ml, cy); ctx.lineTo(W - mr, cy); ctx.stroke()
      ctx.setLineDash([])
      ctx.fillStyle = '#93c5fd'
      ctx.beginPath(); ctx.arc(cx, cy, 3, 0, Math.PI * 2); ctx.fill()
    }

    // Axes
    ctx.fillStyle = '#888'
    ctx.font = '9px monospace'
    ctx.textAlign = 'center'
    // X axis: frequency labels
    const xTicks = 5
    for (let i = 0; i <= xTicks; i++) {
      const fi = Math.round((i / xTicks) * (n_freq - 1))
      const x = ml + (fi + 0.5) * pw
      ctx.fillText(freq_ghz[fi].toFixed(0), x, H - 4)
    }
    ctx.fillText('GHz', W - mr - 8, H - 4)
    // Y axis: power labels
    ctx.textAlign = 'right'
    const yTicks = 4
    for (let i = 0; i <= yTicks; i++) {
      const pi = Math.round((i / yTicks) * (n_power - 1))
      const y = mt + (n_power - 1 - pi) * ph + ph / 2
      ctx.fillText(power_dbm[pi].toFixed(0), ml - 4, y + 3)
    }
    ctx.save()
    ctx.translate(8, mt + (H - mt - mb) / 2)
    ctx.rotate(-Math.PI / 2)
    ctx.textAlign = 'center'
    ctx.fillText('dBm', 0, 0)
    ctx.restore()
  }, [result, n_freq, n_power, freq_ghz, power_dbm, margin_db, currentFreqGhz, currentPowerDbm])

  useEffect(() => { draw() }, [draw])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    const tip = tooltipRef.current
    if (!canvas || !tip) return
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const W = canvas.width, H = canvas.height
    const ml = 40, mr = 10, mt = 10, mb = 28
    const pw = (W - ml - mr) / n_freq
    const ph = (H - mt - mb) / n_power
    const fi = Math.floor((mx - ml) / pw)
    const pi = n_power - 1 - Math.floor((my - mt) / ph)
    if (fi < 0 || fi >= n_freq || pi < 0 || pi >= n_power) {
      tip.style.display = 'none'
      return
    }
    const m = margin_db[pi][fi]
    tip.style.display = 'block'
    tip.style.left = `${mx + 12}px`
    tip.style.top = `${my - 10}px`
    const clickHint = onCellClick ? '  (click to apply)' : ''
    tip.textContent = `${freq_ghz[fi].toFixed(1)} GHz, ${power_dbm[pi].toFixed(0)} dBm: ${m > 0 ? '+' : ''}${m.toFixed(1)} dB${clickHint}`
  }, [result, n_freq, n_power, freq_ghz, power_dbm, margin_db, onCellClick])

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onCellClick) return
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mx = (e.clientX - rect.left) * (canvas.width / rect.width)
    const my = (e.clientY - rect.top) * (canvas.height / rect.height)
    const W = canvas.width, H = canvas.height
    const ml = 40, mr = 10, mt = 10, mb = 28
    const pw = (W - ml - mr) / n_freq
    const ph = (H - mt - mb) / n_power
    const fi = Math.floor((mx - ml) / pw)
    const pi = n_power - 1 - Math.floor((my - mt) / ph)
    if (fi < 0 || fi >= n_freq || pi < 0 || pi >= n_power) return
    onCellClick(freq_ghz[fi], power_dbm[pi])
  }, [onCellClick, n_freq, n_power, freq_ghz, power_dbm])

  return (
    <div className="relative mt-2">
      <canvas
        ref={canvasRef}
        width={280}
        height={180}
        className="w-full rounded border border-border/30 cursor-crosshair"
        style={{ imageRendering: 'pixelated' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => { if (tooltipRef.current) tooltipRef.current.style.display = 'none' }}
        onClick={handleClick}
      />
      <div
        ref={tooltipRef}
        className="absolute hidden bg-black/85 border border-border/50 rounded px-2 py-1 text-[10px] font-mono text-foreground/90 pointer-events-none whitespace-nowrap z-10"
      />
    </div>
  )
}
