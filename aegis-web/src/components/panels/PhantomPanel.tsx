import { useSceneStore } from '@/stores/scene'
import { switchBody } from '@/api/client'

// IT'IS Virtual Population v5 phantom metadata
// Source: https://itis.swiss/virtual-population/virtual-population/vip3/
export const PHANTOM_META: Record<string, { sex: string; age: number; mass_kg: number; height_m: number }> = {
  duke:       { sex: 'male',   age: 34, mass_kg: 70.3, height_m: 1.77 },
  ella:       { sex: 'female', age: 26, mass_kg: 57.3, height_m: 1.63 },
  thelonious: { sex: 'male',   age: 6,  mass_kg: 18.6, height_m: 1.15 },
  eartha:     { sex: 'female', age: 8,  mass_kg: 29.9, height_m: 1.36 },
}

function formatLabel(name: string): string {
  const cap = name.charAt(0).toUpperCase() + name.slice(1)
  const meta = PHANTOM_META[name.toLowerCase()]
  if (!meta) return cap
  return `${cap} (${meta.age}y, ${meta.sex}, ${meta.mass_kg} kg)`
}

export default function PhantomPanel() {
  const bodyName = useSceneStore((s) => s.bodyName)
  const setBodyName = useSceneStore((s) => s.setBodyName)
  const caps = useSceneStore((s) => s.capabilities)

  if (!caps) return null

  const handleChange = async (name: string) => {
    try {
      await switchBody(name)
      setBodyName(name)
    } catch (err) {
      console.error('Failed to switch body:', err)
    }
  }

  const selectClass =
    'w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring'

  return (
    <div>
      <label className="text-xs text-muted-foreground block mb-1">Body mesh</label>
      <select
        className={selectClass}
        value={bodyName}
        onChange={(e) => handleChange(e.target.value)}
      >
        {caps.bodies.map((b) => (
          <option key={b} value={b}>
            {formatLabel(b)}
          </option>
        ))}
      </select>
    </div>
  )
}
