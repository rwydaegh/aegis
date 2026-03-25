import { useRef, useMemo } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { formatSab } from '@/lib/format'

/** 4 cm² averaging circle radius in meters: r = sqrt(4e-4 / pi) ≈ 0.01128 */
const AVG_RADIUS = Math.sqrt(4e-4 / Math.PI)
const TUBE_RADIUS = 0.0015

interface PeakInfo {
  position: THREE.Vector3
  normal: THREE.Vector3
  quaternion: THREE.Quaternion
}

interface PeakIndicatorProps {
  /** Override geometry (MIMO per-user mode) */
  geometryOverride?: THREE.BufferGeometry | null
  /** Override sab array (MIMO per-user mode) */
  sabOverride?: Float32Array | null
  /** Override peak value label */
  peakValueOverride?: number | null
  /** Override compliance status */
  compliantOverride?: boolean | null
}

export default function PeakIndicator({
  geometryOverride,
  sabOverride,
  peakValueOverride,
  compliantOverride,
}: PeakIndicatorProps = {}) {
  const ringRef = useRef<THREE.Mesh>(null)

  // Global stores as fallback for single-user mode
  const globalGeometry = useSceneStore(s => s.bodyGeometry)
  const globalSabArray = useSimulationStore(s => s.sabArray)
  const globalSabAveraged = useSimulationStore(s => s.sabAveragedArray)
  const globalStats = useSimulationStore(s => s.stats)

  // Use overrides if provided, otherwise fall back to global stores
  const geometry = geometryOverride ?? globalGeometry
  const sabArray = sabOverride ?? globalSabAveraged ?? globalSabArray
  const peakValue = peakValueOverride ?? globalStats?.peak_sab_averaged ?? globalStats?.peak_sab ?? null
  const compliant = compliantOverride ?? globalStats?.compliant ?? null

  // Find peak triangle and compute position + normal
  const peak: PeakInfo | null = useMemo(() => {
    if (!sabArray || !geometry) return null

    // Find peak triangle index
    let maxVal = -Infinity
    let maxIdx = 0
    for (let i = 0; i < sabArray.length; i++) {
      if (sabArray[i] > maxVal) { maxVal = sabArray[i]; maxIdx = i }
    }

    const posAttr = geometry.getAttribute('position') as THREE.BufferAttribute
    if (!posAttr) return null

    const baseVertex = maxIdx * 3
    if (baseVertex + 2 >= posAttr.count) return null

    // Triangle vertices
    const v0 = new THREE.Vector3().fromBufferAttribute(posAttr, baseVertex)
    const v1 = new THREE.Vector3().fromBufferAttribute(posAttr, baseVertex + 1)
    const v2 = new THREE.Vector3().fromBufferAttribute(posAttr, baseVertex + 2)

    // Centroid
    const position = new THREE.Vector3().addVectors(v0, v1).add(v2).divideScalar(3)

    // Face normal
    const edge1 = new THREE.Vector3().subVectors(v1, v0)
    const edge2 = new THREE.Vector3().subVectors(v2, v0)
    const normal = new THREE.Vector3().crossVectors(edge1, edge2).normalize()

    // Quaternion to orient the torus (default torus lies in XZ, normal along Y)
    const quaternion = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(0, 1, 0),
      normal,
    )

    return { position, normal, quaternion }
  }, [sabArray, geometry])

  // Breathing animation
  useFrame(({ clock }) => {
    if (!ringRef.current) return
    const s = 1 + 0.06 * Math.sin(clock.getElapsedTime() * 2.5)
    ringRef.current.scale.setScalar(s)
  })

  if (!peak) return null

  return (
    <group position={peak.position} quaternion={peak.quaternion}>
      {/* Averaging area ring (4 cm²) */}
      <mesh ref={ringRef}>
        <torusGeometry args={[AVG_RADIUS, TUBE_RADIUS, 8, 48]} />
        <meshBasicMaterial
          color="#ffffff"
          transparent
          opacity={0.75}
          depthTest={false}
        />
      </mesh>

      {/* Floating label - pixel offset so it works at any zoom level */}
      <Html
        position={[0, 0, 0]}
        center
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        <div style={{
          transform: 'translate(60px, -20px)',
          background: 'rgba(0,0,0,0.78)',
          backdropFilter: 'blur(6px)',
          borderRadius: '6px',
          padding: '3px 8px',
          whiteSpace: 'nowrap',
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
          border: '1px solid rgba(255,255,255,0.12)',
        }}>
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: compliant === false ? '#f87171' : '#4ade80',
            flexShrink: 0,
          }} />
          <span style={{
            color: '#fff',
            fontSize: '11px',
            fontFamily: 'ui-monospace, monospace',
            fontWeight: 500,
            letterSpacing: '-0.01em',
          }}>
            {peakValue != null ? formatSab(peakValue) : '--'}
          </span>
        </div>
      </Html>
    </group>
  )
}
