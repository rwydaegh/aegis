import { applyStrokeStyle, drawStroke } from './drawing'
import { STROKE_WIDTH, type Point, type Stroke } from './types'

interface VisibleRegion {
  // Source (in original screenshot pixel coords)
  sx: number
  sy: number
  sw: number
  sh: number
  // Output dimensions (integers)
  outW: number
  outH: number
  // Offset in display coords (for re-projecting strokes)
  offsetX: number
  offsetY: number
  scaleX: number
  scaleY: number
}

// Compute the visible region in full-resolution coordinates from the current zoom/pan.
export function computeVisibleRegion(
  naturalWidth: number,
  naturalHeight: number,
  displayWidth: number,
  displayHeight: number,
  zoom: number,
  pan: Point,
): VisibleRegion {
  const scaleX = naturalWidth / displayWidth
  const scaleY = naturalHeight / displayHeight
  const visW = displayWidth / zoom
  const visH = displayHeight / zoom
  const cx = displayWidth / 2 - pan.x / zoom
  const cy = displayHeight / 2 - pan.y / zoom
  const offsetX = Math.max(0, cx - visW / 2)
  const offsetY = Math.max(0, cy - visH / 2)
  const sx = offsetX * scaleX
  const sy = offsetY * scaleY
  const sw = Math.min(visW, displayWidth - (cx - visW / 2)) * scaleX
  const sh = Math.min(visH, displayHeight - (cy - visH / 2)) * scaleY
  return {
    sx,
    sy,
    sw,
    sh,
    outW: Math.round(sw),
    outH: Math.round(sh),
    offsetX,
    offsetY,
    scaleX,
    scaleY,
  }
}

// Load an image from a URL as a promise.
function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('Failed to load screenshot for export'))
    img.src = url
  })
}

// Render a composite <canvas> (screenshot + strokes) and resolve it as a PNG blob.
function canvasToPngBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      blob => {
        if (blob) resolve(blob)
        else reject(new Error('Failed to export canvas'))
      },
      'image/png',
    )
  })
}

interface CompositeOptions {
  screenshotUrl: string
  width: number
  height: number
  zoom: number
  pan: Point
  strokes: Stroke[]
}

// Compose the visible portion of the screenshot with annotation strokes at full resolution.
export async function buildCompositeImage(opts: CompositeOptions): Promise<Blob> {
  const { screenshotUrl, width, height, zoom, pan, strokes } = opts
  const img = await loadImage(screenshotUrl)
  const region = computeVisibleRegion(img.naturalWidth, img.naturalHeight, width, height, zoom, pan)

  const composite = document.createElement('canvas')
  composite.width = region.outW
  composite.height = region.outH
  const ctx = composite.getContext('2d')
  if (!ctx) throw new Error('Cannot get canvas context')

  // Draw the visible portion of the high-res screenshot
  ctx.drawImage(img, region.sx, region.sy, region.sw, region.sh, 0, 0, region.outW, region.outH)

  // Draw annotations scaled to match
  applyStrokeStyle(ctx, STROKE_WIDTH * Math.max(region.scaleX, region.scaleY))
  const transform = (p: Point): Point => ({
    x: (p.x - region.offsetX) * region.scaleX,
    y: (p.y - region.offsetY) * region.scaleY,
  })
  for (const stroke of strokes) drawStroke(ctx, stroke, transform)

  return canvasToPngBlob(composite)
}
