import { useRef, useState } from 'react'
import * as Sentry from '@sentry/react'
import { useEnvironmentStore } from '@/stores/environment'
import type { EnvironmentSource } from '@/stores/environment'
import { useSceneStore } from '@/stores/scene'
import { useTerrainStore } from '@/stores/terrain'
import { useUIStore } from '@/stores/ui'
import { Loader2 } from 'lucide-react'

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
  const radius = useEnvironmentStore((s) => s.radius)
  const geometricError = useEnvironmentStore((s) => s.geometricError)
  const osmOptions = useEnvironmentStore((s) => s.osmOptions)
  const loading = useEnvironmentStore((s) => s.loading)
  const error = useEnvironmentStore((s) => s.error)
  const setSource = useEnvironmentStore((s) => s.setSource)
  const setLocation = useEnvironmentStore((s) => s.setLocation)
  const setRadius = useEnvironmentStore((s) => s.setRadius)
  const setGeometricError = useEnvironmentStore((s) => s.setGeometricError)
  const setOsmOptions = useEnvironmentStore((s) => s.setOsmOptions)
  const fetchOSM = useEnvironmentStore((s) => s.fetchOSM)
  const fetchGeoJSON = useEnvironmentStore((s) => s.fetchGeoJSON)
  const fetchTilesForRT = useEnvironmentStore((s) => s.fetchTilesForRT)
  const exportForRT = useEnvironmentStore((s) => s.exportForRT)

  const setCameraMode = useUIStore((s) => s.setCameraMode)
  const voxelData = useSceneStore((s) => s.voxelData)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [geojsonFileName, setGeoJsonFileName] = useState<string | null>(null)

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
                if (opt.value === '3dtiles') setCameraMode('globe')
                else if (source === '3dtiles') setCameraMode('orbit')
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

      {/* Location */}
      {(source === 'osm' || source === '3dtiles') && (
        <div>
          <label className={labelClass}>Location</label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              step="0.0001"
              placeholder="Latitude"
              value={location?.lat ?? ''}
              onChange={(e) =>
                setLocation(
                  parseFloat(e.target.value) || 0,
                  location?.lon ?? 0,
                )
              }
              className={inputClass}
            />
            <input
              type="number"
              step="0.0001"
              placeholder="Longitude"
              value={location?.lon ?? ''}
              onChange={(e) =>
                setLocation(
                  location?.lat ?? 0,
                  parseFloat(e.target.value) || 0,
                )
              }
              className={inputClass}
            />
          </div>
        </div>
      )}

      {/* Radius */}
      {(source === 'osm' || source === '3dtiles') && (
        <div>
          <label className={labelClass}>Radius: {radius} m</label>
          <input
            type="range"
            min={50}
            max={500}
            step={10}
            value={radius}
            onChange={(e) => setRadius(parseInt(e.target.value))}
            className="w-full"
          />
        </div>
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
              disabled={loading}
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

      {/* Action buttons */}
      {(source === 'osm' || source === '3dtiles') && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => {
              if (source === 'osm') void fetchOSM()
              else void fetchTilesForRT()
            }}
            disabled={loading || !location}
            className="flex-1 px-3 py-1.5 rounded text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-1.5"
          >
            {loading && <Loader2 className="size-3 animate-spin" />}
            {source === 'osm' ? 'Fetch OSM' : 'Fetch tiles'}
          </button>
          <button
            onClick={() => void exportForRT('differt').catch(err => Sentry.captureException(err))}
            disabled={loading}
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
