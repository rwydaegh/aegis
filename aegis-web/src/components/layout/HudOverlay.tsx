import StatsCard from '@/components/hud/StatsCard'
import StatusBar from '@/components/hud/StatusBar'
import ColorLegend from '@/components/hud/ColorLegend'
import ServerInfoBadge from '@/components/hud/ServerInfoBadge'
import CompliancePanel from '@/components/hud/CompliancePanel'

export default function HudOverlay() {
  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      {/* Stats card - top right */}
      <div className="absolute top-3 right-3 pointer-events-auto">
        <StatsCard />
      </div>

      {/* Compliance panel - top left below sidebar area */}
      <div className="absolute top-3 left-3 pointer-events-auto" style={{ maxWidth: '320px' }}>
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
    </div>
  )
}
