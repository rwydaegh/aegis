import { useEnvironmentStore } from '@/stores/environment'
import { useTerrainStore } from '@/stores/terrain'
import { Loader2 } from 'lucide-react'

export function TerrainSection() {
  const location = useEnvironmentStore((s) => s.location)
  const radius = useEnvironmentStore((s) => s.radius)

  const terrainEnabled = useTerrainStore((s) => s.enabled)
  const terrainMeshData = useTerrainStore((s) => s.meshData)
  const terrainLoading = useTerrainStore((s) => s.loading)
  const terrainError = useTerrainStore((s) => s.error)
  const setTerrainEnabled = useTerrainStore((s) => s.setEnabled)
  const fetchTerrain = useTerrainStore((s) => s.fetchTerrain)

  return (
    <div className="space-y-2 pt-1 border-t border-border">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Terrain
      </p>
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-1.5 text-xs">
          <input
            type="checkbox"
            checked={terrainEnabled}
            onChange={(e) => setTerrainEnabled(e.target.checked)}
            disabled={!terrainMeshData}
          />
          Show terrain
        </label>
        <button
          onClick={() => {
            if (location) {
              void fetchTerrain(location.lat, location.lon, radius)
            }
          }}
          disabled={terrainLoading || !location}
          className="px-3 py-1.5 rounded text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1.5"
        >
          {terrainLoading && <Loader2 className="size-3 animate-spin" />}
          Fetch terrain
        </button>
      </div>
      {terrainMeshData && (
        <p className="text-xs text-muted-foreground">
          {terrainMeshData.hasElevation
            ? `SRTM elevation loaded (${terrainMeshData.elevationRangeM.toFixed(0)} m range)`
            : 'Flat terrain (no SRTM data for this area)'}
        </p>
      )}
      {terrainError && (
        <p className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1.5">
          {terrainError}
        </p>
      )}
    </div>
  )
}
