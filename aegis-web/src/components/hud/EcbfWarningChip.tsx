import { useState } from 'react'
import { AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EcbfWarningChipProps {
  warnings: string[]
  className?: string
  compact?: boolean
}

const HEADLINE = 'ECBF precoder fell back to a safety baseline'
const EXPLAINER =
  'The exposure-constrained beamformer could not satisfy the absorption budget. ' +
  'The result below uses a min-absorption fallback, not the precoder you selected.'

export default function EcbfWarningChip({ warnings, className, compact = false }: EcbfWarningChipProps) {
  const [expanded, setExpanded] = useState(false)
  if (!warnings || warnings.length === 0) return null

  return (
    <div
      data-testid="ecbf-warning-chip"
      className={cn(
        'px-1.5 py-1.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300',
        className,
      )}
    >
      <button
        type="button"
        onClick={() => setExpanded(v => !v)}
        className="flex items-start gap-1.5 w-full text-left"
        aria-expanded={expanded}
      >
        <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="text-[10px] leading-tight font-semibold flex items-center gap-1">
            {HEADLINE}
            {expanded ? (
              <ChevronDown className="w-3 h-3 opacity-70" />
            ) : (
              <ChevronRight className="w-3 h-3 opacity-70" />
            )}
          </div>
          {!compact && (
            <div className="text-[10px] leading-tight opacity-80 mt-0.5">{EXPLAINER}</div>
          )}
        </div>
      </button>
      {expanded && (
        <ul className="mt-1.5 pl-5 list-disc text-[10px] leading-snug opacity-90 space-y-0.5">
          {warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
