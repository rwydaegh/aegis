import Toolbar from './Toolbar'
import Sidebar from './Sidebar'
import HudOverlay from './HudOverlay'
import { SceneErrorBoundary } from '@/components/scene/ErrorBoundary'
import SceneRoot from '@/components/scene/SceneRoot'

export default function AppShell() {
  return (
    <div className="h-screen w-screen flex flex-col bg-background">
      <Toolbar />
      <div className="flex-1 relative overflow-hidden">
        <Sidebar />
        <SceneErrorBoundary>
          <SceneRoot />
        </SceneErrorBoundary>
        <HudOverlay />
      </div>
    </div>
  )
}
