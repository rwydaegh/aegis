import { PanelLeft, Box } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { cn } from '@/lib/utils'
import type { DosimetryStats } from '@/api/types'
import type { ViewerConfig } from '@/api/types'

function ComplianceBadge({ stats }: { stats: DosimetryStats | null }) {
  if (!stats) {
    return (
      <Badge variant="outline" className="text-muted-foreground border-muted-foreground/30 font-mono text-xs">
        --
      </Badge>
    )
  }
  return stats.compliant ? (
    <Badge className="bg-success/20 text-success border-success/30 font-mono text-xs">
      PASS
    </Badge>
  ) : (
    <Badge className="bg-destructive/20 text-destructive border-destructive/30 font-mono text-xs">
      FAIL
    </Badge>
  )
}

function LevelPill({ level, config }: { level: number; config: ViewerConfig | null }) {
  const levelLabel = config?.dosimetry?.fidelity_levels?.find(l => l.value === level)?.label ?? `L${level}`
  return (
    <span className="inline-flex items-center rounded-full bg-primary/15 border border-primary/20 px-2.5 py-0.5 text-xs font-medium text-primary font-mono">
      {levelLabel}
    </span>
  )
}

export default function Toolbar() {
  const { level, stats } = useSimulationStore()
  const { viewerConfig } = useSceneStore()
  const { sidebarOpen, wireframe, toggleSidebar, toggleWireframe } = useUIStore()

  const uiConfig = viewerConfig?.ui as Record<string, unknown> | undefined
  const scenario = typeof uiConfig?.scenario === 'string' ? uiConfig.scenario : null

  return (
    <header className="h-11 flex items-center justify-between px-3 bg-card/80 backdrop-blur-sm border-b border-border shrink-0 gap-4">
      {/* Left: wordmark + scenario */}
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-sm font-bold tracking-wider text-heading shrink-0">AEGIS</span>
        {scenario && (
          <span className="text-xs text-muted-foreground truncate hidden sm:block">{scenario}</span>
        )}
      </div>

      {/* Center-left: compliance + level */}
      <div className="flex items-center gap-2 shrink-0">
        <ComplianceBadge stats={stats} />
        <LevelPill level={level} config={viewerConfig} />
      </div>

      {/* Right: icon buttons */}
      <div className="flex items-center gap-1 shrink-0">
        <Tooltip>
          <TooltipTrigger
            onClick={toggleWireframe}
            className={cn(
              'inline-flex items-center justify-center size-7 rounded-md transition-colors',
              'hover:bg-muted text-muted-foreground hover:text-foreground',
              wireframe && 'bg-muted text-foreground',
            )}
            aria-label="Toggle wireframe"
          >
            <Box className="size-4" />
          </TooltipTrigger>
          <TooltipContent>Wireframe</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger
            onClick={toggleSidebar}
            className={cn(
              'inline-flex items-center justify-center size-7 rounded-md transition-colors',
              'hover:bg-muted text-muted-foreground hover:text-foreground',
              sidebarOpen && 'bg-muted text-foreground',
            )}
            aria-label="Toggle sidebar"
          >
            <PanelLeft className="size-4" />
          </TooltipTrigger>
          <TooltipContent>Toggle sidebar</TooltipContent>
        </Tooltip>
      </div>
    </header>
  )
}
