import { toScene } from '@/api/coordinates'
import type { ReplayArraySpec } from '@/api/replayTypes'

/**
 * Base-station array marker: a flat blue panel at the array position, plus
 * element dots if explicit element positions are given. Deliberately crude;
 * this is a debug view, not a product render.
 */
export default function ReplayArray({ array }: { array: ReplayArraySpec }) {
  const p = toScene(array.position)
  return (
    <group>
      <mesh position={p}>
        <boxGeometry args={[0.5, 0.5, 0.06]} />
        <meshStandardMaterial color="#3b82f6" emissive="#1e3a8a" emissiveIntensity={0.4} />
      </mesh>
      {array.elements?.map((e, i) => {
        const ep = toScene(e)
        return (
          <mesh key={i} position={ep}>
            <sphereGeometry args={[0.02, 8, 8]} />
            <meshBasicMaterial color="#93c5fd" />
          </mesh>
        )
      })}
    </group>
  )
}
