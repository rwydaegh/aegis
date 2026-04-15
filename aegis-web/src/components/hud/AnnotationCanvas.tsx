import { useRef, useEffect, useCallback, useState, forwardRef, useImperativeHandle } from 'react'
import { Undo2, Trash2, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'

export interface AnnotationCanvasHandle {
  getCompositeImage: () => Promise<Blob>
}

interface Props {
  screenshotUrl: string
  width: number
  height: number
}

interface Stroke {
  points: { x: number; y: number }[]
}

const MIN_ZOOM = 1
const MAX_ZOOM = 10

const AnnotationCanvas = forwardRef<AnnotationCanvasHandle, Props>(
  function AnnotationCanvas({ screenshotUrl, width, height }, ref) {
    const bgCanvasRef = useRef<HTMLCanvasElement>(null)
    const drawCanvasRef = useRef<HTMLCanvasElement>(null)
    const containerRef = useRef<HTMLDivElement>(null)
    const strokesRef = useRef<Stroke[]>([])
    const currentStrokeRef = useRef<Stroke | null>(null)
    const isDrawingRef = useRef(false)
    const isPanningRef = useRef(false)
    const panStartRef = useRef({ x: 0, y: 0 })
    const [strokeCount, setStrokeCount] = useState(0)

    // Zoom and pan state
    const [zoom, setZoom] = useState(1)
    const [pan, setPan] = useState({ x: 0, y: 0 })
    const [spaceHeld, setSpaceHeld] = useState(false)

    // Track space key for pan mode
    useEffect(() => {
      function onKeyDown(e: KeyboardEvent) {
        if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
        if (e.code === 'Space' && !e.repeat) {
          e.preventDefault()
          setSpaceHeld(true)
        }
      }
      function onKeyUp(e: KeyboardEvent) {
        if (e.code === 'Space') setSpaceHeld(false)
      }
      window.addEventListener('keydown', onKeyDown)
      window.addEventListener('keyup', onKeyUp)
      return () => {
        window.removeEventListener('keydown', onKeyDown)
        window.removeEventListener('keyup', onKeyUp)
      }
    }, [])

    // Clamp pan so the image doesn't go out of view
    const clampPan = useCallback((px: number, py: number, z: number) => {
      const maxPanX = Math.max(0, (width * z - width) / 2)
      const maxPanY = Math.max(0, (height * z - height) / 2)
      return {
        x: Math.max(-maxPanX, Math.min(maxPanX, px)),
        y: Math.max(-maxPanY, Math.min(maxPanY, py)),
      }
    }, [width, height])

    useEffect(() => {
      const canvas = bgCanvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      const img = new Image()
      img.onload = () => {
        ctx.clearRect(0, 0, width, height)
        ctx.drawImage(img, 0, 0, width, height)
      }
      img.src = screenshotUrl
    }, [screenshotUrl, width, height])

    const redrawStrokes = useCallback(() => {
      const canvas = drawCanvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.clearRect(0, 0, width, height)
      ctx.strokeStyle = '#ff3333'
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      for (const stroke of strokesRef.current) {
        if (stroke.points.length < 2) continue
        ctx.beginPath()
        ctx.moveTo(stroke.points[0].x, stroke.points[0].y)
        for (let i = 1; i < stroke.points.length; i++) {
          ctx.lineTo(stroke.points[i].x, stroke.points[i].y)
        }
        ctx.stroke()
      }
    }, [width, height])

    // Convert screen coordinates to canvas coordinates (accounting for zoom/pan)
    const getCanvasPoint = useCallback((clientX: number, clientY: number) => {
      const container = containerRef.current
      if (!container) return { x: 0, y: 0 }
      const rect = container.getBoundingClientRect()
      // Position within the viewport div
      const viewX = clientX - rect.left
      const viewY = clientY - rect.top
      // Invert the CSS transform: translate then scale
      const canvasX = (viewX - rect.width / 2 - pan.x) / zoom + width / 2
      const canvasY = (viewY - rect.height / 2 - pan.y) / zoom + height / 2
      return {
        x: Math.max(0, Math.min(width, canvasX)),
        y: Math.max(0, Math.min(height, canvasY)),
      }
    }, [zoom, pan, width, height])

    const handlePointerDown = useCallback((e: React.PointerEvent) => {
      if (spaceHeld || e.button === 1) {
        // Pan mode
        isPanningRef.current = true
        panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
        ;(e.target as Element).setPointerCapture(e.pointerId)
        return
      }
      // Draw mode
      isDrawingRef.current = true
      const point = getCanvasPoint(e.clientX, e.clientY)
      currentStrokeRef.current = { points: [point] }
      ;(e.target as Element).setPointerCapture(e.pointerId)
    }, [spaceHeld, pan, getCanvasPoint])

    const handlePointerMove = useCallback((e: React.PointerEvent) => {
      if (isPanningRef.current) {
        const newPan = clampPan(
          e.clientX - panStartRef.current.x,
          e.clientY - panStartRef.current.y,
          zoom,
        )
        setPan(newPan)
        return
      }
      if (!isDrawingRef.current || !currentStrokeRef.current) return
      const point = getCanvasPoint(e.clientX, e.clientY)
      currentStrokeRef.current.points.push(point)
      const canvas = drawCanvasRef.current
      const ctx = canvas?.getContext('2d')
      if (!ctx) return
      const pts = currentStrokeRef.current.points
      if (pts.length < 2) return
      ctx.strokeStyle = '#ff3333'
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      ctx.beginPath()
      ctx.moveTo(pts[pts.length - 2].x, pts[pts.length - 2].y)
      ctx.lineTo(pts[pts.length - 1].x, pts[pts.length - 1].y)
      ctx.stroke()
    }, [zoom, clampPan, getCanvasPoint])

    const handlePointerUp = useCallback(() => {
      if (isPanningRef.current) {
        isPanningRef.current = false
        return
      }
      if (currentStrokeRef.current && currentStrokeRef.current.points.length > 1) {
        strokesRef.current.push(currentStrokeRef.current)
        setStrokeCount(strokesRef.current.length)
      }
      currentStrokeRef.current = null
      isDrawingRef.current = false
    }, [])

    // Scroll to zoom, centered on cursor (multiplicative for natural feel)
    const handleWheel = useCallback((e: React.WheelEvent) => {
      e.preventDefault()
      // Multiplicative zoom: each scroll step scales by 1.15x (in or out)
      const factor = e.deltaY > 0 ? 1 / 1.15 : 1.15
      setZoom(prev => {
        const next = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, prev * factor))
        const container = containerRef.current
        if (container && next !== prev) {
          const rect = container.getBoundingClientRect()
          const cx = e.clientX - rect.left - rect.width / 2
          const cy = e.clientY - rect.top - rect.height / 2
          const scale = next / prev
          const newPan = clampPan(
            pan.x * scale + cx * (1 - scale),
            pan.y * scale + cy * (1 - scale),
            next,
          )
          setPan(newPan)
        }
        return next
      })
    }, [pan, clampPan])

    const resetView = useCallback(() => {
      setZoom(1)
      setPan({ x: 0, y: 0 })
    }, [])

    const zoomIn = useCallback(() => {
      setZoom(prev => {
        const next = Math.min(MAX_ZOOM, prev * 1.5)
        if (next > prev) setPan(p => clampPan(p.x, p.y, next))
        return next
      })
    }, [clampPan])

    const zoomOut = useCallback(() => {
      setZoom(prev => {
        const next = Math.max(MIN_ZOOM, prev / 1.5)
        setPan(p => clampPan(p.x, p.y, next))
        return next
      })
    }, [clampPan])

    useImperativeHandle(ref, () => ({
      getCompositeImage: () => {
        return new Promise<Blob>((resolve, reject) => {
          // Load the original screenshot to export at full captured resolution
          const img = new Image()
          img.onload = () => {
            const fullW = img.naturalWidth
            const fullH = img.naturalHeight
            const scaleX = fullW / width
            const scaleY = fullH / height

            const composite = document.createElement('canvas')
            composite.width = fullW
            composite.height = fullH
            const ctx = composite.getContext('2d')
            if (!ctx) return reject(new Error('Cannot get canvas context'))

            // Draw screenshot at full resolution
            ctx.drawImage(img, 0, 0, fullW, fullH)

            // Draw annotations scaled up to match
            ctx.strokeStyle = '#ff3333'
            ctx.lineWidth = 3 * Math.max(scaleX, scaleY)
            ctx.lineCap = 'round'
            ctx.lineJoin = 'round'
            for (const stroke of strokesRef.current) {
              if (stroke.points.length < 2) continue
              ctx.beginPath()
              ctx.moveTo(stroke.points[0].x * scaleX, stroke.points[0].y * scaleY)
              for (let i = 1; i < stroke.points.length; i++) {
                ctx.lineTo(stroke.points[i].x * scaleX, stroke.points[i].y * scaleY)
              }
              ctx.stroke()
            }

            composite.toBlob(
              blob => {
                if (blob) resolve(blob)
                else reject(new Error('Failed to export canvas'))
              },
              'image/png',
            )
          }
          img.onerror = () => reject(new Error('Failed to load screenshot for export'))
          img.src = screenshotUrl
        })
      },
    }))

    const undo = useCallback(() => {
      strokesRef.current.pop()
      setStrokeCount(strokesRef.current.length)
      redrawStrokes()
    }, [redrawStrokes])

    const clear = useCallback(() => {
      strokesRef.current = []
      setStrokeCount(0)
      redrawStrokes()
    }, [redrawStrokes])

    const isZoomed = zoom > 1
    const cursor = spaceHeld ? (isPanningRef.current ? 'grabbing' : 'grab') : 'crosshair'

    return (
      <div className="relative select-none" style={{ width, height }}>
        {/* Clip viewport */}
        <div
          className="overflow-hidden rounded"
          style={{ width, height }}
          onWheel={handleWheel}
        >
          {/* Transformed canvas layer */}
          <div
            ref={containerRef}
            style={{
              width,
              height,
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: 'center center',
            }}
          >
            <canvas ref={bgCanvasRef} width={width} height={height} className="absolute inset-0 rounded" />
            <canvas
              ref={drawCanvasRef}
              width={width}
              height={height}
              className="absolute inset-0 rounded"
              style={{ cursor }}
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
            />
          </div>
        </div>

        {/* Toolbar */}
        <div className="absolute top-2 right-2 flex gap-1">
          <button
            onClick={zoomIn}
            className="p-1.5 rounded bg-black/60 hover:bg-black/80 text-white backdrop-blur-sm"
            title="Zoom in"
          >
            <ZoomIn className="size-3.5" />
          </button>
          <button
            onClick={zoomOut}
            disabled={!isZoomed}
            className="p-1.5 rounded bg-black/60 hover:bg-black/80 text-white backdrop-blur-sm disabled:opacity-30"
            title="Zoom out"
          >
            <ZoomOut className="size-3.5" />
          </button>
          {isZoomed && (
            <button
              onClick={resetView}
              className="p-1.5 rounded bg-black/60 hover:bg-black/80 text-white backdrop-blur-sm"
              title="Reset zoom"
            >
              <RotateCcw className="size-3.5" />
            </button>
          )}
          {strokeCount > 0 && (
            <>
              <div className="w-px h-5 self-center bg-white/30" />
              <button
                onClick={undo}
                className="p-1.5 rounded bg-black/60 hover:bg-black/80 text-white backdrop-blur-sm"
                title="Undo last stroke"
              >
                <Undo2 className="size-3.5" />
              </button>
              <button
                onClick={clear}
                className="p-1.5 rounded bg-black/60 hover:bg-black/80 text-white backdrop-blur-sm"
                title="Clear all drawings"
              >
                <Trash2 className="size-3.5" />
              </button>
            </>
          )}
        </div>

        {/* Zoom indicator + pan hint */}
        {isZoomed && (
          <div className="absolute bottom-2 left-2 px-1.5 py-0.5 rounded bg-black/60 text-white text-[10px] font-mono backdrop-blur-sm">
            {zoom.toFixed(1)}x {spaceHeld ? 'drag to pan' : 'hold Space to pan'}
          </div>
        )}
      </div>
    )
  },
)

export default AnnotationCanvas
