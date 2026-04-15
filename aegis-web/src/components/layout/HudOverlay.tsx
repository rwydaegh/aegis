import { useEffect, useRef } from 'react'
import StatusBar from '@/components/hud/StatusBar'
import ColorLegend from '@/components/hud/ColorLegend'
import LSPLegend from '@/components/hud/LSPLegend'
import ServerInfoBadge from '@/components/hud/ServerInfoBadge'
import CompliancePanel from '@/components/hud/CompliancePanel'
import NotificationToast from '@/components/hud/NotificationToast'
import TouchControls from '@/components/hud/TouchControls'
import KeyboardHelp from '@/components/hud/KeyboardHelp'
import { AntennaHint } from '@/components/hud/AntennaHint'
import { CoverageHud } from '@/components/hud/CoverageHud'
import { CoverageTooltip } from '@/components/hud/CoverageTooltip'
import { DataQualityHud } from '@/components/hud/DataQualityHud'
import CameraWidget from '@/components/hud/CameraWidget'
import HudToggle from '@/components/hud/HudToggle'
import { WelcomeOverlay } from '@/components/hud/WelcomeOverlay'
import GuidedTour from '@/components/hud/GuidedTour'
import { useUIStore, selectSidebarOpen } from '@/stores/ui'
import { useSimulationStore } from '@/stores/simulation'
import { useIsMobile, useIsTouchDevice } from '@/hooks/useIsMobile'

export default function HudOverlay() {
  const sidebarMode = useUIStore(s => s.sidebarMode)
  const sidebarOpen = useUIStore(selectSidebarOpen)
  const tourCompleted = useUIStore(s => s.tourCompleted)
  const tourActive = useUIStore(s => s.tourActive)
  const startTour = useUIStore(s => s.startTour)
  const antennaPos = useSimulationStore(s => s.antennaPos)
  const isMobile = useIsMobile()
  const isTouchDevice = useIsTouchDevice()

  // Auto-start tour after first antenna placement (only once, only on desktop)
  const tourTriggeredRef = useRef(false)
  useEffect(() => {
    if (antennaPos && !tourCompleted && !tourActive && !tourTriggeredRef.current && !isMobile) {
      tourTriggeredRef.current = true
      // Small delay so the user sees the heatmap appear first
      const timer = setTimeout(startTour, 1500)
      return () => clearTimeout(timer)
    }
  }, [antennaPos, tourCompleted, tourActive, startTour, isMobile])

  const complianceLeft = isMobile
    ? '12px'
    : sidebarMode === 'expanded'
      ? '332px'
      : sidebarMode === 'rail'
        ? '60px'
        : '12px'

  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      {/* Welcome overlay - shown on first load before antenna placed */}
      <WelcomeOverlay />

      {/* Compliance panel - left side, offset past sidebar when open (desktop only) */}
      <div
        data-tour="compliance"
        className="absolute top-3 pointer-events-auto transition-all duration-200"
        style={{ left: complianceLeft, maxWidth: '320px' }}
      >
        <HudToggle id="compliance">
          <CompliancePanel />
        </HudToggle>
      </div>

      {/* Color legends - right edge, vertically centered, stacked */}
      <div data-tour="color-legend" className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-auto flex flex-col gap-2">
        <HudToggle id="legend">
          <div className="flex flex-col gap-2">
            <ColorLegend />
            <LSPLegend />
          </div>
        </HudToggle>
      </div>

      {/* Status bar - bottom center */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 pointer-events-auto">
        <StatusBar />
      </div>

      {/* Server info - bottom right */}
      <div className="absolute bottom-3 right-3">
        <HudToggle id="server">
          <ServerInfoBadge />
        </HudToggle>
      </div>

      {/* Notification toasts - bottom left */}
      <NotificationToast />

      {/* Touch controls - mobile only, hidden when sidebar is open */}
      {isTouchDevice && !sidebarOpen && <TouchControls />}

      {/* Keyboard shortcut help modal */}
      <KeyboardHelp />

      {/* Camera viewport controls */}
      <div className="absolute bottom-14 right-3">
        <HudToggle id="camera">
          <CameraWidget />
        </HudToggle>
      </div>

      {/* Antenna placement hint - shown after welcome dismissed, before antenna placed */}
      <AntennaHint />
      <div className="absolute bottom-16 left-4 flex flex-col gap-2">
        <HudToggle id="coverage">
          <CoverageHud />
        </HudToggle>
        <HudToggle id="dataQuality">
          <DataQualityHud />
        </HudToggle>
      </div>

      {/* Guided tour overlay */}
      <GuidedTour />

      {/* Coverage site hover tooltip - fixed at cursor position */}
      <CoverageTooltip />
    </div>
  )
}
