import { useState, useRef, useCallback, useEffect } from 'react'
import { Bug, X, Send, Loader2, ExternalLink, ImageOff, Image as ImageIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import AnnotationCanvas, { type AnnotationCanvasHandle } from '../annotationCanvas'
import type { Phase, ScreenshotDimensions } from './types'

interface BugReporterModalProps {
  screenshot: string
  screenshotDimensions: ScreenshotDimensions
  onClose: () => void
  onSubmit: (description: string, annotatedScreenshot: Blob | null) => Promise<void>
  phase: Phase
  issueUrl: string | null
  errorMessage: string | null
}

// ---------------------------------------------------------------------------
// Sub-sections (kept local to avoid cross-file prop plumbing for pure markup)
// ---------------------------------------------------------------------------

interface ModalHeaderProps {
  onClose: () => void
  phase: Phase
}

function ModalHeader({ onClose, phase }: ModalHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-3">
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
  )
}

interface SuccessViewProps {
  issueUrl: string
  onClose: () => void
}

function SuccessView({ issueUrl, onClose }: SuccessViewProps) {
  return (
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
  )
}

interface ScreenshotSectionProps {
  includeScreenshot: boolean
  setIncludeScreenshot: (v: boolean) => void
  screenshot: string
  screenshotDimensions: ScreenshotDimensions
  canvasRef: React.Ref<AnnotationCanvasHandle>
}

function ScreenshotSection({
  includeScreenshot,
  setIncludeScreenshot,
  screenshot,
  screenshotDimensions,
  canvasRef,
}: ScreenshotSectionProps) {
  const hasScreenshot = screenshot.length > 0 && screenshotDimensions.width > 0

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
          Screenshot
        </p>
        <button
          type="button"
          onClick={() => setIncludeScreenshot(!includeScreenshot)}
          className={cn(
            'inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded transition-colors',
            includeScreenshot
              ? 'text-foreground/70 hover:text-foreground'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {includeScreenshot ? (
            <><ImageOff className="size-3" /> Hide</>
          ) : (
            <><ImageIcon className="size-3" /> Show</>
          )}
        </button>
      </div>
      {includeScreenshot && hasScreenshot && (
        <>
          <p className="text-[10px] text-muted-foreground/60 mb-1">
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
        </>
      )}
      {includeScreenshot && !hasScreenshot && (
        <p className="text-[10px] text-muted-foreground/60 italic">
          Screenshot capture failed. You can still submit a text-only report.
        </p>
      )}
    </div>
  )
}

interface SubmitActionsProps {
  phase: Phase
  onClose: () => void
  onSubmit: () => void
  canSubmit: boolean
}

function SubmitActions({ phase, onClose, onSubmit, canSubmit }: SubmitActionsProps) {
  return (
    <div className="flex justify-end gap-2 pt-1">
      <button
        onClick={onClose}
        disabled={phase === 'submitting'}
        className="px-3 py-1.5 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors disabled:opacity-50"
      >
        Cancel
      </button>
      <button
        onClick={onSubmit}
        disabled={phase === 'submitting' || !canSubmit}
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
  )
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/** Close the modal on Escape (unless mid-submission). */
function useEscapeToClose(onClose: () => void, phase: Phase) {
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
}

// ---------------------------------------------------------------------------
// Main modal
// ---------------------------------------------------------------------------

export default function BugReporterModal({
  screenshot,
  screenshotDimensions,
  onClose,
  onSubmit,
  phase,
  issueUrl,
  errorMessage,
}: BugReporterModalProps) {
  const [description, setDescription] = useState('')
  const [includeScreenshot, setIncludeScreenshot] = useState(true)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const canvasRef = useRef<AnnotationCanvasHandle>(null)

  const handleSubmit = useCallback(async () => {
    if (phase === 'submitting') return
    const text = description.trim()
    if (!text) {
      textareaRef.current?.focus()
      return
    }
    const blob = includeScreenshot && canvasRef.current
      ? await canvasRef.current.getCompositeImage()
      : null
    await onSubmit(text, blob)
  }, [description, phase, onSubmit, includeScreenshot])

  useEscapeToClose(onClose, phase)

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
        className="fixed inset-0 bg-black/50 z-[60]"
        onClick={phase === 'submitting' ? undefined : onClose}
        data-bug-reporter-modal="true"
      />
      {/* Dialog */}
      <div
        className="fixed inset-0 flex items-center justify-center z-[60] pointer-events-none p-4"
        data-bug-reporter-modal="true"
      >
        <div
          className={cn(
            'bg-card/95 backdrop-blur-md rounded-xl border border-border shadow-2xl',
            'p-4 sm:p-5 max-h-[90vh] overflow-y-auto pointer-events-auto',
            'animate-in fade-in zoom-in-95 duration-150',
          )}
          style={{ width: 'fit-content', maxWidth: 'calc(100vw - 2rem)' }}
          onClick={(e) => e.stopPropagation()}
        >
          <ModalHeader onClose={onClose} phase={phase} />

          {phase === 'success' && issueUrl && (
            <SuccessView issueUrl={issueUrl} onClose={onClose} />
          )}

          {phase !== 'success' && (
            <div className="space-y-3">
              <ScreenshotSection
                includeScreenshot={includeScreenshot}
                setIncludeScreenshot={setIncludeScreenshot}
                screenshot={screenshot}
                screenshotDimensions={screenshotDimensions}
                canvasRef={canvasRef}
              />

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
                  rows={3}
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

              {phase === 'error' && errorMessage && (
                <p className="text-xs text-destructive rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2">
                  {errorMessage}
                </p>
              )}

              <SubmitActions
                phase={phase}
                onClose={onClose}
                onSubmit={handleSubmit}
                canSubmit={description.trim().length > 0}
              />
            </div>
          )}
        </div>
      </div>
    </>
  )
}
