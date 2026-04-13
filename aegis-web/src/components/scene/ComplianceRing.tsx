import { useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'

/**
 * Renders a ground-plane ring at the minimum ICNIRP-compliant distance
 * from the antenna. Red disc = exclusion zone; green ring = boundary.
 * Only visible when compliance data is available.
 */
export default function ComplianceRing() {
  const stats = useSimulationStore(s => s.stats)
  const compliance = useSimulationStore(s => s.compliance)
  const antennaPos = useSimulationStore(s => s.antennaPos)
  const config = useSceneStore(s => s.viewerConfig)
  const complianceRingVisible = useSceneStore(s => s.complianceRingVisible)

  const discRef = useRef<THREE.Mesh>(null)
  const ringRef = useRef<THREE.Mesh>(null)

  const distanceM = stats?.distance_m
  const marginDb = compliance?.margin_db

  // Compute minimum compliant distance using far-field 1/r^2 scaling:
  // margin(d) = margin(d0) + 20*log10(d/d0) = 0  =>  d = d0 * 10^(-margin0/20)
  const minCompliantDist = useMemo(() => {
    if (marginDb == null || distanceM == null || distanceM <= 0) return null
    if (!Number.isFinite(marginDb)) return null
    const d = distanceM * Math.pow(10, -marginDb / 20)
    // Clamp to reasonable range
    if (d < 0.1 || d > 500) return null
    return d
  }, [marginDb, distanceM])

  // Subtle breathing animation
  useFrame(({ clock }) => {
    if (!ringRef.current) return
    const s = 1 + 0.015 * Math.sin(clock.getElapsedTime() * 1.5)
    ringRef.current.scale.set(s, s, 1)
  })

  if (!complianceRingVisible) return null
  if (!antennaPos || minCompliantDist == null) return null

  const poleH = config?.antenna?.pole_height ?? 2
  // Center the ring at the antenna base (ground plane)
  const centerX = antennaPos[0]
  const centerZ = antennaPos[2]

  // Color depends on current compliance status
  const isCompliant = compliance?.overall_pass ?? false
  const discColor = isCompliant ? '#16a34a' : '#dc2626'
  const discOpacity = isCompliant ? 0.06 : 0.10
  const ringColor = isCompliant ? '#4ade80' : '#f87171'

  return (
    <group position={[centerX, 0.005, centerZ]}>
      {/* Exclusion zone disc (semi-transparent) */}
      <mesh ref={discRef} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[minCompliantDist, 64]} />
        <meshBasicMaterial
          color={discColor}
          transparent
          opacity={discOpacity}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>

      {/* Compliance boundary ring */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[minCompliantDist - 0.04, minCompliantDist + 0.04, 64]} />
        <meshBasicMaterial
          color={ringColor}
          transparent
          opacity={0.5}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>

      {/* Distance label at the ring edge */}
      <Html
        position={[0, poleH + 0.3, -minCompliantDist]}
        center
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        <div style={{
          background: 'rgba(0,0,0,0.78)',
          backdropFilter: 'blur(6px)',
          borderRadius: '6px',
          padding: '3px 8px',
          whiteSpace: 'nowrap',
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
          border: `1px solid ${isCompliant ? 'rgba(74,222,128,0.3)' : 'rgba(248,113,113,0.3)'}`,
        }}>
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: isCompliant ? '#4ade80' : '#f87171',
            flexShrink: 0,
          }} />
          <span style={{
            color: '#fff',
            fontSize: '10px',
            fontFamily: 'ui-monospace, monospace',
            fontWeight: 500,
            letterSpacing: '-0.01em',
          }}>
            {minCompliantDist.toFixed(1)} m
          </span>
        </div>
      </Html>
    </group>
  )
}
