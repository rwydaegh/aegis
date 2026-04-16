import { useCallback, useState, type RefObject } from 'react'
import { clampPan, panForCursorZoom } from './viewport'
import { MAX_ZOOM, MIN_ZOOM, type Point } from './types'

interface UseZoomPanOpts {
  width: number
  height: number
  containerRef: RefObject<HTMLDivElement | null>
}

interface ZoomPanApi {
  zoom: number
  pan: Point
  setPan: (p: Point | ((prev: Point) => Point)) => void
  onWheel: (e: React.WheelEvent) => void
  zoomIn: () => void
  zoomOut: () => void
  reset: () => void
}

// Encapsulate the zoom/pan state and interactions in one place, keeping the
// main AnnotationCanvas component focused on drawing concerns.
export function useZoomPan({ width, height, containerRef }: UseZoomPanOpts): ZoomPanApi {
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState<Point>({ x: 0, y: 0 })

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const factor = e.deltaY > 0 ? 1 / 1.15 : 1.15
    const { clientX, clientY } = e
    setZoom(prev => {
      const next = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, prev * factor))
      setPan(p => panForCursorZoom(containerRef.current, clientX, clientY, p, prev, next, width, height))
      return next
    })
  }, [containerRef, width, height])

  const zoomIn = useCallback(() => {
    setZoom(prev => {
      const next = Math.min(MAX_ZOOM, prev * 1.5)
      if (next > prev) setPan(p => clampPan(p.x, p.y, next, width, height))
      return next
    })
  }, [width, height])

  const zoomOut = useCallback(() => {
    setZoom(prev => {
      const next = Math.max(MIN_ZOOM, prev / 1.5)
      setPan(p => clampPan(p.x, p.y, next, width, height))
      return next
    })
  }, [width, height])

  const reset = useCallback(() => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }, [])

  return { zoom, pan, setPan, onWheel, zoomIn, zoomOut, reset }
}
