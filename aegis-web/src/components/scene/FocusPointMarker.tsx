import { useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Line } from '@react-three/drei'
import { useMIMOStore } from '@/stores/mimo'

const MARKER_COLOR = '#00e5ff'
const MARKER_RADIUS = 0.08
const RING_RADIUS = 0.15

export default function FocusPointMarker() {
  const focusPoint = useMIMOStore(s => s.focusPoint)
  const arrayConfig = useMIMOStore(s => s.arrayConfig)
  const sphereRef = useRef<THREE.Mesh>(null)

  // Gentle pulse
  useFrame(({ clock }) => {
    if (!sphereRef.current) return
    const s = 1 + 0.1 * Math.sin(clock.elapsedTime * 2.5)
    sphereRef.current.scale.setScalar(s)
  })

  if (!arrayConfig) return null

  const arrPos = arrayConfig.position
  const fp = focusPoint

  // Build ring geometry (a circle in the XZ plane at focus point)
  const ringPoints: [number, number, number][] = []
  const segments = 32
  for (let i = 0; i <= segments; i++) {
    const angle = (i / segments) * Math.PI * 2
    ringPoints.push([
      fp[0] + RING_RADIUS * Math.cos(angle),
      fp[1],
      fp[2] + RING_RADIUS * Math.sin(angle),
    ])
  }

  return (
    <group>
      {/* Focus point sphere */}
      <mesh ref={sphereRef} position={fp}>
        <sphereGeometry args={[MARKER_RADIUS, 16, 16]} />
        <meshBasicMaterial color={MARKER_COLOR} transparent opacity={0.9} depthTest={false} />
      </mesh>

      {/* Ground ring */}
      <Line
        points={ringPoints}
        color={MARKER_COLOR}
        lineWidth={1.5}
        transparent
        opacity={0.5}
      />

      {/* Beam line from array to focus point */}
      <Line
        points={[arrPos, fp]}
        color={MARKER_COLOR}
        lineWidth={1}
        dashed
        dashSize={0.15}
        gapSize={0.1}
        transparent
        opacity={0.4}
      />

      {/* Vertical drop line from focus point to ground */}
      {fp[1] > 0.05 && (
        <Line
          points={[[fp[0], fp[1], fp[2]], [fp[0], 0, fp[2]]]}
          color={MARKER_COLOR}
          lineWidth={0.5}
          dashed
          dashSize={0.05}
          gapSize={0.05}
          transparent
          opacity={0.25}
        />
      )}
    </group>
  )
}
