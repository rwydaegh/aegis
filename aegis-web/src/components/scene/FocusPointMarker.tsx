import { useRef, useMemo } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Line } from '@react-three/drei'
import { useMIMOStore } from '@/stores/mimo'
import { useSceneStore } from '@/stores/scene'

const FALLBACK_MARKER = {
  color: '#00e5ff',
  marker_radius: 0.025,
  ring_radius: 0.05,
}

interface FocusPointMarkerProps {
  focusPoint?: [number, number, number]
  arrayPosition?: [number, number, number]
}

export default function FocusPointMarker({ focusPoint: fpProp, arrayPosition: arrProp }: FocusPointMarkerProps = {}) {
  const mimoFp = useMIMOStore(s => s.focusPoint)
  const mimoConfig = useMIMOStore(s => s.arrayConfig)
  const markerCfg = useSceneStore(s => s.viewerConfig?.ui?.focus_point_marker) ?? FALLBACK_MARKER
  const MARKER_COLOR = markerCfg.color
  const MARKER_RADIUS = markerCfg.marker_radius
  const RING_RADIUS = markerCfg.ring_radius
  const sphereRef = useRef<THREE.Mesh>(null)

  // Gentle pulse
  useFrame(({ clock }) => {
    if (!sphereRef.current) return
    const s = 1 + 0.1 * Math.sin(clock.elapsedTime * 2.5)
    sphereRef.current.scale.setScalar(s)
  })

  // Fall back to MIMO store if props not provided
  const fp = fpProp ?? mimoFp
  const arrPos = arrProp ?? mimoConfig?.position

  // Build ring geometry (a circle in the XZ plane at focus point).
  // useMemo must run on every render to satisfy the Rules of Hooks, so it
  // guards on fp internally instead of sitting behind the early return below.
  const ringPoints = useMemo(() => {
    if (!fp) return []
    const pts: [number, number, number][] = []
    const segments = 32
    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2
      pts.push([
        fp[0] + RING_RADIUS * Math.cos(angle),
        fp[1],
        fp[2] + RING_RADIUS * Math.sin(angle),
      ])
    }
    return pts
  }, [fp, RING_RADIUS])

  if (!fp || !arrPos) return null

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
