/**
 * BugReporter - a toolbar button that opens a modal for submitting in-app bug reports.
 *
 * Captures a full-page screenshot via html-to-image (uses browser's own CSS engine,
 * so oklch and other modern CSS work natively). Collects Zustand store state and
 * posts to /api/bug-report. On success shows a link to the created GitHub issue.
 */
import { useState, useCallback, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Bug, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import BugReporterModal from './BugReporterModal'
import {
  blobToDataUrl,
  captureFullPage,
  collectState,
  computeScreenshotDimensions,
  postBugReport,
} from './helpers'
import type { Phase, ScreenshotDimensions } from './types'

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/** Shift+B opens the reporter (ignored when typing in an input). */
function useShiftBShortcut(handleOpen: () => void) {
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
}

// ---------------------------------------------------------------------------
// Submission helper
// ---------------------------------------------------------------------------

/** Convert the (optional) annotated blob to a data URL and POST the report. */
async function submitReport(params: {
  description: string
  annotatedBlob: Blob | null
  state: Record<string, unknown>
}): Promise<string> {
  const { description, annotatedBlob, state } = params
  const screenshotDataUrl = annotatedBlob ? await blobToDataUrl(annotatedBlob) : ''
  const result = await postBugReport({ screenshot: screenshotDataUrl, description, state })
  return result.issueUrl
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function BugReporter() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [screenshot, setScreenshot] = useState<string>('')
  const [screenshotDimensions, setScreenshotDimensions] = useState<ScreenshotDimensions>({ width: 0, height: 0 })
  const [state, setState] = useState<Record<string, unknown>>({})
  const [issueUrl, setIssueUrl] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Resolve final screenshot dimensions once the image loads, then open the modal.
  const finalizeCapture = useCallback((shot: string) => {
    const img = new Image()
    img.onload = () => {
      setScreenshotDimensions(computeScreenshotDimensions(img))
      setPhase('open')
    }
    img.onerror = () => {
      setScreenshotDimensions({ width: 0, height: 0 })
      setPhase('open')
    }
    img.src = shot
  }, [])

  const handleOpen = useCallback(async () => {
    if (phase !== 'idle') return
    setPhase('capturing')
    setState(collectState())
    try {
      const shot = await captureFullPage()
      setScreenshot(shot)
      finalizeCapture(shot)
    } catch (err) {
      console.error('BugReporter: screenshot failed', err)
      setScreenshot('')
      setScreenshotDimensions({ width: 0, height: 0 })
      setPhase('open')
    }
  }, [phase, finalizeCapture])

  useShiftBShortcut(handleOpen)

  const handleClose = useCallback(() => {
    setPhase('idle')
    setScreenshot('')
    setScreenshotDimensions({ width: 0, height: 0 })
    setState({})
    setIssueUrl(null)
    setErrorMessage(null)
  }, [])

  const handleSubmit = useCallback(
    async (description: string, annotatedBlob: Blob | null) => {
      setPhase('submitting')
      setErrorMessage(null)
      try {
        const url = await submitReport({ description, annotatedBlob, state })
        setIssueUrl(url)
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

      {/* Modal - portalled to body to escape toolbar's backdrop-filter containing block */}
      {isOpen && createPortal(
        <BugReporterModal
          screenshot={screenshot}
          screenshotDimensions={screenshotDimensions}
          onClose={handleClose}
          onSubmit={handleSubmit}
          phase={phase}
          issueUrl={issueUrl}
          errorMessage={errorMessage}
        />,
        document.body,
      )}
    </>
  )
}
