import { useEnvironmentStore } from '@/stores/environment'
import { useSimulationStore } from '@/stores/simulation'
import { useMIMOStore } from '@/stores/mimo'
import { Loader2, RotateCw } from 'lucide-react'

export function ReloadButton() {
  const loading = useEnvironmentStore((s) => s.loading)
  const geocoding = useEnvironmentStore((s) => s.geocoding)
  const reloadAroundPositions = useEnvironmentStore((s) => s.reloadAroundPositions)
  const bodyOffset = useSimulationStore((s) => s.bodyOffset)
  const mimoEnabled = useMIMOStore((s) => s.enabled)
  const mimoUsers = useMIMOStore((s) => s.users)

  const busy = loading || geocoding

  const handleReload = () => {
    if (mimoEnabled && mimoUsers.size > 0) {
      const positions = [...mimoUsers.values()].map((u) => u.position)
      void reloadAroundPositions(positions)
    } else {
      void reloadAroundPositions([bodyOffset])
    }
  }

  return (
    <button
      onClick={handleReload}
      disabled={busy}
      className="w-full px-3 py-1.5 rounded text-xs font-medium bg-muted text-muted-foreground hover:text-foreground disabled:opacity-50 flex items-center justify-center gap-1.5"
    >
      {loading ? (
        <Loader2 className="size-3 animate-spin" />
      ) : (
        <RotateCw className="size-3" />
      )}
      {mimoEnabled ? 'Reload around all users' : 'Reload around body'}
    </button>
  )
}
