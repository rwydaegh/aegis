import { useEnvironmentStore } from '@/stores/environment'
import { labelClass } from './constants'

export function RadiusControl() {
  const radius = useEnvironmentStore((s) => s.radius)
  const setRadius = useEnvironmentStore((s) => s.setRadius)

  return (
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
  )
}
