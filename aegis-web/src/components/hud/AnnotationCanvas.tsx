import { useRef, useEffect, useCallback, useState, forwardRef, useImperativeHandle } from 'react'
import { Undo2, Trash2 } from 'lucide-react'

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

const AnnotationCanvas = forwardRef<AnnotationCanvasHandle, Props>(
  function AnnotationCanvas({ screenshotUrl, width, height }, ref) {
    const bgCanvasRef = useRef<HTMLCanvasElement>(null)
    const drawCanvasRef = useRef<HTMLCanvasElement>(null)
    const strokesRef = useRef<Stroke[]>([])
    const currentStrokeRef = useRef<Stroke | null>(null)
    const isDrawingRef = useRef(false)
    const [strokeCount, setStrokeCount] = useState(0)

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

    const getCanvasPoint = (e: React.PointerEvent) => {
      const canvas = drawCanvasRef.current
      if (!canvas) return { x: 0, y: 0 }
      const rect = canvas.getBoundingClientRect()
      return {
        x: (e.clientX - rect.left) * (width / rect.width),
        y: (e.clientY - rect.top) * (height / rect.height),
      }
    }

    const handlePointerDown = (e: React.PointerEvent) => {
      isDrawingRef.current = true
      const point = getCanvasPoint(e)
      currentStrokeRef.current = { points: [point] }
      ;(e.target as Element).setPointerCapture(e.pointerId)
    }

    const handlePointerMove = (e: React.PointerEvent) => {
      if (!isDrawingRef.current || !currentStrokeRef.current) return
      const point = getCanvasPoint(e)
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
    }

    const handlePointerUp = () => {
      if (currentStrokeRef.current && currentStrokeRef.current.points.length > 1) {
        strokesRef.current.push(currentStrokeRef.current)
        setStrokeCount(strokesRef.current.length)
      }
      currentStrokeRef.current = null
      isDrawingRef.current = false
    }

    useImperativeHandle(ref, () => ({
      getCompositeImage: () => {
        return new Promise<Blob>((resolve, reject) => {
          const composite = document.createElement('canvas')
          composite.width = width
          composite.height = height
          const ctx = composite.getContext('2d')
          if (!ctx) return reject(new Error('Cannot get canvas context'))
          if (bgCanvasRef.current) ctx.drawImage(bgCanvasRef.current, 0, 0)
          if (drawCanvasRef.current) ctx.drawImage(drawCanvasRef.current, 0, 0)
          composite.toBlob(
            blob => {
              if (blob) resolve(blob)
              else reject(new Error('Failed to export canvas'))
            },
            'image/jpeg',
            0.85,
          )
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

    return (
      <div className="relative select-none" style={{ width, height }}>
        <canvas ref={bgCanvasRef} width={width} height={height} className="absolute inset-0 rounded" />
        <canvas
          ref={drawCanvasRef}
          width={width}
          height={height}
          className="absolute inset-0 cursor-crosshair rounded"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
        />
        {strokeCount > 0 && (
          <div className="absolute top-2 right-2 flex gap-1">
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
          </div>
        )}
      </div>
    )
  },
)

export default AnnotationCanvas
