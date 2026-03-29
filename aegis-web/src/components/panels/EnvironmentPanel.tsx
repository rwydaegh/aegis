import * as Sentry from '@sentry/react'
import { useEnvironmentStore } from '@/stores/environment'
import type { EnvironmentSource } from '@/stores/environment'
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
  const source = useEnvironmentStore((s) => s.source)
  const location = useEnvironmentStore((s) => s.location)
  const radius = useEnvironmentStore((s) => s.radius)
  const geometricError = useEnvironmentStore((s) => s.geometricError)
  const googleApiKey = useEnvironmentStore((s) => s.googleApiKey)
  const osmOptions = useEnvironmentStore((s) => s.osmOptions)
  const loading = useEnvironmentStore((s) => s.loading)
  const error = useEnvironmentStore((s) => s.error)
  const setSource = useEnvironmentStore((s) => s.setSource)
  const setLocation = useEnvironmentStore((s) => s.setLocation)
  const setRadius = useEnvironmentStore((s) => s.setRadius)
  const setGeometricError = useEnvironmentStore((s) => s.setGeometricError)
  const setGoogleApiKey = useEnvironmentStore((s) => s.setGoogleApiKey)
  const setOsmOptions = useEnvironmentStore((s) => s.setOsmOptions)
  const fetchOSM = useEnvironmentStore((s) => s.fetchOSM)
  const fetchTilesForRT = useEnvironmentStore((s) => s.fetchTilesForRT)
  const exportForRT = useEnvironmentStore((s) => s.exportForRT)

  return (
    <div className="space-y-3 text-sm">
      {/* Source selector */}
      <div>
        <label className={labelClass}>Source</label>
        <div className="grid grid-cols-4 gap-1">
          {SOURCE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setSource(opt.value)}
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
          <div>
            <label className={labelClass}>Google API key</label>
            <input
              type="password"
              value={googleApiKey}
              onChange={(e) => setGoogleApiKey(e.target.value)}
              placeholder="AIza..."
              className={inputClass}
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
    </div>
  )
}
