import { PanelLeft, Box, Share2, BookOpen, Keyboard, CirclePlay } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore, selectSidebarOpen } from '@/stores/ui'
import { useMIMOStore } from '@/stores/mimo'
import { useCoverageStore } from '@/stores/coverage'
import { useAntennaStore } from '@/stores/antenna'

import { cn } from '@/lib/utils'
import type { DosimetryStats } from '@/api/types'
import SessionTimer from '@/components/layout/SessionTimer'
import UserBadges from '@/components/hud/UserBadges'
import BugReporter from '@/components/hud/bugReporter'
import { ScenarioDropdown } from '@/components/hud/ScenarioDropdown'
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import { generateShareUrl } from '@/lib/shareLink'

function ComplianceBadge({ stats }: { stats: DosimetryStats | null }) {
  if (!stats) {
    return (
      <Badge variant="outline" className="text-muted-foreground border-muted-foreground/30 font-mono text-xs">
        --
      </Badge>
    )
  }
  if (stats.compliant == null) {
    return (
      <Tooltip>
        <TooltipTrigger className="cursor-help">
          <Badge variant="outline" className="text-amber-400/80 border-amber-400/30 font-mono text-xs">
            N/A
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          {stats.warning ?? 'Compliance check not available at this frequency'}
        </TooltipContent>
      </Tooltip>
    )
  }

  const compliant = stats.compliant

  if (!compliant) {
    return (
      <Badge className="bg-destructive/20 text-destructive border-destructive/30 font-mono text-xs">
        FAIL
      </Badge>
    )
  }

  // WARN when any check exceeds 80% of the limit but still passes
  const isWarn = stats.compliance?.checks?.some(c => c.pass && c.ratio > 0.8)
  if (isWarn) {
    return (
      <Tooltip>
        <TooltipTrigger className="cursor-help">
          <Badge className="bg-amber-400/20 text-amber-400 border-amber-400/30 font-mono text-xs">
            WARN
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          Compliant but within 20% of ICNIRP limit
        </TooltipContent>
      </Tooltip>
    )
  }

  return (
    <Badge className="bg-success/20 text-success border-success/30 font-mono text-xs">
      PASS
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

  const tooltipLines = corrections.length > 0
    ? corrections.map(c => ({ F: 'Fresnel T(θ)', P: 'Polarisation', C: 'Curvature', D: 'Diffraction' })[c] ?? c)
    : null

  const pill = (
    <span className="inline-flex items-center rounded-full bg-primary/15 border border-primary/20 px-2.5 py-0.5 text-xs font-medium text-primary font-mono">
      {label}
    </span>
  )

  if (!tooltipLines) return pill

  return (
    <Tooltip>
      <TooltipTrigger className="cursor-help">{pill}</TooltipTrigger>
      <TooltipContent side="bottom">
        Active corrections: {tooltipLines.join(', ')}
      </TooltipContent>
    </Tooltip>
  )
}


export default function Toolbar() {
  const { stats } = useActiveSimulation()
  const { viewerConfig } = useSceneStore()
  const { wireframe, toggleSidebar, toggleWireframe, setStatusMessage, toggleHelp, startTour } = useUIStore()
  const sidebarOpen = useUIStore(selectSidebarOpen)
  const mimoEnabled = useMIMOStore(s => s.enabled)

  const activeScenario = useUIStore(s => s.activeScenario)
  const scenario = activeScenario
    ? (viewerConfig?.scenarios?.[activeScenario]?.description ?? activeScenario)
    : (viewerConfig?.active_scenario_description ?? viewerConfig?.active_scenario ?? null)

  async function handleShare() {
    const url = generateShareUrl()
    await navigator.clipboard.writeText(url)
    setStatusMessage('Link copied to clipboard')
    setTimeout(() => setStatusMessage(null), 3000)
  }

  return (
    <header className="h-11 flex items-center justify-between px-3 bg-card/80 backdrop-blur-sm border-b border-border shrink-0 gap-4 relative z-30">
      {/* Left: wordmark + docs + scenario */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={() => {
            // Reset scene state
            useSimulationStore.getState().clearResults()
            useSimulationStore.setState({ antennaPos: null })
            useAntennaStore.getState().clearAntennas()
            useSceneStore.getState().clearScene()
            useUIStore.getState().setActiveScenario(null)
            useUIStore.getState().setWelcomeDismissed(false)
            useUIStore.getState().dismissTour()
            useCoverageStore.getState().setEnabled(false)
            // Strip URL params and hash
            history.replaceState(null, '', window.location.pathname)
          }}
          className="text-base font-semibold text-heading shrink-0 hover:text-primary transition-colors cursor-pointer"
        >
          aegis
        </button>
        <a
          href="https://docs.aegis.waves-ugent.be"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden md:inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-0.5 text-xs font-medium text-primary hover:bg-primary/20 transition-colors shrink-0"
        >
          <BookOpen className="size-3" />
          Docs
        </a>
        <ScenarioDropdown />
        {scenario && (
          <span className="text-xs text-muted-foreground truncate hidden sm:block">{scenario}</span>
        )}
      </div>

      {/* Center-left: compliance + level */}
      <div className="flex items-center gap-2 shrink-0">
        {mimoEnabled && <UserBadges />}
        <ComplianceBadge stats={stats} />
        <ModePill />
      </div>

      {/* Right: session timer + icon buttons */}
      <div className="flex items-center gap-1 shrink-0">
        <span className="hidden md:inline-flex"><SessionTimer /></span>

        <Tooltip>
          <TooltipTrigger
            onClick={() => { void handleShare() }}
            data-testid="toolbar-share"
            className={cn(
              'hidden md:inline-flex items-center justify-center size-7 rounded-md transition-colors',
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
              'hidden md:inline-flex items-center justify-center size-7 rounded-md transition-colors',
              'hover:bg-muted text-muted-foreground hover:text-foreground',
              wireframe && 'bg-muted text-foreground',
            )}
            aria-label="Toggle wireframe"
          >
            <Box className="size-4" />
          </TooltipTrigger>
          <TooltipContent>Wireframe</TooltipContent>
        </Tooltip>

        <BugReporter />

        <div className="hidden md:block w-px h-4 bg-border/60 mx-0.5" />

        <Tooltip>
          <TooltipTrigger
            onClick={startTour}
            className={cn(
              'hidden md:inline-flex items-center justify-center size-7 rounded-md transition-colors',
              'hover:bg-muted text-muted-foreground hover:text-foreground',
            )}
            aria-label="Guided tour"
          >
            <CirclePlay className="size-4" />
          </TooltipTrigger>
          <TooltipContent>Guided tour</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger
            data-tour="help-button"
            onClick={toggleHelp}
            className={cn(
              'hidden md:inline-flex items-center justify-center size-7 rounded-md transition-colors',
              'hover:bg-muted text-muted-foreground hover:text-foreground',
            )}
            aria-label="Keyboard shortcuts (?)"
          >
            <Keyboard className="size-4" />
          </TooltipTrigger>
          <TooltipContent>Keyboard shortcuts (?)</TooltipContent>
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
