import { PanelLeft, Box, AlignCenter, AlignJustify, LayoutGrid, Focus, RotateCcw, Video } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import type { CameraPreset } from '@/stores/ui'
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

const CAMERA_PRESETS: Array<{ preset: CameraPreset & string; label: string; icon: React.ReactNode }> = [
  { preset: 'front', label: 'Front view', icon: <AlignCenter className="size-4" /> },
  { preset: 'side', label: 'Side view', icon: <AlignJustify className="size-4" /> },
  { preset: 'top', label: 'Top view', icon: <LayoutGrid className="size-4" /> },
  { preset: 'focus', label: 'Focus body', icon: <Focus className="size-4" /> },
  { preset: 'reset', label: 'Reset camera', icon: <RotateCcw className="size-4" /> },
]

export default function Toolbar() {
  const { level, stats } = useSimulationStore()
  const { viewerConfig } = useSceneStore()
  const { sidebarOpen, wireframe, cameraMode, toggleSidebar, toggleWireframe, setCameraPreset, setCameraMode } = useUIStore()

  const uiConfig = viewerConfig?.ui as Record<string, unknown> | undefined
  const scenario = typeof uiConfig?.scenario === 'string' ? uiConfig.scenario : null

  function handleCameraPreset(preset: CameraPreset & string) {
    setCameraPreset(preset)
    // Clear after a tick so the controller fires on every click (even the same preset)
    setTimeout(() => setCameraPreset(null), 50)
  }

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

      {/* Center: camera mode + presets */}
      <div className="flex items-center gap-1 shrink-0">
        <Tooltip>
          <TooltipTrigger
            onClick={() => setCameraMode(cameraMode === 'orbit' ? 'follow' : 'orbit')}
            className={cn(
              'inline-flex items-center justify-center size-7 rounded-md border transition-colors',
              cameraMode === 'follow'
                ? 'bg-primary/15 border-primary/30 text-primary'
                : 'border-border hover:bg-muted text-muted-foreground hover:text-foreground',
            )}
            aria-label="Toggle follow camera"
          >
            <Video className="size-4" />
          </TooltipTrigger>
          <TooltipContent>{cameraMode === 'follow' ? 'Free camera' : 'Follow camera'}</TooltipContent>
        </Tooltip>

        <div className="flex items-center gap-0.5 border border-border rounded-md p-0.5">
          {CAMERA_PRESETS.map(({ preset, label, icon }) => (
            <Tooltip key={preset}>
              <TooltipTrigger
                onClick={() => handleCameraPreset(preset)}
                className={cn(
                  'inline-flex items-center justify-center size-7 rounded transition-colors',
                  'hover:bg-muted text-muted-foreground hover:text-foreground',
                )}
                aria-label={label}
              >
                {icon}
              </TooltipTrigger>
              <TooltipContent>{label}</TooltipContent>
            </Tooltip>
          ))}
        </div>
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
