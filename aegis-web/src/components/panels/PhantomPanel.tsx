import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'

export const PHANTOM_META: Record<string, { sex: string; age: number; mass_kg: number; height_m: number }> = {
  adult_male:   { sex: 'male',   age: 34, mass_kg: 73.0, height_m: 1.76 },
  adult_female: { sex: 'female', age: 26, mass_kg: 60.0, height_m: 1.63 },
  boy_6y:       { sex: 'male',   age: 6,  mass_kg: 19.0, height_m: 1.15 },
  girl_8y:      { sex: 'female', age: 8,  mass_kg: 30.0, height_m: 1.36 },
  duke:         { sex: 'male',   age: 34, mass_kg: 70.3, height_m: 1.77 },
  ella:         { sex: 'female', age: 26, mass_kg: 57.3, height_m: 1.63 },
  thelonious:   { sex: 'male',   age: 6,  mass_kg: 18.6, height_m: 1.15 },
  eartha:       { sex: 'female', age: 8,  mass_kg: 29.9, height_m: 1.36 },
}

function formatLabel(name: string): string {
  const cap = name.charAt(0).toUpperCase() + name.slice(1)
  const meta = PHANTOM_META[name.toLowerCase()]
  if (!meta) return cap
  return `${cap} (${meta.age}y, ${meta.sex}, ${meta.mass_kg} kg)`
}

const PHANTOM_ORDER = [
  'adult_male',
  'adult_female',
  'boy_6y',
  'girl_8y',
  'duke',
  'ella',
  'eartha',
  'thelonious',
]

export default function PhantomPanel() {
  const bodyName = useSceneStore((s) => s.bodyName)
  const setBodyName = useSceneStore((s) => s.setBodyName)
  const caps = useSceneStore((s) => s.capabilities)
  const setCameraPreset = useUIStore((s) => s.setCameraPreset)
  const animationClip = useSceneStore((s) => s.animationClip)
  const setAnimationClip = useSceneStore((s) => s.setAnimationClip)
  const animationPlaying = useSceneStore((s) => s.animationPlaying)
  const setAnimationPlaying = useSceneStore((s) => s.setAnimationPlaying)
  const phantomType = useSceneStore((s) => s.phantomType)

  if (!caps) return null

  // Setting bodyName triggers useBodyLoader (via useEffect on bodyName) to fetch
  // the new body geometry. Do not load geometry here to avoid a race condition
  // where useBodyLoader fires on bodyName change and overwrites the correct body.
  const handleChange = (name: string) => {
    setBodyName(name)
    setCameraPreset('focus')
    setTimeout(() => setCameraPreset(null), 50)
  }

  const sortedBodies = [...(caps.bodies || [])].sort((a, b) => {
    const ai = PHANTOM_ORDER.indexOf(a.toLowerCase())
    const bi = PHANTOM_ORDER.indexOf(b.toLowerCase())
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
  })

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
        {sortedBodies.map((b) => (
          <option key={b} value={b}>
            {formatLabel(b)}
          </option>
        ))}
      </select>

      {phantomType === 'gltf' && (
        <>
          <label className="text-xs text-muted-foreground block mb-1 mt-3">Pose</label>
          <select
            className={selectClass}
            value={animationClip}
            onChange={(e) => setAnimationClip(e.target.value)}
          >
            {['idle', 'walking', 'phone_ear_r', 'phone_ear_l', 'sitting'].map((p) => (
              <option key={p} value={p}>{p.replace(/_/g, ' ')}</option>
            ))}
          </select>

          <button
            className="mt-2 w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground hover:bg-accent"
            onClick={() => setAnimationPlaying(!animationPlaying)}
          >
            {animationPlaying ? '⏸ Pause' : '▶ Play'}
          </button>
        </>
      )}
    </div>
  )
}
