import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { fetchBody } from '@/api/client'

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
  const setBodyGeometry = useSceneStore((s) => s.setBodyGeometry)
  const caps = useSceneStore((s) => s.capabilities)

  if (!caps) return null

  const handleChange = async (name: string) => {
    try {
      const { binary, meta } = await fetchBody(name)

      const geometry = new THREE.BufferGeometry()
      geometry.setAttribute('position', new THREE.BufferAttribute(binary.positions, 3))
      geometry.setAttribute('normal', new THREE.BufferAttribute(binary.normals, 3))

      // Body mesh is triangle soup (3 vertices per triangle, no index buffer)
      // Add a color attribute for heatmap (initialized to neutral gray)
      const colors = new Float32Array(binary.positions.length)
      colors.fill(0.5)
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

      geometry.computeBoundingBox()

      // Shift body so feet (min Y) sit on ground plane at y=0
      const bb = geometry.boundingBox!
      if (bb.min.y < 0) {
        geometry.translate(0, -bb.min.y, 0)
        geometry.computeBoundingBox()
      }

      // Update store: set name first, then geometry
      setBodyName(name)
      setBodyGeometry(geometry)

      void meta // meta available if needed later
    } catch (err) {
      console.error('Failed to load body:', err)
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
