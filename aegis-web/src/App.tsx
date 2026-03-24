import { useEffect } from 'react'
import { useConfig } from '@/hooks/useConfig'
import AppShell from '@/components/layout/AppShell'
import LoginGate from '@/components/layout/LoginGate'
import { deserializeShareLink, applyShareState } from '@/lib/shareLink'

export default function App() {
  const { status, error } = useConfig()

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

  return (
    <LoginGate>
      <AppShell />
    </LoginGate>
  )
}
