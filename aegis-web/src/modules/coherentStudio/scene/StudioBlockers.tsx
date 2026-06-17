import { useMemo } from 'react'
import * as THREE from 'three'
import { Line } from '@react-three/drei'
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
const METALNESS = 0.45
const ROUGHNESS = 0.4

export default function StudioBlockers() {
  const scene = useStudioStore((s) => s.scene)
  const showBlockers = useStudioStore((s) => s.showBlockers)
  const background = useStudioStore((s) => s.background)

  // Room wireframe edge segments (point pairs), rebuilt only when the room
  // dimensions change. Drawn with drei's Line so the stroke is genuinely thick
  // (WebGL lineWidth on lineSegments is clamped to 1 px on most drivers).
  const roomEdgePoints = useMemo<[number, number, number][] | null>(() => {
    if (!scene) return null
    const [sx, sy, sz] = scene.room_dims
    const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(sx, sy, sz))
    const pos = edges.attributes.position as THREE.BufferAttribute
    const pts: [number, number, number][] = []
    for (let i = 0; i < pos.count; i++) pts.push([pos.getX(i), pos.getY(i), pos.getZ(i)])
    edges.dispose()
    return pts
  }, [scene])

  if (!scene) return null

  // The factory outline reads as plain line-art: black on the white / figure
  // backdrop, white on the dark working view.
  const roomColor = background === 'white' ? '#000000' : '#ffffff'

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

      {showBlockers && roomEdgePoints && (
        // Room box is centred at the world origin (BS at x=-13, far wall at +x),
        // floor at z=0 so the centre sits at z = room_height / 2. Part of the
        // scene context, so it follows the blockers toggle (off -> clean body tile).
        <Line
          points={roomEdgePoints}
          segments
          color={roomColor}
          lineWidth={2.5}
          position={[0, 0, scene.room_dims[2] / 2]}
        />
      )}
    </group>
  )
}
