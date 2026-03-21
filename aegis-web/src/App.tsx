import { useConfig } from '@/hooks/useConfig'
import AppShell from '@/components/layout/AppShell'

export default function App() {
  const { status, error } = useConfig()

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
