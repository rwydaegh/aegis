/**
 * BugReporter - a floating button that opens a modal for submitting in-app bug reports.
 *
 * Captures a screenshot from the WebGL canvas (preserveDrawingBuffer must be on),
 * collects Zustand store state, and posts to /api/bug-report.
 * On success shows a link to the created GitHub issue.
 */
import { useState, useRef, useCallback, useEffect } from 'react'
import { Bug, X, Send, Loader2, ExternalLink } from 'lucide-react'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { cn } from '@/lib/utils'
import AnnotationCanvas, { type AnnotationCanvasHandle } from './AnnotationCanvas'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BugReportResponse {
  issueNumber: number
  issueUrl: string
}

type Phase = 'idle' | 'capturing' | 'open' | 'submitting' | 'success' | 'error'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Collect a lightweight snapshot of the current app state for the issue body. */
function collectState(): Record<string, unknown> {
  const sim = useSimulationStore.getState()
  const ui = useUIStore.getState()
  return {
    mode: sim.mode,
    freqGhz: sim.freqGhz,
    powerDbm: sim.powerDbm,
    fresnel: sim.fresnel,
    polarisation: sim.polarisation,
    curvature: sim.curvature,
    diffraction: sim.diffraction,
    skinModel: sim.skinModel,
    antennaPos: sim.antennaPos ? sim.antennaPos.join(', ') : null,
    cameraMode: ui.cameraMode,
    sidebarMode: ui.sidebarMode,
    legendScale: ui.legendScale,
  }
}

/** Grab the largest canvas on the page (the WebGL viewport).
 *  Requires preserveDrawingBuffer: true on the R3F Canvas. */
function captureScreenshot(): string {
  const allCanvases = Array.from(document.querySelectorAll('canvas'))
  const canvas = allCanvases.reduce<HTMLCanvasElement | null>((best, c) => {
    if (!best) return c
    return c.width * c.height > best.width * best.height ? c : best
  }, null)
  if (!canvas || canvas.width === 0) throw new Error('No visible canvas found')
  return canvas.toDataURL('image/jpeg', 0.7)
}

async function postBugReport(payload: {
  screenshot: string
  description: string
  state: Record<string, unknown>
}): Promise<BugReportResponse> {
  const res = await fetch('/api/bug-report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`
    try {
      const data = await res.json()
      if (data?.error) msg = data.error
    } catch {
      // ignore parse errors
    }
    throw new Error(msg)
  }
  return res.json() as Promise<BugReportResponse>
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

interface BugReporterModalProps {
  screenshot: string
  screenshotDimensions: { width: number; height: number }
  onClose: () => void
  onSubmit: (description: string, annotatedScreenshot: Blob) => Promise<void>
  phase: Phase
  issueUrl: string | null
  errorMessage: string | null
}

function BugReporterModal({
  screenshot,
  screenshotDimensions,
  onClose,
  onSubmit,
  phase,
  issueUrl,
  errorMessage,
}: BugReporterModalProps) {
  const [description, setDescription] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const canvasRef = useRef<AnnotationCanvasHandle>(null)

  const handleSubmit = useCallback(async () => {
    if (phase === 'submitting') return
    const text = description.trim()
    if (!text) {
      textareaRef.current?.focus()
      return
    }
    const blob = canvasRef.current
      ? await canvasRef.current.getCompositeImage()
      : new Blob()
    await onSubmit(text, blob)
  }, [description, phase, onSubmit])

  // Escape to close, Cmd/Ctrl+Enter to submit
  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape' && phase !== 'submitting') {
        e.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose, phase])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault()
        handleSubmit()
      }
    },
    [handleSubmit],
  )

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-[60] pointer-events-auto"
        onClick={phase === 'submitting' ? undefined : onClose}
      />
      {/* Dialog */}
      <div className="fixed inset-0 flex items-center justify-center z-[60] pointer-events-none">
        <div
          className={cn(
            'bg-card/95 backdrop-blur-md rounded-xl border border-border shadow-2xl',
            'p-5 max-w-[calc(100vw-4rem)] pointer-events-auto',
            'animate-in fade-in zoom-in-95 duration-150',
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Bug className="size-4 text-muted-foreground" />
              <h2 className="text-sm font-medium text-heading">Report a bug</h2>
            </div>
            {phase !== 'submitting' && (
              <button
                onClick={onClose}
                className="text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Close"
              >
                <X className="size-4" />
              </button>
            )}
          </div>

          {/* Success state */}
          {phase === 'success' && issueUrl && (
            <div className="space-y-3">
              <p className="text-sm text-foreground/80">
                Thank you! Your report was submitted.
              </p>
              <a
                href={issueUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
              >
                <ExternalLink className="size-3" />
                View issue on GitHub
              </a>
              <div className="flex justify-end mt-4">
                <button
                  onClick={onClose}
                  className="px-3 py-1.5 rounded-md text-xs bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          )}

          {/* Form state */}
          {phase !== 'success' && (
            <div className="space-y-3">
              {/* Screenshot with annotation canvas */}
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5">
                  Draw on the screenshot to highlight the issue
                </p>
                <div className="border border-border/50 rounded-md overflow-hidden">
                  <AnnotationCanvas
                    ref={canvasRef}
                    screenshotUrl={screenshot}
                    width={screenshotDimensions.width}
                    height={screenshotDimensions.height}
                  />
                </div>
              </div>

              {/* Description */}
              <div>
                <label
                  htmlFor="bug-description"
                  className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium block mb-1.5"
                >
                  What went wrong?
                </label>
                <textarea
                  id="bug-description"
                  ref={textareaRef}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Describe the issue..."
                  disabled={phase === 'submitting'}
                  rows={4}
                  className={cn(
                    'w-full rounded-md border border-border bg-muted/40 px-3 py-2',
                    'text-xs text-foreground placeholder:text-muted-foreground/60',
                    'focus:outline-none focus:ring-1 focus:ring-primary/50',
                    'resize-none disabled:opacity-50',
                  )}
                  autoFocus
                />
                <p className="text-[10px] text-muted-foreground/60 mt-1">
                  {navigator.platform?.includes('Mac') ? 'Cmd' : 'Ctrl'}+Enter to submit
                </p>
              </div>

              {/* Error */}
              {phase === 'error' && errorMessage && (
                <p className="text-xs text-destructive rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2">
                  {errorMessage}
                </p>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-2 pt-1">
                <button
                  onClick={onClose}
                  disabled={phase === 'submitting'}
                  className="px-3 py-1.5 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={phase === 'submitting' || !description.trim()}
                  className={cn(
                    'px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
                    'inline-flex items-center gap-1.5',
                    'bg-primary text-primary-foreground hover:bg-primary/90',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                  )}
                >
                  {phase === 'submitting' ? (
                    <>
                      <Loader2 className="size-3 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Send className="size-3" />
                      Submit report
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const MAX_WIDTH = 960
const MAX_HEIGHT = 600

export default function BugReporter() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [screenshot, setScreenshot] = useState<string>('')
  const [screenshotDimensions, setScreenshotDimensions] = useState({ width: 0, height: 0 })
  const [state, setState] = useState<Record<string, unknown>>({})
  const [issueUrl, setIssueUrl] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleOpen = useCallback(() => {
    if (phase !== 'idle') return
    setPhase('capturing')
    const appState = collectState()
    setState(appState)
    try {
      const shot = captureScreenshot()
      setScreenshot(shot)
      // Compute display dimensions for the annotation canvas
      const img = new Image()
      img.onload = () => {
        let w = img.width
        let h = img.height
        if (w > MAX_WIDTH) { h = Math.round(h * (MAX_WIDTH / w)); w = MAX_WIDTH }
        if (h > MAX_HEIGHT) { w = Math.round(w * (MAX_HEIGHT / h)); h = MAX_HEIGHT }
        setScreenshotDimensions({ width: w, height: h })
        setPhase('open')
      }
      img.onerror = () => {
        setScreenshotDimensions({ width: MAX_WIDTH, height: MAX_HEIGHT })
        setPhase('open')
      }
      img.src = shot
    } catch (err) {
      console.error('BugReporter: screenshot failed', err)
      setScreenshot('')
      setScreenshotDimensions({ width: MAX_WIDTH, height: MAX_HEIGHT })
      setPhase('open')
    }
  }, [phase])

  // Shift+B keyboard shortcut
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === 'B' && e.shiftKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        handleOpen()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleOpen])

  const handleClose = useCallback(() => {
    setPhase('idle')
    setScreenshot('')
    setScreenshotDimensions({ width: 0, height: 0 })
    setState({})
    setIssueUrl(null)
    setErrorMessage(null)
  }, [])

  const handleSubmit = useCallback(
    async (description: string, annotatedBlob: Blob) => {
      setPhase('submitting')
      setErrorMessage(null)
      try {
        // Convert annotated blob to data URL for submission
        const dataUrl = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => resolve(reader.result as string)
          reader.onerror = reject
          reader.readAsDataURL(annotatedBlob)
        })
        const result = await postBugReport({ screenshot: dataUrl, description, state })
        setIssueUrl(result.issueUrl)
        setPhase('success')
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error'
        setErrorMessage(msg)
        setPhase('error')
      }
    },
    [state],
  )

  const isOpen = phase === 'open' || phase === 'submitting' || phase === 'success' || phase === 'error'

  return (
    <>
      {/* Trigger button - styled to sit in the toolbar */}
      <button
        onClick={phase === 'capturing' ? undefined : handleOpen}
        disabled={phase === 'capturing'}
        className={cn(
          'inline-flex items-center gap-1 justify-center',
          'h-7 px-2 rounded-md transition-colors cursor-pointer',
          'bg-destructive/15 border border-destructive/25 text-destructive',
          'hover:bg-destructive/25 hover:text-destructive',
          'disabled:opacity-50 disabled:cursor-wait',
        )}
        aria-label="Report a bug"
        title="Report a bug (Shift+B)"
      >
        {phase === 'capturing' ? (
          <Loader2 className="size-3.5 animate-spin" />
        ) : (
          <>
            <Bug className="size-3.5" />
            <span className="text-[10px] font-medium hidden md:inline">Bug</span>
          </>
        )}
      </button>

      {/* Modal */}
      {isOpen && (
        <BugReporterModal
          screenshot={screenshot}
          screenshotDimensions={screenshotDimensions}
          onClose={handleClose}
          onSubmit={handleSubmit}
          phase={phase}
          issueUrl={issueUrl}
          errorMessage={errorMessage}
        />
      )}
    </>
  )
}
