import { STROKE_COLOR, STROKE_WIDTH, type Point, type Stroke } from './types'

// Apply stroke styling used by every draw path (base canvas, composite canvas).
export function applyStrokeStyle(
  ctx: CanvasRenderingContext2D,
  lineWidth: number = STROKE_WIDTH,
): void {
  ctx.strokeStyle = STROKE_COLOR
  ctx.lineWidth = lineWidth
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
}

// Draw the given stroke onto a canvas context, transforming each point.
export function drawStroke(
  ctx: CanvasRenderingContext2D,
  stroke: Stroke,
  transform: (p: Point) => Point = p => p,
): void {
  if (stroke.points.length < 2) return
  const first = transform(stroke.points[0])
  ctx.beginPath()
  ctx.moveTo(first.x, first.y)
  for (let i = 1; i < stroke.points.length; i++) {
    const p = transform(stroke.points[i])
    ctx.lineTo(p.x, p.y)
  }
  ctx.stroke()
}

// Redraw all committed strokes on the draw canvas at native resolution.
export function redrawAllStrokes(
  canvas: HTMLCanvasElement | null,
  strokes: Stroke[],
  width: number,
  height: number,
): void {
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, width, height)
  applyStrokeStyle(ctx)
  for (const stroke of strokes) drawStroke(ctx, stroke)
}

// Incrementally draw the last segment of the in-progress stroke (for live feedback).
export function drawIncrementalSegment(
  canvas: HTMLCanvasElement | null,
  points: Point[],
): void {
  if (!canvas || points.length < 2) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  applyStrokeStyle(ctx)
  const prev = points[points.length - 2]
  const curr = points[points.length - 1]
  ctx.beginPath()
  ctx.moveTo(prev.x, prev.y)
  ctx.lineTo(curr.x, curr.y)
  ctx.stroke()
}
