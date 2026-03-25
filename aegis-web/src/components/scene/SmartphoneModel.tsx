import { useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'

// Realistic smartphone dimensions (meters)
const PHONE_W = 0.075 // width (short edge)
const PHONE_H = 0.155 // height (long edge)
const PHONE_D = 0.008 // depth (thickness)
const BEZEL = 0.004

// Device offset from user body origin, in Z-up [x, y, z] = [right, forward, up].
// Must match the device_offset sent to the backend in useMIMODosimetry.ts.
const DEVICE_OFFSET_ZUP: [number, number, number] = [0.25, 0.0, 1.4]

interface SmartphoneModelProps {
  /** User body position in scene (Y-up) coords */
  position: [number, number, number]
  /** User body Y-rotation in radians */
  rotationY: number
}

export default function SmartphoneModel({ position, rotationY }: SmartphoneModelProps) {
  const groupRef = useRef<THREE.Group>(null)

  // Subtle hover animation
  useFrame(({ clock }) => {
    if (!groupRef.current) return
    groupRef.current.position.y =
      baseY + 0.003 * Math.sin(clock.elapsedTime * 1.5)
  })

  // Convert Z-up device offset to Y-up scene coords: [x, z, -y]
  const localX = DEVICE_OFFSET_ZUP[0]
  const localY = DEVICE_OFFSET_ZUP[2] // z-up height -> y-up height
  const localZ = -DEVICE_OFFSET_ZUP[1] // z-up forward -> -scene z

  // Rotate local offset by user body orientation around Y
  const cos = Math.cos(rotationY)
  const sin = Math.sin(rotationY)
  const worldX = position[0] + cos * localX + sin * localZ
  const worldZ = position[2] - sin * localX + cos * localZ
  const baseY = position[1] + localY

  return (
    <group
      ref={groupRef}
      position={[worldX, baseY, worldZ]}
      rotation={[0, rotationY, 0]}
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
}
