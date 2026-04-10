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
import { WelcomeOverlay } from '@/components/hud/WelcomeOverlay'
import { useUIStore } from '@/stores/ui'
import { useIsMobile } from '@/hooks/useIsMobile'

export default function HudOverlay() {
  const sidebarOpen = useUIStore(s => s.sidebarOpen)
  const isMobile = useIsMobile()

  const complianceLeft = (sidebarOpen && !isMobile) ? '332px' : '12px'

  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      {/* Welcome overlay - shown on first load before antenna placed */}
      <WelcomeOverlay />

      {/* Compliance panel - left side, offset past sidebar when open (desktop only) */}
      <div
        className="absolute top-3 pointer-events-auto transition-all duration-200"
        style={{ left: complianceLeft, maxWidth: '320px' }}
      >
        <CompliancePanel />
      </div>

      {/* Color legends - right edge, vertically centered, stacked */}
      <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-auto flex flex-col gap-2">
        <ColorLegend />
        <LSPLegend />
      </div>

      {/* Status bar - bottom center */}
      <div className="pointer-events-auto">
        <StatusBar />
      </div>

      {/* Server info - bottom right */}
      <ServerInfoBadge />

      {/* Notification toasts - bottom left */}
      <NotificationToast />

      {/* Touch controls - mobile only, hidden when sidebar is open */}
      {isMobile && !sidebarOpen && <TouchControls />}

      {/* Keyboard shortcut help modal */}
      <KeyboardHelp />

      {/* Antenna placement hint - shown after welcome dismissed, before antenna placed */}
      <AntennaHint />
      <CoverageHud />
    </div>
  )
}
