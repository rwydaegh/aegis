import { useRef, forwardRef, useImperativeHandle } from 'react'
import { buildCompositeImage } from './composite'
import { Toolbar } from './Toolbar'
import { useBackgroundImage } from './useBackgroundImage'
import { usePointerHandlers } from './usePointerHandlers'
import { useSpaceHeld } from './useSpaceHeld'
import { useZoomPan } from './useZoomPan'
import type { AnnotationCanvasHandle } from './types'

export type { AnnotationCanvasHandle } from './types'

interface Props {
  screenshotUrl: string
  width: number
  height: number
}

const AnnotationCanvas = forwardRef<AnnotationCanvasHandle, Props>(
  function AnnotationCanvas({ screenshotUrl, width, height }, ref) {
    const bgCanvasRef = useRef<HTMLCanvasElement>(null)
    const drawCanvasRef = useRef<HTMLCanvasElement>(null)
    const containerRef = useRef<HTMLDivElement>(null)

    const spaceHeld = useSpaceHeld()
    const { zoom, pan, setPan, onWheel, zoomIn, zoomOut, reset } = useZoomPan({
      width, height, containerRef,
    })
    const pointer = usePointerHandlers({
      width, height, zoom, pan, setPan, containerRef, drawCanvasRef, spaceHeld,
    })

    useBackgroundImage(bgCanvasRef, screenshotUrl, width, height)

    useImperativeHandle(ref, () => ({
      getCompositeImage: () => buildCompositeImage({
        screenshotUrl,
        width,
        height,
        zoom,
        pan,
        strokes: pointer.strokesRef.current,
      }),
    }))

    const isZoomed = zoom > 1
    const cursor = spaceHeld ? (pointer.isPanning() ? 'grabbing' : 'grab') : 'crosshair'

    return (
      <div className="relative select-none" style={{ width, height }}>
        {/* Clip viewport */}
        <div className="overflow-hidden rounded" style={{ width, height }} onWheel={onWheel}>
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
              onPointerDown={pointer.onPointerDown}
              onPointerMove={pointer.onPointerMove}
              onPointerUp={pointer.onPointerUp}
            />
          </div>
        </div>

        <Toolbar
          isZoomed={isZoomed}
          strokeCount={pointer.strokeCount}
          onZoomIn={zoomIn}
          onZoomOut={zoomOut}
          onResetView={reset}
          onUndo={pointer.undo}
          onClear={pointer.clear}
        />

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
