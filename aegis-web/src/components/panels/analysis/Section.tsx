import type { ReactNode } from 'react'

// ---------------------------------------------------------------------------
// Collapsible section
// ---------------------------------------------------------------------------

export function Section({
  title,
  open,
  onToggle,
  children,
}: {
  title: string
  open: boolean
  onToggle: () => void
  children: ReactNode
}) {
  return (
    <div className="border-b border-border/50 pb-2 mb-2 last:border-b-0">
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full text-xs font-medium py-1 cursor-pointer text-foreground"
      >
        <span>{title}</span>
        <span className="text-muted-foreground">{open ? '−' : '+'}</span>
      </button>
      {open && <div className="mt-1">{children}</div>}
    </div>
  )
}
