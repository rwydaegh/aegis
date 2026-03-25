import StatusBar from '@/components/hud/StatusBar'
import ColorLegend from '@/components/hud/ColorLegend'
import ServerInfoBadge from '@/components/hud/ServerInfoBadge'
import CompliancePanel from '@/components/hud/CompliancePanel'
import NotificationToast from '@/components/hud/NotificationToast'
import { useUIStore } from '@/stores/ui'

export default function HudOverlay() {
  const sidebarOpen = useUIStore(s => s.sidebarOpen)

  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      {/* Compliance panel - left side, offset past sidebar when open */}
      <div
        className="absolute top-3 pointer-events-auto transition-all duration-200"
        style={{ left: sidebarOpen ? '332px' : '12px', maxWidth: '320px' }}
      >
        <CompliancePanel />
      </div>

      {/* Color legend - right edge, vertically centered */}
      <ColorLegend />

      {/* Status bar - bottom center */}
      <div className="pointer-events-auto">
        <StatusBar />
      </div>

      {/* Server info - bottom right */}
      <ServerInfoBadge />

      {/* Notification toasts - bottom left */}
      <NotificationToast />
    </div>
  )
}
