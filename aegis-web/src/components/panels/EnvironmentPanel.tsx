import { useRef, useState } from 'react'
import * as Sentry from '@sentry/react'
import { useEnvironmentStore } from '@/stores/environment'
import { EnvironmentEmptyState } from './EnvironmentEmptyState'
import type { EnvironmentSource } from '@/stores/environment'
import { useSceneStore } from '@/stores/scene'
import { useTerrainStore } from '@/stores/terrain'
import { useUIStore } from '@/stores/ui'
import { useSimulationStore } from '@/stores/simulation'
import { useMIMOStore } from '@/stores/mimo'
import { Loader2, Search, RotateCw } from 'lucide-react'

const SOURCE_OPTIONS: { value: EnvironmentSource; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'voxels', label: 'Voxels' },
  { value: 'osm', label: 'OSM' },
  { value: '3dtiles', label: '3D Tiles' },
]

const labelClass = 'text-xs text-muted-foreground block mb-1'
const inputClass =
  'w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground'

export default function EnvironmentPanel() {
  const terrainEnabled = useTerrainStore((s) => s.enabled)
  const terrainMeshData = useTerrainStore((s) => s.meshData)
  const terrainLoading = useTerrainStore((s) => s.loading)
  const terrainError = useTerrainStore((s) => s.error)
  const setTerrainEnabled = useTerrainStore((s) => s.setEnabled)
  const fetchTerrain = useTerrainStore((s) => s.fetchTerrain)

  const source = useEnvironmentStore((s) => s.source)
  const location = useEnvironmentStore((s) => s.location)
  const locationQuery = useEnvironmentStore((s) => s.locationQuery)
  const locationFormatted = useEnvironmentStore((s) => s.locationFormatted)
  const radius = useEnvironmentStore((s) => s.radius)
  const geometricError = useEnvironmentStore((s) => s.geometricError)
  const osmOptions = useEnvironmentStore((s) => s.osmOptions)
  const loading = useEnvironmentStore((s) => s.loading)
  const geocoding = useEnvironmentStore((s) => s.geocoding)
  const error = useEnvironmentStore((s) => s.error)
  const setSource = useEnvironmentStore((s) => s.setSource)
  const setLocationQuery = useEnvironmentStore((s) => s.setLocationQuery)
  const setRadius = useEnvironmentStore((s) => s.setRadius)
  const setGeometricError = useEnvironmentStore((s) => s.setGeometricError)
  const setOsmOptions = useEnvironmentStore((s) => s.setOsmOptions)
  const geocodeAndFetch = useEnvironmentStore((s) => s.geocodeAndFetch)
  const fetchGeoJSON = useEnvironmentStore((s) => s.fetchGeoJSON)
  const exportForRT = useEnvironmentStore((s) => s.exportForRT)

  const reloadAroundPositions = useEnvironmentStore((s) => s.reloadAroundPositions)

  const setCameraMode = useUIStore((s) => s.setCameraMode)
  const setCameraPreset = useUIStore((s) => s.setCameraPreset)
  const voxelData = useSceneStore((s) => s.voxelData)
  const bodyOffset = useSimulationStore((s) => s.bodyOffset)
  const mimoEnabled = useMIMOStore((s) => s.enabled)
  const mimoUsers = useMIMOStore((s) => s.users)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [geojsonFileName, setGeoJsonFileName] = useState<string | null>(null)

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
    <div className="space-y-3 text-sm">
      {/* Source selector */}
      <div>
        <label className={labelClass}>Source</label>
        <div className="grid grid-cols-4 gap-1">
          {SOURCE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => {
                setSource(opt.value)
                if (opt.value === '3dtiles') {
                  setCameraMode('globe')
                } else if (source === '3dtiles') {
                  setCameraMode('orbit')
                  // Reset camera from globe-scale ECEF back to local scene
                  setCameraPreset('reset')
                }
              }}
              className={`px-2 py-1.5 rounded text-xs font-medium transition-colors ${
                source === opt.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:text-foreground'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Empty state CTA - shown when source is 'none' */}
      <EnvironmentEmptyState />

      {/* Voxels status */}
      {source === 'voxels' && (
        <div className="space-y-2 pt-1 border-t border-border">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Voxels
          </p>
          {voxelData ? (
            <p className="text-xs text-muted-foreground">
              Voxels loaded. Use the Layers panel to toggle material visibility.
            </p>
          ) : (
            <p className="text-xs text-muted-foreground">
              No voxels loaded. Go to <span className="font-medium text-foreground">Scene &gt; Location</span> to load a location and generate voxel data.
            </p>
          )}
        </div>
      )}

      {/* Location text field */}
      {(source === 'osm' || source === '3dtiles') && (
        <div>
          <label className={labelClass}>Location</label>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void geocodeAndFetch()
            }}
            className="flex gap-1.5"
          >
            <input
              type="text"
              placeholder="e.g. Ghent, Belgium"
              value={locationQuery}
              onChange={(e) => setLocationQuery(e.target.value)}
              className={inputClass}
            />
            <button
              type="submit"
              disabled={busy || !locationQuery.trim()}
              className="px-2.5 py-1.5 rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center shrink-0"
            >
              {geocoding ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Search className="size-3.5" />
              )}
            </button>
          </form>
          {locationFormatted && location && (
            <p className="text-xs text-muted-foreground mt-1">
              {locationFormatted} ({location.lat.toFixed(4)}, {location.lon.toFixed(4)})
            </p>
          )}
        </div>
      )}

      {/* Radius */}
      {(source === 'osm' || source === '3dtiles') && (
        <div>
          <label className={labelClass}>Radius: {radius} m</label>
          <input
            type="range"
            min={50}
            max={1000}
            step={10}
            value={radius}
            onChange={(e) => setRadius(parseInt(e.target.value))}
            className="w-full"
          />
        </div>
      )}

      {/* Reload around users/body */}
      {source === 'osm' && location && (
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
      )}

      {/* OSM options */}
      {source === 'osm' && (
        <div className="space-y-2 pt-1 border-t border-border">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            OSM options
          </p>
          <div>
            <label className={labelClass}>
              Default building height: {osmOptions.defaultBuildingHeight} m
            </label>
            <input
              type="range"
              min={3}
              max={30}
              step={1}
              value={osmOptions.defaultBuildingHeight}
              onChange={(e) =>
                setOsmOptions({
                  defaultBuildingHeight: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
          </div>
          <div>
            <label className={labelClass}>
              Level height: {osmOptions.levelHeight} m
            </label>
            <input
              type="range"
              min={2}
              max={5}
              step={0.1}
              value={osmOptions.levelHeight}
              onChange={(e) =>
                setOsmOptions({ levelHeight: parseFloat(e.target.value) })
              }
              className="w-full"
            />
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs">
              <input
                type="checkbox"
                checked={osmOptions.buildings}
                onChange={(e) =>
                  setOsmOptions({ buildings: e.target.checked })
                }
              />
              Buildings
            </label>
            <label className="flex items-center gap-1.5 text-xs">
              <input
                type="checkbox"
                checked={osmOptions.roads}
                onChange={(e) => setOsmOptions({ roads: e.target.checked })}
              />
              Roads
            </label>
            <label className="flex items-center gap-1.5 text-xs">
              <input
                type="checkbox"
                checked={osmOptions.water}
                onChange={(e) => setOsmOptions({ water: e.target.checked })}
              />
              Water
            </label>
          </div>
          <div>
            <label className="flex items-center gap-1.5 text-xs">
              <input
                type="checkbox"
                checked={osmOptions.detail}
                onChange={(e) => setOsmOptions({ detail: e.target.checked })}
              />
              Detailed facades
            </label>
          </div>
        </div>
      )}

      {/* GeoJSON upload */}
      {source === 'osm' && (
        <div className="space-y-2 pt-1 border-t border-border">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            GeoJSON
          </p>
          <div className="space-y-1">
            <label className={labelClass}>Upload a .geojson or .json file</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".geojson,.json"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (!file) return
                setGeoJsonFileName(file.name)
                const reader = new FileReader()
                reader.onload = (evt) => {
                  const text = evt.target?.result as string
                  if (text) void fetchGeoJSON(text)
                }
                reader.readAsText(file)
                // reset so the same file can be re-selected
                e.target.value = ''
              }}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={busy}
              className="w-full px-3 py-1.5 rounded text-xs font-medium bg-muted text-muted-foreground hover:text-foreground disabled:opacity-50 flex items-center justify-center gap-1.5"
            >
              {loading && geojsonFileName ? (
                <Loader2 className="size-3 animate-spin" />
              ) : null}
              Choose file
            </button>
            {geojsonFileName && (
              <p className="text-xs text-muted-foreground truncate">
                {geojsonFileName}
              </p>
            )}
          </div>
        </div>
      )}

      {/* 3D Tiles options */}
      {source === '3dtiles' && (
        <div className="space-y-2 pt-1 border-t border-border">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            3D Tiles options
          </p>
          <div>
            <label className={labelClass}>
              Geometric error: {geometricError}
            </label>
            <input
              type="range"
              min={5}
              max={100}
              step={5}
              value={geometricError}
              onChange={(e) => setGeometricError(parseInt(e.target.value))}
              className="w-full"
            />
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {loading && (source === 'osm' || source === '3dtiles') && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="size-3 animate-spin" />
          {source === 'osm' ? 'Fetching OSM data...' : 'Fetching tiles...'}
        </div>
      )}

      {/* Export button */}
      {(source === 'osm' || source === '3dtiles') && location && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => void exportForRT('differt').catch(err => Sentry.captureException(err))}
            disabled={busy}
            className="px-3 py-1.5 rounded text-xs font-medium bg-muted text-muted-foreground hover:text-foreground disabled:opacity-50"
          >
            Export
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1.5">
          {error}
        </p>
      )}

      {/* Terrain section */}
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
        {terrainError && (
          <p className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1.5">
            {terrainError}
          </p>
        )}
      </div>
    </div>
  )
}
