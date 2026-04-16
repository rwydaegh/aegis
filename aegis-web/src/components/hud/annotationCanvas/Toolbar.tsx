import { Undo2, Trash2, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'

interface Props {
  isZoomed: boolean
  strokeCount: number
  onZoomIn: () => void
  onZoomOut: () => void
  onResetView: () => void
  onUndo: () => void
  onClear: () => void
}

// Floating toolbar overlay for the annotation canvas.
export function Toolbar({
  isZoomed,
  strokeCount,
  onZoomIn,
  onZoomOut,
  onResetView,
  onUndo,
  onClear,
}: Props) {
  const btnClass = 'p-1.5 rounded bg-black/60 hover:bg-black/80 text-white backdrop-blur-sm'
  return (
    <div className="absolute top-2 right-2 flex gap-1">
      <button onClick={onZoomIn} className={btnClass} title="Zoom in">
        <ZoomIn className="size-3.5" />
      </button>
      <button
        onClick={onZoomOut}
        disabled={!isZoomed}
        className={`${btnClass} disabled:opacity-30`}
        title="Zoom out"
      >
        <ZoomOut className="size-3.5" />
      </button>
      {isZoomed && (
        <button onClick={onResetView} className={btnClass} title="Reset zoom">
          <RotateCcw className="size-3.5" />
        </button>
      )}
      {strokeCount > 0 && (
        <>
          <div className="w-px h-5 self-center bg-white/30" />
          <button onClick={onUndo} className={btnClass} title="Undo last stroke">
            <Undo2 className="size-3.5" />
          </button>
          <button onClick={onClear} className={btnClass} title="Clear all drawings">
            <Trash2 className="size-3.5" />
          </button>
        </>
      )}
    </div>
  )
}
