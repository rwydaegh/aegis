import { toScene } from '@/api/coordinates'
import type { ReplaySceneSpec, ReplayBox, Vec3 } from '@/api/replayTypes'

const KIND_COLOR: Record<string, string> = {
  scatterer: '#7a8595',
  blocker: '#cc4444',
  wall: '#334155',
}

/**
 * One axis-aligned-in-server box, rendered in scene (Y-up) coords.
 * Server size [sx, sy, sz] maps to scene box args [sx, sz, sy]. Yaw about the
 * server z (vertical) axis maps to a rotation about the scene y axis.
 */
function Box({ center, size, yaw_rad, kind }: ReplayBox) {
  const p = toScene(center)
  const [sx, sy, sz] = size
  const color = (kind && KIND_COLOR[kind]) ?? '#6b7280'
  const opacity = kind === 'wall' ? 0.15 : 0.55
  return (
    <mesh position={p} rotation={[0, -(yaw_rad ?? 0), 0]} castShadow receiveShadow>
      <boxGeometry args={[sx, sz, sy]} />
      <meshStandardMaterial color={color} transparent opacity={opacity} roughness={0.9} />
    </mesh>
  )
}

function RoomWireframe({ center, size }: { center?: Vec3; size: Vec3 }) {
  const c = center ?? [0, 0, 0]
  const p = toScene(c)
  const [sx, sy, sz] = size
  return (
    <mesh position={p}>
      <boxGeometry args={[sx, sz, sy]} />
      <meshBasicMaterial color="#3b4252" wireframe />
    </mesh>
  )
}

export default function ReplaySceneGeometry({ scene }: { scene: ReplaySceneSpec }) {
  const groundSize = scene.ground?.size ?? 80
  return (
    <group>
      {scene.room && <RoomWireframe center={scene.room.center} size={scene.room.size} />}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <planeGeometry args={[groundSize, groundSize]} />
        <meshStandardMaterial color="#15171c" roughness={1} />
      </mesh>
      {scene.boxes.map((b, i) => (
        <Box key={i} {...b} />
      ))}
    </group>
  )
}
