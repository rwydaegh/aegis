import type { Point } from './types'

// Clamp a pan offset so the zoomed image cannot leave the viewport.
export function clampPan(
  px: number,
  py: number,
  zoom: number,
  width: number,
  height: number,
): Point {
  const maxPanX = Math.max(0, (width * zoom - width) / 2)
  const maxPanY = Math.max(0, (height * zoom - height) / 2)
  return {
    x: Math.max(-maxPanX, Math.min(maxPanX, px)),
    y: Math.max(-maxPanY, Math.min(maxPanY, py)),
  }
}

// Convert a client (screen) point to a canvas coordinate, inverting zoom/pan.
export function clientToCanvas(
  container: HTMLDivElement | null,
  clientX: number,
  clientY: number,
  pan: Point,
  zoom: number,
  width: number,
  height: number,
): Point {
  if (!container) return { x: 0, y: 0 }
  const rect = container.getBoundingClientRect()
  const viewX = clientX - rect.left
  const viewY = clientY - rect.top
  // Invert the CSS transform: translate then scale
  const canvasX = (viewX - rect.width / 2 - pan.x) / zoom + width / 2
  const canvasY = (viewY - rect.height / 2 - pan.y) / zoom + height / 2
  return {
    x: Math.max(0, Math.min(width, canvasX)),
    y: Math.max(0, Math.min(height, canvasY)),
  }
}

// Compute the new pan when zoom is applied centered on a given cursor point.
export function panForCursorZoom(
  container: HTMLDivElement | null,
  clientX: number,
  clientY: number,
  pan: Point,
  prevZoom: number,
  nextZoom: number,
  width: number,
  height: number,
): Point {
  if (!container || nextZoom === prevZoom) return pan
  const rect = container.getBoundingClientRect()
  const cx = clientX - rect.left - rect.width / 2
  const cy = clientY - rect.top - rect.height / 2
  const scale = nextZoom / prevZoom
  return clampPan(
    pan.x * scale + cx * (1 - scale),
    pan.y * scale + cy * (1 - scale),
    nextZoom,
    width,
    height,
  )
}
