import { useCallback, useRef, useState, type RefObject } from 'react'
import { drawIncrementalSegment, redrawAllStrokes } from './drawing'
import { clampPan, clientToCanvas } from './viewport'
import type { Point, Stroke } from './types'

interface UsePointerHandlersOpts {
  width: number
  height: number
  zoom: number
  pan: Point
  setPan: (p: Point | ((prev: Point) => Point)) => void
  containerRef: RefObject<HTMLDivElement | null>
  drawCanvasRef: RefObject<HTMLCanvasElement | null>
  spaceHeld: boolean
}

interface PointerHandlersApi {
  strokesRef: React.MutableRefObject<Stroke[]>
  strokeCount: number
  isPanning: () => boolean
  onPointerDown: (e: React.PointerEvent) => void
  onPointerMove: (e: React.PointerEvent) => void
  onPointerUp: () => void
  undo: () => void
  clear: () => void
}

export function usePointerHandlers(opts: UsePointerHandlersOpts): PointerHandlersApi {
  const { width, height, zoom, pan, setPan, containerRef, drawCanvasRef, spaceHeld } = opts

  const strokesRef = useRef<Stroke[]>([])
  const currentStrokeRef = useRef<Stroke | null>(null)
  const isDrawingRef = useRef(false)
  const isPanningRef = useRef(false)
  const panStartRef = useRef<Point>({ x: 0, y: 0 })
  const [strokeCount, setStrokeCount] = useState(0)

  const startPan = useCallback((e: React.PointerEvent) => {
    isPanningRef.current = true
    panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
    ;(e.target as Element).setPointerCapture(e.pointerId)
  }, [pan])

  const startDraw = useCallback((e: React.PointerEvent) => {
    isDrawingRef.current = true
    const point = clientToCanvas(containerRef.current, e.clientX, e.clientY, pan, zoom, width, height)
    currentStrokeRef.current = { points: [point] }
    ;(e.target as Element).setPointerCapture(e.pointerId)
  }, [containerRef, pan, zoom, width, height])

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (spaceHeld || e.button === 1) startPan(e)
    else startDraw(e)
  }, [spaceHeld, startPan, startDraw])

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (isPanningRef.current) {
      setPan(clampPan(
        e.clientX - panStartRef.current.x,
        e.clientY - panStartRef.current.y,
        zoom, width, height,
      ))
      return
    }
    if (!isDrawingRef.current || !currentStrokeRef.current) return
    const point = clientToCanvas(containerRef.current, e.clientX, e.clientY, pan, zoom, width, height)
    currentStrokeRef.current.points.push(point)
    drawIncrementalSegment(drawCanvasRef.current, currentStrokeRef.current.points)
  }, [containerRef, drawCanvasRef, pan, setPan, zoom, width, height])

  const onPointerUp = useCallback(() => {
    if (isPanningRef.current) {
      isPanningRef.current = false
      return
    }
    const stroke = currentStrokeRef.current
    if (stroke && stroke.points.length > 1) {
      strokesRef.current.push(stroke)
      setStrokeCount(strokesRef.current.length)
    }
    currentStrokeRef.current = null
    isDrawingRef.current = false
  }, [])

  const redraw = useCallback(() => {
    redrawAllStrokes(drawCanvasRef.current, strokesRef.current, width, height)
  }, [drawCanvasRef, width, height])

  const undo = useCallback(() => {
    strokesRef.current.pop()
    setStrokeCount(strokesRef.current.length)
    redraw()
  }, [redraw])

  const clear = useCallback(() => {
    strokesRef.current = []
    setStrokeCount(0)
    redraw()
  }, [redraw])

  return {
    strokesRef,
    strokeCount,
    isPanning: () => isPanningRef.current,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    undo,
    clear,
  }
}
