import { PanelLeft, Box, AlignCenter, AlignJustify, LayoutGrid, Focus, Video, Share2, BookOpen, Users } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useMIMOStore } from '@/stores/mimo'
import type { CameraPreset } from '@/stores/ui'
import { cn } from '@/lib/utils'
import type { DosimetryStats } from '@/api/types'
import SessionTimer from '@/components/layout/SessionTimer'
import UserBadges from '@/components/hud/UserBadges'
import { generateShareUrl } from '@/lib/shareLink'

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

function ModePill() {
  const mode = useSimulationStore((s) => s.mode)
  const fresnel = useSimulationStore((s) => s.fresnel)
  const polarisation = useSimulationStore((s) => s.polarisation)
  const curvature = useSimulationStore((s) => s.curvature)
  const diffraction = useSimulationStore((s) => s.diffraction)

  const corrections: string[] = []
  if (mode === 'spatial') {
    if (fresnel) corrections.push('F')
    if (polarisation) corrections.push('P')
    if (curvature) corrections.push('C')
    if (diffraction) corrections.push('D')
  }

  const modeLabel = mode.charAt(0).toUpperCase() + mode.slice(1)
  const label = corrections.length > 0
    ? `${modeLabel} +${corrections.join('')}`
    : modeLabel

  return (
    <span className="inline-flex items-center rounded-full bg-primary/15 border border-primary/20 px-2.5 py-0.5 text-xs font-medium text-primary font-mono">
      {label}
    </span>
  )
}

const CAMERA_PRESETS: Array<{ preset: CameraPreset & string; label: string; icon: React.ReactNode }> = [
  { preset: 'front', label: 'Front view', icon: <AlignCenter className="size-4" /> },
  { preset: 'side', label: 'Side view', icon: <AlignJustify className="size-4" /> },
  { preset: 'top', label: 'Top view', icon: <LayoutGrid className="size-4" /> },
  { preset: 'focus', label: 'Focus body', icon: <Focus className="size-4" /> },
]

export default function Toolbar() {
  const { stats } = useSimulationStore()
  const { viewerConfig } = useSceneStore()
  const { sidebarOpen, wireframe, cameraMode, toggleSidebar, toggleWireframe, setCameraPreset, setCameraMode, setStatusMessage } = useUIStore()
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const setMIMOEnabled = useMIMOStore(s => s.setEnabled)

  const scenario = viewerConfig?.active_scenario_description ?? viewerConfig?.active_scenario ?? null

  function handleCameraPreset(preset: CameraPreset & string) {
    setCameraPreset(preset)
    // Clear after a tick so the controller fires on every click (even the same preset)
    setTimeout(() => setCameraPreset(null), 50)
  }

  async function handleShare() {
    const url = generateShareUrl()
    await navigator.clipboard.writeText(url)
    setStatusMessage('Link copied to clipboard')
    setTimeout(() => setStatusMessage(null), 3000)
  }

  return (
    <header className="h-11 flex items-center justify-between px-3 bg-card/80 backdrop-blur-sm border-b border-border shrink-0 gap-4">
      {/* Left: wordmark + docs + scenario */}
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-sm font-bold tracking-wider text-heading shrink-0">AEGIS</span>
        <a
          href="https://docs.aegis.waves-ugent.be"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-0.5 text-xs font-medium text-primary hover:bg-primary/20 transition-colors shrink-0"
        >
          <BookOpen className="size-3" />
          Docs
        </a>
        {scenario && (
          <span className="text-xs text-muted-foreground truncate hidden sm:block">{scenario}</span>
        )}
      </div>

      {/* Center-left: compliance + level */}
      <div className="flex items-center gap-2 shrink-0">
        {mimoEnabled ? <UserBadges /> : <ComplianceBadge stats={stats} />}
        <ModePill />
      </div>

      {/* Center: camera presets + follow */}
      <div className="flex items-center gap-1 shrink-0">
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
          <Tooltip>
            <TooltipTrigger
              onClick={() => setCameraMode(cameraMode === 'orbit' ? 'follow' : 'orbit')}
              className={cn(
                'inline-flex items-center justify-center size-7 rounded transition-colors',
                cameraMode === 'follow'
                  ? 'bg-primary/15 text-primary'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground',
              )}
              aria-label="Toggle follow camera"
            >
              <Video className="size-4" />
            </TooltipTrigger>
            <TooltipContent>{cameraMode === 'follow' ? 'Free camera' : 'Follow camera'}</TooltipContent>
          </Tooltip>
        </div>
      </div>

      {/* Right: session timer + icon buttons */}
      <div className="flex items-center gap-1 shrink-0">
        <SessionTimer />

        <Tooltip>
          <TooltipTrigger
            onClick={() => setMIMOEnabled(!mimoEnabled)}
            className={cn(
              'inline-flex items-center justify-center size-7 rounded-md transition-colors',
              'hover:bg-muted text-muted-foreground hover:text-foreground',
              mimoEnabled && 'bg-primary/15 text-primary',
            )}
            aria-label="Toggle MIMO mode"
          >
            <Users className="size-4" />
          </TooltipTrigger>
          <TooltipContent>
            {mimoEnabled ? 'Disable MIMO mode' : 'Enable MIMO mode'}
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger
            onClick={() => { void handleShare() }}
            className={cn(
              'inline-flex items-center justify-center size-7 rounded-md transition-colors',
              'hover:bg-muted text-muted-foreground hover:text-foreground',
            )}
            aria-label="Share link"
          >
            <Share2 className="size-4" />
          </TooltipTrigger>
          <TooltipContent>Copy share link</TooltipContent>
        </Tooltip>

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
