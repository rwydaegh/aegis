import { useEnvironmentStore } from '@/stores/environment'
import { labelClass } from './constants'

export function OSMOptions() {
  const osmOptions = useEnvironmentStore((s) => s.osmOptions)
  const setOsmOptions = useEnvironmentStore((s) => s.setOsmOptions)

  return (
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
  )
}
