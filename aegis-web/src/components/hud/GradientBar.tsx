import type { ReactNode } from 'react'

const BAR_HEIGHT = 240
const BAR_WIDTH = 16

export interface GradientBarTick {
  label: string
  pct: number
}

interface GradientBarProps {
  gradient: string
  ticks: GradientBarTick[]
  title: ReactNode
  shimmer?: boolean
  footer?: ReactNode
}

export default function GradientBar({ gradient, ticks, title, shimmer, footer }: GradientBarProps) {
  return (
      <div className={`bg-card/80 backdrop-blur-md rounded-lg border border-border px-3 py-2.5 ${shimmer ? 'shimmer-panel' : ''}`}>
        {/* Title row */}
        <div className="flex items-center justify-between gap-1.5 mb-2">
          {title}
        </div>

        {/* Gradient bar with tick labels */}
        <div className="flex gap-2">
          {/* Labels column */}
          <div className="relative" style={{ height: BAR_HEIGHT, width: 60 }}>
            {ticks.map(({ label, pct }, i) => (
              <span
                key={i}
                className="absolute right-0 text-xs font-mono tabular-nums text-foreground whitespace-nowrap"
                style={{ top: pct * BAR_HEIGHT - 7 }}
              >
                {label}
              </span>
            ))}
          </div>

          {/* Tick marks + gradient bar */}
          <div className="relative" style={{ height: BAR_HEIGHT }}>
            <div
              className="rounded-sm border border-border/60"
              style={{ background: gradient, height: BAR_HEIGHT, width: BAR_WIDTH }}
            />
            {ticks.map(({ pct }, i) => (
              <div
                key={i}
                className="absolute bg-foreground/40"
                style={{ top: pct * BAR_HEIGHT, left: -4, width: 4, height: 1 }}
              />
            ))}
          </div>
        </div>

        {footer}
      </div>
  )
}
