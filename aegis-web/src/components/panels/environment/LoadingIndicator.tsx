import { useEnvironmentStore } from '@/stores/environment'
import { Loader2 } from 'lucide-react'

export function LoadingIndicator() {
  const source = useEnvironmentStore((s) => s.source)
  const loading = useEnvironmentStore((s) => s.loading)

  if (!loading) return null
  if (source !== 'osm' && source !== '3dtiles') return null

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <Loader2 className="size-3 animate-spin" />
      {source === 'osm' ? 'Fetching OSM data...' : 'Fetching tiles...'}
    </div>
  )
}
