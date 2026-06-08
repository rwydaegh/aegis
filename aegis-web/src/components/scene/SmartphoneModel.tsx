import { memo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'

// Realistic smartphone dimensions (meters)
const PHONE_W = 0.075 // width (short edge)
const PHONE_H = 0.155 // height (long edge)
const PHONE_D = 0.008 // depth (thickness)
const BEZEL = 0.004

interface SmartphoneModelProps {
  /** Phone position. In body-relative mode this is the user body position
   *  (Y-up); in absolute-orientation mode it is the phone origin directly. */
  position: [number, number, number]
  /** User body Y-rotation in radians (body-relative mode only) */
  rotationY?: number
  /** Device offset in Z-up [right, forward, up] from body origin (body-relative mode only) */
  deviceOffset?: [number, number, number]
  /** Absolute Euler orientation [x, y, z] in radians, applied with intrinsic
   *  Z-Y-X order to match the server's euler_to_matrix(yaw, pitch, roll). When
   *  provided, the phone renders at `position` with this rotation and the
   *  body-relative `deviceOffset` / `rotationY` math is ignored. */
  orientation?: [number, number, number]
}

export default memo(function SmartphoneModel({
  position,
  rotationY = 0,
  deviceOffset = [0, 0, 0],
  orientation,
}: SmartphoneModelProps) {
  const groupRef = useRef<THREE.Group>(null)

  const absolute = orientation != null

  let worldX: number
  let baseY: number
  let worldZ: number
  let groupRotation: [number, number, number] | [number, number, number, THREE.EulerOrder]

  if (absolute) {
    worldX = position[0]
    baseY = position[1]
    worldZ = position[2]
    groupRotation = [orientation[0], orientation[1], orientation[2], 'ZYX']
  } else {
    // Convert Z-up device offset to Y-up scene coords: [x, z_up, -y_fwd]
    const localX = deviceOffset[0]
    const localY = deviceOffset[2] // z-up height -> y-up height
    const localZ = -deviceOffset[1] // z-up forward -> -scene z

    // Rotate local offset by user body orientation around Y
    const cos = Math.cos(rotationY)
    const sin = Math.sin(rotationY)
    worldX = position[0] + cos * localX + sin * localZ
    worldZ = position[2] - sin * localX + cos * localZ
    baseY = position[1] + localY
    groupRotation = [0, rotationY, 0]
  }

  // Subtle hover animation
  useFrame(({ clock }) => {
    if (!groupRef.current) return
    groupRef.current.position.y =
      baseY + 0.003 * Math.sin(clock.elapsedTime * 1.5)
  })

  return (
    <group
      ref={groupRef}
      position={[worldX, baseY, worldZ]}
      rotation={groupRotation}
    >
      {/* Phone body */}
      <mesh castShadow>
        <boxGeometry args={[PHONE_W, PHONE_H, PHONE_D]} />
        <meshStandardMaterial color="#1a1a1a" metalness={0.5} roughness={0.35} />
      </mesh>

      {/* Screen (front face, slight offset) */}
      <mesh position={[0, 0, PHONE_D / 2 + 0.0002]}>
        <planeGeometry args={[PHONE_W - BEZEL * 2, PHONE_H - BEZEL * 2]} />
        <meshStandardMaterial
          color="#0a0a18"
          metalness={0.85}
          roughness={0.1}
          emissive="#06061a"
          emissiveIntensity={0.2}
        />
      </mesh>

      {/* Camera lens on back */}
      <mesh
        position={[-PHONE_W / 2 + 0.015, PHONE_H / 2 - 0.02, -PHONE_D / 2 - 0.0005]}
        rotation={[Math.PI / 2, 0, 0]}
      >
        <cylinderGeometry args={[0.005, 0.005, 0.001, 16]} />
        <meshStandardMaterial color="#222" metalness={0.9} roughness={0.1} />
      </mesh>
    </group>
  )
})
