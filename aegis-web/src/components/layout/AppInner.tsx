import { useEffect } from 'react'
import { useConfig } from '@/hooks/useConfig'
import AppShell from '@/components/layout/AppShell'
import { deserializeShareLink, applyShareState } from '@/lib/shareLink'
import { useScenario } from '@/hooks/useScenario'

export default function AppInner() {
  const { status, error } = useConfig()
  const { loadScenario } = useScenario()

  // Hydrate from URL fragment once config has loaded (share link overrides server defaults)
  useEffect(() => {
    if (status !== 'ready') return
    const hash = window.location.hash
    if (hash.startsWith('#s=')) {
      const state = deserializeShareLink(hash.slice(3))
      applyShareState(state)
      window.history.replaceState(null, '', window.location.pathname)
    }
  }, [status])

  // Load scenario from URL param once config is ready (share links take precedence)
  useEffect(() => {
    if (status !== 'ready') return
    if (window.location.hash.startsWith('#s=')) return

    const params = new URLSearchParams(window.location.search)
    const scenarioName = params.get('scenario')
    if (scenarioName) {
      loadScenario(scenarioName)
    }
  }, [status, loadScenario])

  if (status === 'loading') {
    return (
      <div className="h-screen w-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-muted border-t-primary rounded-full animate-spin mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">Connecting to server...</p>
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="h-screen w-screen bg-background flex items-center justify-center">
        <div className="text-center max-w-md">
          <p className="text-destructive font-medium mb-2">Connection failed</p>
          <p className="text-muted-foreground text-sm">{error}</p>
          <p className="text-muted-foreground text-xs mt-4">
            Make sure the AEGIS server is running on port 5000
          </p>
        </div>
      </div>
    )
  }

  return <AppShell />
}
