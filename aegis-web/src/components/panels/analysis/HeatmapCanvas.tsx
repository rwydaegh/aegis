import { useRef, useEffect, useCallback } from 'react'
import type { HeatmapResult } from '@/api/client'
import { marginColor } from './utils'

// ---------------------------------------------------------------------------
// Compliance heatmap canvas (2D: frequency x power)
// ---------------------------------------------------------------------------

interface CanvasLayout { W: number; H: number; ml: number; mr: number; mt: number; mb: number; pw: number; ph: number }

function getCanvasLayout(canvas: HTMLCanvasElement, n_freq: number, n_power: number): CanvasLayout {
  const W = canvas.width
  const H = canvas.height
  const ml = 40, mr = 10, mt = 10, mb = 28
  return { W, H, ml, mr, mt, mb, pw: (W - ml - mr) / n_freq, ph: (H - mt - mb) / n_power }
}

function hitTestCell(
  mx: number, my: number,
  l: CanvasLayout,
  n_freq: number, n_power: number,
): { fi: number; pi: number } | null {
  const fi = Math.floor((mx - l.ml) / l.pw)
  const pi = n_power - 1 - Math.floor((my - l.mt) / l.ph)
  if (fi < 0 || fi >= n_freq || pi < 0 || pi >= n_power) return null
  return { fi, pi }
}

function drawCells(ctx: CanvasRenderingContext2D, l: CanvasLayout, n_freq: number, n_power: number, margin_db: number[][]): void {
  for (let pi = 0; pi < n_power; pi++) {
    const row = margin_db[pi]
    for (let fi = 0; fi < n_freq; fi++) {
      const [r, g, b] = marginColor(row[fi])
      ctx.fillStyle = `rgb(${r},${g},${b})`
      ctx.fillRect(l.ml + fi * l.pw, l.mt + (n_power - 1 - pi) * l.ph, Math.ceil(l.pw), Math.ceil(l.ph))
    }
  }
}

function drawComplianceBoundary(
  ctx: CanvasRenderingContext2D,
  l: CanvasLayout,
  n_freq: number,
  n_power: number,
  power_dbm: number[],
  p_max_dbm_per_freq: number[],
): void {
  ctx.strokeStyle = '#ffffff'
  ctx.lineWidth = 1.5
  ctx.beginPath()
  let started = false
  const pMin = power_dbm[0]
  const pMax = power_dbm[n_power - 1]
  for (let fi = 0; fi < n_freq; fi++) {
    const pMaxDbm = p_max_dbm_per_freq[fi]
    if (!Number.isFinite(pMaxDbm)) continue
    const yFrac = 1 - (pMaxDbm - pMin) / (pMax - pMin)
    if (yFrac < 0 || yFrac > 1) continue
    const x = l.ml + (fi + 0.5) * l.pw
    const y = l.mt + yFrac * (l.H - l.mt - l.mb)
    if (!started) { ctx.moveTo(x, y); started = true }
    else ctx.lineTo(x, y)
  }
  ctx.stroke()
}

function drawCrosshairs(
  ctx: CanvasRenderingContext2D,
  l: CanvasLayout,
  freq_ghz: number[],
  power_dbm: number[],
  n_freq: number,
  n_power: number,
  currentFreqGhz: number,
  currentPowerDbm: number,
): void {
  const fMin = freq_ghz[0], fMax = freq_ghz[n_freq - 1]
  const pMin = power_dbm[0], pMax = power_dbm[n_power - 1]
  const cx = l.ml + ((currentFreqGhz - fMin) / (fMax - fMin)) * (l.W - l.ml - l.mr)
  const cy = l.mt + (1 - (currentPowerDbm - pMin) / (pMax - pMin)) * (l.H - l.mt - l.mb)
  if (cx < l.ml || cx > l.W - l.mr || cy < l.mt || cy > l.H - l.mb) return

  ctx.strokeStyle = 'rgba(147,197,253,0.7)'
  ctx.lineWidth = 1
  ctx.setLineDash([3, 3])
  ctx.beginPath(); ctx.moveTo(cx, l.mt); ctx.lineTo(cx, l.H - l.mb); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(l.ml, cy); ctx.lineTo(l.W - l.mr, cy); ctx.stroke()
  ctx.setLineDash([])
  ctx.fillStyle = '#93c5fd'
  ctx.beginPath(); ctx.arc(cx, cy, 3, 0, Math.PI * 2); ctx.fill()
}

function drawAxes(
  ctx: CanvasRenderingContext2D,
  l: CanvasLayout,
  freq_ghz: number[],
  power_dbm: number[],
  n_freq: number,
  n_power: number,
): void {
  ctx.fillStyle = '#888'
  ctx.font = '9px monospace'
  ctx.textAlign = 'center'
  const xTicks = 5
  for (let i = 0; i <= xTicks; i++) {
    const fi = Math.round((i / xTicks) * (n_freq - 1))
    ctx.fillText(freq_ghz[fi].toFixed(0), l.ml + (fi + 0.5) * l.pw, l.H - 4)
  }
  ctx.fillText('GHz', l.W - l.mr - 8, l.H - 4)

  ctx.textAlign = 'right'
  const yTicks = 4
  for (let i = 0; i <= yTicks; i++) {
    const pi = Math.round((i / yTicks) * (n_power - 1))
    const y = l.mt + (n_power - 1 - pi) * l.ph + l.ph / 2
    ctx.fillText(power_dbm[pi].toFixed(0), l.ml - 4, y + 3)
  }
  ctx.save()
  ctx.translate(8, l.mt + (l.H - l.mt - l.mb) / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.textAlign = 'center'
  ctx.fillText('dBm', 0, 0)
  ctx.restore()
}

// ---------------------------------------------------------------------------
// Component
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
    const l = getCanvasLayout(canvas, n_freq, n_power)
    ctx.clearRect(0, 0, l.W, l.H)
    drawCells(ctx, l, n_freq, n_power, margin_db)
    drawComplianceBoundary(ctx, l, n_freq, n_power, power_dbm, result.p_max_dbm_per_freq)
    drawCrosshairs(ctx, l, freq_ghz, power_dbm, n_freq, n_power, currentFreqGhz, currentPowerDbm)
    drawAxes(ctx, l, freq_ghz, power_dbm, n_freq, n_power)
  }, [result, n_freq, n_power, freq_ghz, power_dbm, margin_db, currentFreqGhz, currentPowerDbm])

  useEffect(() => { draw() }, [draw])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    const tip = tooltipRef.current
    if (!canvas || !tip) return
    const rect = canvas.getBoundingClientRect()
    const cssX = e.clientX - rect.left
    const cssY = e.clientY - rect.top
    const mx = cssX * (canvas.width / rect.width)
    const my = cssY * (canvas.height / rect.height)
    const l = getCanvasLayout(canvas, n_freq, n_power)
    const hit = hitTestCell(mx, my, l, n_freq, n_power)
    if (!hit) { tip.style.display = 'none'; return }
    const { fi, pi } = hit
    const m = margin_db[pi][fi]
    tip.style.display = 'block'
    tip.style.left = `${cssX + 12}px`
    tip.style.top = `${cssY - 10}px`
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
    const l = getCanvasLayout(canvas, n_freq, n_power)
    const hit = hitTestCell(mx, my, l, n_freq, n_power)
    if (!hit) return
    onCellClick(freq_ghz[hit.fi], power_dbm[hit.pi])
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
