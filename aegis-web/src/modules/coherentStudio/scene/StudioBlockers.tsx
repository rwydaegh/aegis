import { useMemo } from 'react'
import * as THREE from 'three'
import { useStudioStore } from '../store'

// The real factory blockers from the traced scene: metallic scatterer cuboids
// plus, in the NLOS condition, the corridor blocker slab (drawn
// semi-transparent so the array pattern reads through it). Optionally the room
// box is drawn as a lineart wireframe (the factory outline).
//
// Geometry arrives in the server (Z-up) frame. toScene is exactly a -90 deg
// rotation about X ((x,y,z) -> (x, z, -y)), so wrapping everything in a group
// with that rotation lets us place boxes in server coordinates directly: a box
// at server `center`, sized (length, width, height) along server XYZ, yawed
// about server +z, lands correctly oriented in the Y-up scene.

// Light steel grey. Metalness is kept moderate (not ~1) on purpose: with no
// environment map a fully metallic surface reflects only direct lights and
// goes black everywhere else, which reads as a dark slab on a white backdrop.
// A mid metalness keeps a visible diffuse base while the lights still give a
// brushed-metal specular sheen on both the dark and white backgrounds.
const METAL_COLOR = '#c4cad3'
const BLOCKER_COLOR = '#aebfcf'
const ROOM_COLOR = '#8895a5'
const METALNESS = 0.45
const ROUGHNESS = 0.4

export default function StudioBlockers() {
  const scene = useStudioStore((s) => s.scene)
  const showBlockers = useStudioStore((s) => s.showBlockers)
  const showRoomOutline = useStudioStore((s) => s.showRoomOutline)

  // Room wireframe edges, rebuilt only when the room dimensions change.
  const roomEdges = useMemo(() => {
    if (!scene) return null
    const [sx, sy, sz] = scene.room_dims
    return new THREE.EdgesGeometry(new THREE.BoxGeometry(sx, sy, sz))
  }, [scene])

  if (!scene) return null

  return (
    <group rotation={[-Math.PI / 2, 0, 0]}>
      {showBlockers &&
        scene.scatterers.map((s, i) => (
          <mesh key={i} position={s.center} rotation={[0, 0, s.yaw_rad]}>
            <boxGeometry args={s.size} />
            <meshStandardMaterial color={METAL_COLOR} metalness={METALNESS} roughness={ROUGHNESS} />
          </mesh>
        ))}

      {showBlockers && scene.blocker && (
        <mesh position={scene.blocker.center}>
          <boxGeometry args={scene.blocker.size} />
          <meshStandardMaterial
            color={BLOCKER_COLOR}
            metalness={METALNESS}
            roughness={ROUGHNESS}
            transparent
            opacity={0.32}
            depthWrite={false}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}

      {showRoomOutline && roomEdges && (
        // Room box is centred at the world origin (BS at x=-13, far wall at +x),
        // floor at z=0 so the centre sits at z = room_height / 2.
        <lineSegments position={[0, 0, scene.room_dims[2] / 2]} geometry={roomEdges}>
          <lineBasicMaterial color={ROOM_COLOR} transparent opacity={0.4} />
        </lineSegments>
      )}
    </group>
  )
}
