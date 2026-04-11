import { useEffect, useState, useCallback, useRef } from 'react'
import { useUIStore, TOUR_STEP_COUNT } from '@/stores/ui'
import { ChevronRight, X } from 'lucide-react'

interface TourStep {
  /** CSS selector for the target element, or null for center-screen */
  target: string | null
  title: string
  body: string
  /** Which side to place the tooltip relative to the target */
  side: 'top' | 'bottom' | 'left' | 'right'
  /** Action to perform when this step becomes active */
  onEnter?: () => void
}

const STEPS: TourStep[] = [
  {
    target: null,
    title: 'Welcome to AEGIS',
    body: 'AEGIS computes absorbed power density on human bodies from wireless antennas. This quick tour walks you through the interface.',
    side: 'bottom',
  },
  {
    target: '[data-tour="compliance"]',
    title: 'Compliance checks',
    body: 'The compliance panel shows ICNIRP 2020 checks for the current antenna setup. Each bar shows how close you are to the regulatory limit.',
    side: 'right',
  },
  {
    target: '[data-tour="color-legend"]',
    title: 'Dosimetry heatmap',
    body: 'Colors on the body show absorbed power density. Use the legend to toggle between linear and dB scales, or lock the range for comparisons.',
    side: 'left',
  },
  {
    target: '[data-tour="icon-rail"]',
    title: 'Sidebar groups',
    body: 'Settings are organized into four groups: World (scene setup), Source (antennas), Exposure (phantom and propagation), and Analysis (results and export).',
    side: 'right',
    onEnter: () => {
      const ui = useUIStore.getState()
      if (ui.sidebarMode === 'hidden') ui.setSidebarMode('expanded')
    },
  },
  {
    target: '[data-tour="camera-widget"]',
    title: 'Camera and movement',
    body: 'Snap to preset views or toggle follow mode. Move the phantom body with W/A/S/D keys and rotate the camera by dragging the scene.',
    side: 'left',
  },
  {
    target: '[data-tour="help-button"]',
    title: 'Keyboard shortcuts',
    body: 'Press ? anytime to see all keyboard shortcuts. You can restart this tour from the toolbar play button.',
    side: 'bottom',
  },
]

interface Rect {
  top: number
  left: number
  width: number
  height: number
}

function getTargetRect(selector: string | null): Rect | null {
  if (!selector) return null
  const el = document.querySelector(selector)
  if (!el) return null
  const r = el.getBoundingClientRect()
  return { top: r.top, left: r.left, width: r.width, height: r.height }
}

function StepDots({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-1.5">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`rounded-full transition-all duration-200 ${
            i === current
              ? 'w-4 h-1.5 bg-primary'
              : i < current
                ? 'w-1.5 h-1.5 bg-primary/50'
                : 'w-1.5 h-1.5 bg-muted-foreground/30'
          }`}
        />
      ))}
    </div>
  )
}

export default function GuidedTour() {
  const tourActive = useUIStore(s => s.tourActive)
  const tourStep = useUIStore(s => s.tourStep)
  const advanceTour = useUIStore(s => s.advanceTour)
  const dismissTour = useUIStore(s => s.dismissTour)

  const [targetRect, setTargetRect] = useState<Rect | null>(null)
  const [visible, setVisible] = useState(false)
  const rafRef = useRef(0)

  const step = STEPS[tourStep]
  const isLast = tourStep === TOUR_STEP_COUNT - 1

  // Track target element position
  const updateRect = useCallback(() => {
    if (!tourActive || !step) return
    const rect = getTargetRect(step.target)
    setTargetRect(rect)
    rafRef.current = requestAnimationFrame(updateRect)
  }, [tourActive, step])

  useEffect(() => {
    if (!tourActive) {
      setVisible(false)
      return
    }
    // Run onEnter for the current step
    step?.onEnter?.()
    // Small delay for enter animation
    const timer = setTimeout(() => setVisible(true), 50)
    rafRef.current = requestAnimationFrame(updateRect)
    return () => {
      clearTimeout(timer)
      cancelAnimationFrame(rafRef.current)
    }
  }, [tourActive, tourStep, step, updateRect])

  // Dismiss on Escape
  useEffect(() => {
    if (!tourActive) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismissTour()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [tourActive, dismissTour])

  if (!tourActive || !step) return null

  // Spotlight cutout padding
  const pad = 8
  const cutout = targetRect
    ? {
        top: targetRect.top - pad,
        left: targetRect.left - pad,
        width: targetRect.width + pad * 2,
        height: targetRect.height + pad * 2,
      }
    : null

  // Tooltip positioning
  const tooltipStyle = computeTooltipPosition(cutout, step.side)

  return (
    <div
      className={`fixed inset-0 z-[100] transition-opacity duration-300 ${
        visible ? 'opacity-100' : 'opacity-0'
      }`}
    >
      {/* Overlay with cutout */}
      <svg className="absolute inset-0 w-full h-full pointer-events-auto" onClick={dismissTour}>
        <defs>
          <mask id="tour-mask">
            <rect width="100%" height="100%" fill="white" />
            {cutout && (
              <rect
                x={cutout.left}
                y={cutout.top}
                width={cutout.width}
                height={cutout.height}
                rx={8}
                fill="black"
              />
            )}
          </mask>
        </defs>
        <rect
          width="100%"
          height="100%"
          fill="rgba(0, 0, 0, 0.6)"
          mask="url(#tour-mask)"
        />
      </svg>

      {/* Spotlight ring around target */}
      {cutout && (
        <div
          className="absolute rounded-lg border-2 border-primary/60 pointer-events-none transition-all duration-300"
          style={{
            top: cutout.top,
            left: cutout.left,
            width: cutout.width,
            height: cutout.height,
          }}
        />
      )}

      {/* Tooltip card */}
      <div
        className="absolute pointer-events-auto transition-all duration-300"
        style={tooltipStyle}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-card/95 backdrop-blur-xl rounded-xl border border-border shadow-2xl p-4 w-72">
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className="text-sm font-semibold text-heading">{step.title}</h3>
            <button
              onClick={dismissTour}
              className="text-muted-foreground hover:text-foreground transition-colors shrink-0 mt-0.5"
              aria-label="Dismiss tour"
            >
              <X className="size-3.5" />
            </button>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed mb-4">
            {step.body}
          </p>
          <div className="flex items-center justify-between">
            <StepDots current={tourStep} total={TOUR_STEP_COUNT} />
            <div className="flex items-center gap-2">
              {!isLast && (
                <button
                  onClick={dismissTour}
                  className="text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  Skip
                </button>
              )}
              <button
                onClick={advanceTour}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors"
              >
                {isLast ? 'Done' : 'Next'}
                {!isLast && <ChevronRight className="size-3" />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function computeTooltipPosition(
  cutout: Rect | null,
  side: TourStep['side'],
): React.CSSProperties {
  const gap = 16
  const tooltipW = 288 // w-72 = 18rem = 288px

  // Center-screen fallback when no target
  if (!cutout) {
    return {
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
    }
  }

  const vw = window.innerWidth
  const vh = window.innerHeight

  switch (side) {
    case 'right': {
      const left = Math.min(cutout.left + cutout.width + gap, vw - tooltipW - 16)
      const top = Math.max(16, cutout.top + cutout.height / 2 - 60)
      return { top: Math.min(top, vh - 200), left }
    }
    case 'left': {
      const left = Math.max(16, cutout.left - tooltipW - gap)
      const top = Math.max(16, cutout.top + cutout.height / 2 - 60)
      return { top: Math.min(top, vh - 200), left }
    }
    case 'bottom': {
      const top = cutout.top + cutout.height + gap
      const left = Math.max(16, Math.min(cutout.left + cutout.width / 2 - tooltipW / 2, vw - tooltipW - 16))
      return { top: Math.min(top, vh - 200), left }
    }
    case 'top': {
      const top = Math.max(16, cutout.top - gap - 180)
      const left = Math.max(16, Math.min(cutout.left + cutout.width / 2 - tooltipW / 2, vw - tooltipW - 16))
      return { top, left }
    }
  }
}
