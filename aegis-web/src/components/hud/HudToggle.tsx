import type { ReactNode } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { useUIStore } from '@/stores/ui'
import { useIsTouchDevice } from '@/hooks/useIsMobile'

const LABELS: Record<string, string> = {
  compliance: 'Compliance',
  legend: 'Legend',
  camera: 'Camera',
  server: 'Server',
  status: 'Status',
  coverage: 'Coverage',
}

interface HudToggleProps {
  id: string
  children: ReactNode
}

export default function HudToggle({ id, children }: HudToggleProps) {
  const hidden = useUIStore(s => s.hiddenWidgets.has(id))
  const toggle = useUIStore(s => s.toggleWidget)
  const isTouch = useIsTouchDevice()

  if (hidden) {
    return (
      <button
        onClick={() => toggle(id)}
        className="pointer-events-auto flex items-center gap-1 rounded-full
          bg-card/60 backdrop-blur-sm border border-border/50 px-2 py-1
          text-muted-foreground hover:text-foreground hover:bg-card/80
          transition-colors cursor-pointer"
        aria-label={`Show ${LABELS[id] ?? id}`}
      >
        <EyeOff className="size-3.5" />
        <span className="text-[10px] font-medium">{LABELS[id] ?? id}</span>
      </button>
    )
  }

  return (
    <div className="relative group/hud">
      {children}
      <button
        onClick={() => toggle(id)}
        className={`absolute top-1 right-1 z-10 pointer-events-auto
          inline-flex items-center justify-center size-5 rounded-full
          bg-card/70 border border-border/40 text-muted-foreground
          hover:text-foreground hover:bg-card/90 transition-all cursor-pointer
          ${isTouch ? 'opacity-70' : 'opacity-0 group-hover/hud:opacity-70'}`}
        aria-label={`Hide ${LABELS[id] ?? id}`}
      >
        <Eye className="size-3" />
      </button>
    </div>
  )
}
