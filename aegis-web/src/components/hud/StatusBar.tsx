import { useState, useEffect, useRef } from 'react'
import { useUIStore } from '@/stores/ui'

function formatMs(ms: number): string {
  if (ms < 1) return '<1 ms'
  if (ms < 1000) return `${Math.round(ms)} ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export default function StatusBar() {
  const { isComputing, statusMessage, setComputeElapsed, lastComputeTiming } = useUIStore()
  const [elapsed, setElapsed] = useState(0)
  const [expanded, setExpanded] = useState(false)
  const startRef = useRef<number | null>(null)

  useEffect(() => {
    if (isComputing) {
      startRef.current = Date.now()
      setElapsed(0)
      setComputeElapsed(0)
      setExpanded(false)
      const interval = setInterval(() => {
        const ms = Date.now() - (startRef.current ?? Date.now())
        setElapsed(ms)
        setComputeElapsed(ms)
      }, 100)
      return () => clearInterval(interval)
    } else {
      startRef.current = null
    }
  }, [isComputing, setComputeElapsed])

  const showTiming = !isComputing && lastComputeTiming
  if (!isComputing && !statusMessage && !showTiming) return null

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex flex-col items-center gap-0">
      {expanded && showTiming && (
        <div className="bg-card/90 backdrop-blur-md rounded-lg border border-border px-3 py-2 mb-1
          text-[11px] font-mono text-muted-foreground min-w-[200px]">
          {lastComputeTiming.rtMs != null && (
            <div className="flex justify-between gap-4">
              <span className="text-foreground/60">ray tracing</span>
              <span>{formatMs(lastComputeTiming.rtMs)}</span>
            </div>
          )}
          <div className="flex justify-between gap-4">
            <span className="text-foreground/60">kernel</span>
            <span>{formatMs(lastComputeTiming.kernelMs)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-foreground/60">averaging</span>
            <span>
              {formatMs(lastComputeTiming.averagingMs)}
              {lastComputeTiming.avgCached && (
                <span className="text-primary/60 ml-1">cached</span>
              )}
            </span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-foreground/60">compliance</span>
            <span>{formatMs(lastComputeTiming.complianceMs)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-foreground/60">transfer</span>
            <span>{formatMs(lastComputeTiming.networkMs)}</span>
          </div>
          {lastComputeTiming.gpuBackend && (
            <div className="flex justify-between gap-4">
              <span className="text-foreground/60">gpu</span>
              <span className={lastComputeTiming.gpuBackend === 'cpu'
                ? 'text-yellow-500' : 'text-green-500'}>
                {lastComputeTiming.gpuBackend}
              </span>
            </div>
          )}
        </div>
      )}

      <div
        className={`flex items-center gap-2 bg-card/90 backdrop-blur-md rounded-full border border-border px-4 py-2
          ${showTiming ? 'cursor-pointer hover:bg-card/95 select-none' : ''}`}
        onClick={() => showTiming && setExpanded(e => !e)}
      >
        {isComputing && (
          <span className="text-xs shimmer-text">
            Computing... {elapsed > 0 ? `(${(elapsed / 1000).toFixed(1)}s)` : ''}
          </span>
        )}
        {showTiming && (
          <>
            <svg className="w-3 h-3 text-primary/70" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="8" cy="8" r="6.5" />
              <path d="M8 4v4.5l3 1.5" />
            </svg>
            <span className="text-xs font-mono tabular-nums text-foreground/80">
              {formatMs(lastComputeTiming.totalMs)}
            </span>
            <svg
              className={`w-2.5 h-2.5 text-muted-foreground transition-transform ${expanded ? 'rotate-180' : ''}`}
              viewBox="0 0 10 6" fill="none" stroke="currentColor" strokeWidth="1.5"
            >
              <path d="M1 1l4 4 4-4" />
            </svg>
          </>
        )}
        {!isComputing && !showTiming && statusMessage && (
          <span className="text-xs text-muted-foreground">{statusMessage}</span>
        )}
      </div>
    </div>
  )
}
