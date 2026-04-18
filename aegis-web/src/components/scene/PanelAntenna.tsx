import { memo, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'

interface PanelAntennaProps {
  nH: number
  nV: number
  panelWidth: number
  panelHeight: number
  depth?: number
  azimuthDeg: number
  tiltDeg: number
  position: [number, number, number]
  color?: string
  showElements?: boolean
  elementDotRadius?: number
  poleRadius?: number
  selected?: boolean
  onClick?: () => void
}

const FALLBACK_PANEL = {
  depth: 0.05,
  pole_radius: 0.04,
  element_dot_radius: 0.008,
  default_color: '#888888',
}

export default memo(function PanelAntenna({
  nH,
  nV,
  panelWidth,
  panelHeight,
  depth,
  azimuthDeg,
  tiltDeg,
  position,
  color,
  showElements = true,
  elementDotRadius,
  poleRadius,
  selected = false,
  onClick,
}: PanelAntennaProps) {
  const panelCfg = useSceneStore(s => s.viewerConfig?.basestations?.panel)
  const resolvedDepth = depth ?? panelCfg?.depth ?? FALLBACK_PANEL.depth
  const resolvedPoleRadius = poleRadius ?? panelCfg?.pole_radius ?? FALLBACK_PANEL.pole_radius
  const resolvedDotRadius = elementDotRadius ?? panelCfg?.element_dot_radius ?? FALLBACK_PANEL.element_dot_radius
  const resolvedColor = color ?? panelCfg?.default_color ?? FALLBACK_PANEL.default_color
  const groupRef = useRef<THREE.Group>(null)

  // Compute panel orientation quaternion from azimuth and tilt
  const quaternion = useMemo(() => {
    const q = new THREE.Quaternion()
    // Azimuth: rotate around Y axis (compass bearing, 0=North=-Z in Three.js Y-up)
    // The panel's local +Z face (where elements are drawn) must point toward the
    // boresight direction. At azimuth=0 (North), boresight = [0,0,-1] in Three.js,
    // so we need local +Z -> world -Z, which requires a pi offset on the Y rotation.
    // Tilt: positive = downtilt (boresight below horizontal).
    const azRad = THREE.MathUtils.degToRad(azimuthDeg)
    const tiltRad = THREE.MathUtils.degToRad(tiltDeg)
    const euler = new THREE.Euler(tiltRad, Math.PI - azRad, 0, 'YXZ')
    q.setFromEuler(euler)
    return q
  }, [azimuthDeg, tiltDeg])

  // Compute element positions on the panel face (local coords)
  const elementPositions = useMemo(() => {
    if (!showElements || nH <= 0 || nV <= 0) return []
    const positions: [number, number, number][] = []
    const spacingH = nH > 1 ? panelWidth / (nH + 1) : 0
    const spacingV = nV > 1 ? panelHeight / (nV + 1) : 0
    const startH = nH > 1 ? -panelWidth / 2 + spacingH : 0
    const startV = nV > 1 ? -panelHeight / 2 + spacingV : 0
    for (let i = 0; i < nH; i++) {
      for (let j = 0; j < nV; j++) {
        const x = nH > 1 ? startH + i * spacingH : 0
        const y = nV > 1 ? startV + j * spacingV : 0
        positions.push([x, y, depth + 0.001])
      }
    }
    return positions
  }, [nH, nV, panelWidth, panelHeight, depth, showElements])

  const [px, py, pz] = position
  const poleHeight = py

  const panelColor = selected ? '#ffaa00' : color
  const emissive = selected ? '#664400' : '#000000'

  return (
    <group ref={groupRef}>
      {/* Support pole from ground to panel center */}
      {poleHeight > 0.1 && (
        <mesh position={[px, poleHeight / 2, pz]}>
          <cylinderGeometry args={[poleRadius, poleRadius, poleHeight, 8]} />
          <meshStandardMaterial color="#404040" metalness={0.6} roughness={0.4} />
        </mesh>
      )}

      {/* Panel body - oriented by azimuth and tilt.
          The box is offset forward by depth/2 so the back face sits at the
          group origin (where the pole connects), keeping the pole behind
          the panel instead of piercing through the center. */}
      <group position={[px, py, pz]} quaternion={quaternion}>
        <mesh onClick={onClick} position={[0, 0, depth / 2]}>
          <boxGeometry args={[panelWidth, panelHeight, depth]} />
          <meshStandardMaterial
            color={panelColor}
            emissive={emissive}
            metalness={0.5}
            roughness={0.3}
          />
        </mesh>

        {/* Element dots on the front face */}
        {showElements && elementPositions.map((pos, i) => (
          <mesh key={i} position={pos}>
            <circleGeometry args={[elementDotRadius, 12]} />
            <meshBasicMaterial color="#cccccc" side={THREE.FrontSide} />
          </mesh>
        ))}
      </group>
    </group>
  )
})
