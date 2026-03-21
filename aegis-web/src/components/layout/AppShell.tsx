import Toolbar from './Toolbar'
import Sidebar from './Sidebar'
import HudOverlay from './HudOverlay'

export default function AppShell() {
  return (
    <div className="h-screen w-screen flex flex-col bg-background">
      <Toolbar />
      <div className="flex-1 relative overflow-hidden">
        <Sidebar />
        {/* R3F Canvas will go here later */}
        <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
          3D Canvas placeholder
        </div>
        <HudOverlay />
      </div>
    </div>
  )
}
