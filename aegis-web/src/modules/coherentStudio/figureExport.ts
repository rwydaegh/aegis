import * as THREE from 'three'
import { colormapRgb } from './scene/studioHelpers'

// Figure export: re-render the WebGL scene at a target resolution (so the PNG is
// print-crisp and independent of the on-screen window), then optionally composite
// the colour bars into a right-hand gutter with a 2D canvas pass. Kept dependency
// free (no html-to-image): the bars are drawn from the live scale data, so they
// scale with the export resolution and stay vector-crisp at any size.

/** One colour bar to draw into the export, distilled from a ResolvedScale. */
export interface ColorbarSpec {
  /** Short label above the bar, e.g. "S_ab" or "field |E|". */
  title: string
  /** Unit / scale note under the title, e.g. "W m^-2 (abs.)" or "dB". */
  unit?: string
  vmin: number
  vmax: number
  colormap: string
  logMode: boolean
  dynamicRangeDb: number
}

/** Compact numeric label for a colour-bar endpoint. */
export function formatTick(v: number): string {
  if (!Number.isFinite(v)) return ''
  if (v === 0) return '0'
  const a = Math.abs(v)
  if (a >= 1e4 || a < 1e-2) return v.toExponential(1)
  if (a >= 100) return v.toFixed(0)
  if (a >= 1) return v.toFixed(1)
  return v.toFixed(2)
}

/**
 * Compute the export canvas size and per-bar gutter width.
 * Preserves the scene aspect; long edge becomes longEdgePx. Each colour bar adds
 * a gutter column sized to the scene height (so labels stay legible).
 */
export function exportLayout(
  sceneW: number,
  sceneH: number,
  longEdgePx: number,
  nbars: number,
): { imgW: number; imgH: number; gutter: number; totalW: number } {
  const aspect = sceneW / sceneH
  let imgW: number
  let imgH: number
  if (aspect >= 1) {
    imgW = longEdgePx
    imgH = Math.round(longEdgePx / aspect)
  } else {
    imgH = longEdgePx
    imgW = Math.round(longEdgePx * aspect)
  }
  // A gutter wide enough for the bar plus its labels, ~16% of scene height each.
  const gutter = nbars > 0 ? Math.round(imgH * 0.17) : 0
  return { imgW, imgH, gutter, totalW: imgW + gutter * nbars }
}

/** Draw one vertical colour bar (with frame, title, and end labels) at (x, y). */
export function drawColorbar(
  ctx: CanvasRenderingContext2D,
  x: number,
  gutterW: number,
  imgH: number,
  spec: ColorbarSpec,
): void {
  const barW = Math.round(gutterW * 0.24)
  const barH = Math.round(imgH * 0.6)
  const barX = Math.round(x + gutterW * 0.16)
  const barY = Math.round(imgH * 0.2)
  const fontPx = Math.max(9, Math.round(imgH * 0.02))

  // Gradient: sample top (vmax) to bottom (vmin) so the hottest value is up top.
  const n = 128
  for (let i = 0; i < n; i++) {
    const t = 1 - i / (n - 1)
    const [r, g, b] = colormapRgb(spec.colormap, t)
    ctx.fillStyle = `rgb(${r},${g},${b})`
    ctx.fillRect(barX, barY + Math.floor((i * barH) / n), barW, Math.ceil(barH / n) + 1)
  }
  ctx.strokeStyle = '#222'
  ctx.lineWidth = Math.max(1, Math.round(imgH * 0.0015))
  ctx.strokeRect(barX, barY, barW, barH)

  ctx.fillStyle = '#1a1a1a'
  ctx.textBaseline = 'middle'
  ctx.textAlign = 'left'
  const labelX = barX + barW + Math.round(gutterW * 0.06)
  // Endpoints: log mode reads as dB below peak; linear reads the raw range.
  const topLabel = spec.logMode ? '0 dB' : formatTick(spec.vmax)
  const botLabel = spec.logMode ? `-${spec.dynamicRangeDb.toFixed(0)} dB` : formatTick(spec.vmin)
  ctx.font = `${fontPx}px serif`
  ctx.fillText(topLabel, labelX, barY + fontPx * 0.5)
  ctx.fillText(botLabel, labelX, barY + barH - fontPx * 0.5)

  // Title above the bar.
  ctx.textAlign = 'left'
  ctx.font = `${Math.round(fontPx * 1.1)}px serif`
  ctx.fillText(spec.title, barX, barY - fontPx * 1.6)
  if (spec.unit) {
    ctx.font = `${Math.round(fontPx * 0.85)}px serif`
    ctx.fillStyle = '#555'
    ctx.fillText(spec.unit, barX, barY - fontPx * 0.5)
  }
}

/**
 * Re-render the scene at the target long edge, copy the high-res frame onto a 2D
 * canvas, draw any colour bars beside it, and return a PNG blob.
 *
 * The high-res frame is copied with drawImage straight from the WebGL canvas
 * (synchronous, so it captures the frame before the on-screen render loop repaints
 * at window size, and avoids data: URLs that the page CSP blocks). The renderer is
 * restored to its on-screen size afterwards.
 */
export async function captureComposite(
  gl: THREE.WebGLRenderer,
  scene: THREE.Scene,
  camera: THREE.PerspectiveCamera,
  longEdgePx: number,
  bars: ColorbarSpec[],
): Promise<Blob> {
  const glCanvas = gl.domElement
  const cssW = glCanvas.clientWidth || glCanvas.width
  const cssH = glCanvas.clientHeight || glCanvas.height
  const { imgW, imgH, gutter, totalW } = exportLayout(cssW, cssH, longEdgePx, bars.length)

  const prevDpr = gl.getPixelRatio()
  const prevAspect = camera.aspect

  const out = document.createElement('canvas')
  out.width = totalW
  out.height = imgH
  const ctx = out.getContext('2d')
  if (!ctx) throw new Error('2D context unavailable for figure export')

  gl.setPixelRatio(1)
  gl.setSize(imgW, imgH, false)
  camera.aspect = imgW / imgH
  camera.updateProjectionMatrix()
  gl.render(scene, camera)
  // Synchronous copy of the high-res frame before anything repaints it.
  ctx.drawImage(glCanvas, 0, 0, imgW, imgH)

  // Restore on-screen state; the always-on render loop repaints next frame.
  gl.setPixelRatio(prevDpr)
  gl.setSize(cssW, cssH, false)
  camera.aspect = prevAspect
  camera.updateProjectionMatrix()
  gl.render(scene, camera)

  bars.forEach((bar, i) => drawColorbar(ctx, imgW + gutter * i, gutter, imgH, bar))
  return await new Promise<Blob>((resolve, reject) =>
    out.toBlob((b) => (b ? resolve(b) : reject(new Error('toBlob failed'))), 'image/png'),
  )
}

/** Trigger a browser download of a blob. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
