import { useSceneStore } from '@/stores/scene'
import { switchBody } from '@/api/client'

export default function PhantomPanel() {
  const bodyName = useSceneStore((s) => s.bodyName)
  const setBodyName = useSceneStore((s) => s.setBodyName)
  const caps = useSceneStore((s) => s.capabilities)

  if (!caps) return null

  const handleChange = async (name: string) => {
    try {
      await switchBody(name)
      setBodyName(name) // triggers useBodyLoader to refetch
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
            {b}
          </option>
        ))}
      </select>
    </div>
  )
}
