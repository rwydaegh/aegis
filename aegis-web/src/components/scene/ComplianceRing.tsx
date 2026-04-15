import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { scalarRadiationGain, interpolatePatternGain } from '@/lib/antennaGain'

const N_AZIMUTH = 128
const RING_THICKNESS = 0.04
const SMOOTHING_PASSES = 2

/**
 * Renders a ground-plane compliance boundary around the antenna.
 * For directional antennas (patch, uploaded patterns), the boundary
 * follows the radiation pattern shape. For uniform patterns (isotropic,
 * vertical dipole), falls back to a circle.
 */
export default function ComplianceRing() {
  const stats = useSimulationStore(s => s.stats)
  const compliance = useSimulationStore(s => s.compliance)
  const antennaPos = useSimulationStore(s => s.antennaPos)
  const appliedPattern = useSimulationStore(s => s.appliedPattern)
  const appliedPatternMeta = useSimulationStore(s => s.appliedPatternMeta)
  const config = useSceneStore(s => s.viewerConfig)
  const complianceRingVisible = useSceneStore(s => s.complianceRingVisible)

  const ringGroupRef = useRef<THREE.Group>(null)
  const prevDiscRef = useRef<THREE.BufferGeometry | null>(null)
  const prevRingRef = useRef<THREE.BufferGeometry | null>(null)

  const distanceM = stats?.distance_m
  const marginDb = compliance?.margin_db

  // Isotropic compliance distance (base radius before directivity shaping)
  const minCompliantDist = useMemo(() => {
    if (marginDb == null || distanceM == null || distanceM <= 0) return null
    if (!Number.isFinite(marginDb)) return null
    const d = distanceM * Math.pow(10, -marginDb / 20)
    if (d < 0.1 || d > 500) return null
    return d
  }, [marginDb, distanceM])

  // Compute boundary geometry: directional shape or circular fallback
  const boundary = useMemo(() => {
    // Dispose previous geometries
    prevDiscRef.current?.dispose()
    prevRingRef.current?.dispose()
    prevDiscRef.current = null
    prevRingRef.current = null

    if (minCompliantDist == null || !config) {
      return { discGeo: null, ringGeo: null, maxDist: 0, isCircular: true }
    }

    const rp = config.antenna?.radiation_pattern
    const type = rp?.type ?? 'short_dipole'
    const elements = rp?.elements?.length
      ? rp.elements
      : [{ offset: [0, 0, 0], weight: [1, 0], axis: [0, 1, 0] }]
    const useApplied = !!(appliedPattern && appliedPatternMeta)

    // Sample horizontal gain at N azimuth angles
    const gains = new Float32Array(N_AZIMUTH)
    const dir = new THREE.Vector3()
    let gMean = 0
    let gMax = -Infinity
    let gMin = Infinity

    for (let i = 0; i < N_AZIMUTH; i++) {
      const az = (i / N_AZIMUTH) * 2 * Math.PI
      dir.set(Math.sin(az), 0, Math.cos(az))
      const g = useApplied
        ? interpolatePatternGain(dir, appliedPattern!)
        : scalarRadiationGain(dir, type, elements)
      gains[i] = g
      gMean += g
      if (g > gMax) gMax = g
      if (g < gMin) gMin = g
    }
    gMean /= N_AZIMUTH

    // If pattern is nearly uniform in horizontal plane, use a circle
    if (gMean <= 0 || gMax <= 0 || (gMax - gMin) / gMax < 0.02) {
      return { discGeo: null, ringGeo: null, maxDist: minCompliantDist, isCircular: true }
    }

    // Smooth the gains to avoid jagged boundaries from noisy patterns
    for (let pass = 0; pass < SMOOTHING_PASSES; pass++) {
      const smoothed = new Float32Array(N_AZIMUTH)
      for (let i = 0; i < N_AZIMUTH; i++) {
        const prev = gains[(i - 1 + N_AZIMUTH) % N_AZIMUTH]
        const next = gains[(i + 1) % N_AZIMUTH]
        smoothed[i] = 0.25 * prev + 0.5 * gains[i] + 0.25 * next
      }
      gains.set(smoothed)
    }

    // Recompute mean after smoothing
    gMean = 0
    let maxR = 0
    for (let i = 0; i < N_AZIMUTH; i++) gMean += gains[i]
    gMean /= N_AZIMUTH

    // Build boundary radii: r(az) = baseDist * sqrt(G(az) / G_mean)
    const radii = new Float32Array(N_AZIMUTH)
    for (let i = 0; i < N_AZIMUTH; i++) {
      radii[i] = minCompliantDist * Math.sqrt(gains[i] / gMean)
      if (radii[i] > maxR) maxR = radii[i]
    }

    // --- Disc geometry (filled area) using THREE.Shape ---
    const shape = new THREE.Shape()
    for (let i = 0; i <= N_AZIMUTH; i++) {
      const idx = i % N_AZIMUTH
      const az = (idx / N_AZIMUTH) * 2 * Math.PI
      const r = radii[idx]
      // Shape XY maps to scene XZ after -90deg X rotation: shape.y -> scene -Z
      const sx = Math.sin(az) * r
      const sy = -Math.cos(az) * r
      if (i === 0) shape.moveTo(sx, sy)
      else shape.lineTo(sx, sy)
    }
    const discGeo = new THREE.ShapeGeometry(shape, 1)

    // --- Ring geometry (boundary outline strip) ---
    const nVerts = N_AZIMUTH * 2
    const positions = new Float32Array(nVerts * 3)
    const indices: number[] = []

    for (let i = 0; i < N_AZIMUTH; i++) {
      const az = (i / N_AZIMUTH) * 2 * Math.PI
      const r = radii[i]
      const rOuter = r + RING_THICKNESS
      const rInner = Math.max(r - RING_THICKNESS, 0)
      const cx = Math.sin(az)
      const cy = -Math.cos(az)

      const oi = i * 2
      const ii = i * 2 + 1
      // Laid out in XY plane (will be rotated to XZ)
      positions[oi * 3] = cx * rOuter
      positions[oi * 3 + 1] = cy * rOuter
      positions[oi * 3 + 2] = 0
      positions[ii * 3] = cx * rInner
      positions[ii * 3 + 1] = cy * rInner
      positions[ii * 3 + 2] = 0

      const j = (i + 1) % N_AZIMUTH
      indices.push(oi, ii, j * 2)
      indices.push(j * 2, ii, j * 2 + 1)
    }

    const ringGeo = new THREE.BufferGeometry()
    ringGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    ringGeo.setIndex(indices)
    ringGeo.computeVertexNormals()

    prevDiscRef.current = discGeo
    prevRingRef.current = ringGeo

    return { discGeo, ringGeo, maxDist: maxR, isCircular: false }
  }, [minCompliantDist, config, appliedPattern, appliedPatternMeta])

  // Clean up geometries on unmount
  useEffect(() => () => {
    prevDiscRef.current?.dispose()
    prevRingRef.current?.dispose()
  }, [])

  // Subtle breathing animation on the ring
  useFrame(({ clock }) => {
    if (!ringGroupRef.current) return
    const s = 1 + 0.015 * Math.sin(clock.getElapsedTime() * 1.5)
    ringGroupRef.current.scale.set(s, s, s)
  })

  if (!complianceRingVisible) return null
  if (!antennaPos || minCompliantDist == null) return null

  const poleH = config?.antenna?.pole_height ?? 2
  const centerX = antennaPos[0]
  const centerZ = antennaPos[2]

  const isCompliant = compliance?.overall_pass ?? false
  const discColor = isCompliant ? '#16a34a' : '#dc2626'
  const discOpacity = isCompliant ? 0.06 : 0.10
  const ringColor = isCompliant ? '#4ade80' : '#f87171'
  const displayDist = boundary.isCircular ? minCompliantDist : boundary.maxDist

  const label = (
    <Html
      position={[0, poleH + 0.3, -displayDist]}
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
          {displayDist.toFixed(1)} m
        </span>
      </div>
    </Html>
  )

  // Circular fallback for uniform patterns
  if (boundary.isCircular) {
    return (
      <group position={[centerX, 0.005, centerZ]}>
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <circleGeometry args={[minCompliantDist, 64]} />
          <meshBasicMaterial
            color={discColor}
            transparent
            opacity={discOpacity}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
        <group ref={ringGroupRef}>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[minCompliantDist - RING_THICKNESS, minCompliantDist + RING_THICKNESS, 64]} />
            <meshBasicMaterial
              color={ringColor}
              transparent
              opacity={0.5}
              side={THREE.DoubleSide}
              depthWrite={false}
            />
          </mesh>
        </group>
        {label}
      </group>
    )
  }

  // Directional boundary
  return (
    <group position={[centerX, 0.005, centerZ]}>
      {boundary.discGeo && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} geometry={boundary.discGeo}>
          <meshBasicMaterial
            color={discColor}
            transparent
            opacity={discOpacity}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      )}
      <group ref={ringGroupRef}>
        {boundary.ringGeo && (
          <mesh rotation={[-Math.PI / 2, 0, 0]} geometry={boundary.ringGeo}>
            <meshBasicMaterial
              color={ringColor}
              transparent
              opacity={0.5}
              side={THREE.DoubleSide}
              depthWrite={false}
            />
          </mesh>
        )}
      </group>
      {label}
    </group>
  )
}
