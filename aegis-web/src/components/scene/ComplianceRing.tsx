import React, { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { scalarRadiationGain, interpolatePatternGain, type AntennaElement } from '@/lib/antennaGain'

const N_AZIMUTH = 128
const RING_THICKNESS = 0.04
const SMOOTHING_PASSES = 2

// ---------------------------------------------------------------------------
// Pure helpers (module scope)
// ---------------------------------------------------------------------------

function sampleHorizontalGains(
  nAzimuth: number,
  useApplied: boolean,
  appliedPattern: Float32Array | null | undefined,
  type: string,
  elements: AntennaElement[],
): { gains: Float32Array; gMean: number; gMax: number; gMin: number } {
  const gains = new Float32Array(nAzimuth)
  const dir = new THREE.Vector3()
  let gMean = 0
  let gMax = -Infinity
  let gMin = Infinity

  for (let i = 0; i < nAzimuth; i++) {
    const az = (i / nAzimuth) * 2 * Math.PI
    dir.set(Math.sin(az), 0, Math.cos(az))
    const g = (useApplied && appliedPattern)
      ? interpolatePatternGain(dir, appliedPattern)
      : scalarRadiationGain(dir, type, elements)
    gains[i] = g
    gMean += g
    if (g > gMax) gMax = g
    if (g < gMin) gMin = g
  }
  gMean /= nAzimuth
  return { gains, gMean, gMax, gMin }
}

function smoothGains(gains: Float32Array, passes: number): void {
  for (let pass = 0; pass < passes; pass++) {
    const n = gains.length
    const smoothed = new Float32Array(n)
    for (let i = 0; i < n; i++) {
      const prev = gains[(i - 1 + n) % n]
      const next = gains[(i + 1) % n]
      smoothed[i] = 0.25 * prev + 0.5 * gains[i] + 0.25 * next
    }
    gains.set(smoothed)
  }
}

function buildRadii(gains: Float32Array, baseDist: number): { radii: Float32Array; maxR: number; gMean: number } {
  let gMean = 0
  const n = gains.length
  for (let i = 0; i < n; i++) gMean += gains[i]
  gMean /= n

  const radii = new Float32Array(n)
  let maxR = 0
  for (let i = 0; i < n; i++) {
    radii[i] = baseDist * Math.sqrt(gains[i] / gMean)
    if (radii[i] > maxR) maxR = radii[i]
  }
  return { radii, maxR, gMean }
}

function buildDiscGeometry(radii: Float32Array, nAzimuth: number): THREE.ShapeGeometry {
  const shape = new THREE.Shape()
  for (let i = 0; i <= nAzimuth; i++) {
    const idx = i % nAzimuth
    const az = (idx / nAzimuth) * 2 * Math.PI
    const r = radii[idx]
    const sx = Math.sin(az) * r
    const sy = -Math.cos(az) * r
    if (i === 0) shape.moveTo(sx, sy)
    else shape.lineTo(sx, sy)
  }
  return new THREE.ShapeGeometry(shape, 1)
}

function buildRingGeometry(radii: Float32Array, nAzimuth: number): THREE.BufferGeometry {
  const nVerts = nAzimuth * 2
  const positions = new Float32Array(nVerts * 3)
  const indices: number[] = []

  for (let i = 0; i < nAzimuth; i++) {
    const az = (i / nAzimuth) * 2 * Math.PI
    const r = radii[i]
    const rOuter = r + RING_THICKNESS
    const rInner = Math.max(r - RING_THICKNESS, 0)
    const cx = Math.sin(az)
    const cy = -Math.cos(az)

    const oi = i * 2
    const ii = i * 2 + 1
    positions[oi * 3] = cx * rOuter
    positions[oi * 3 + 1] = cy * rOuter
    positions[oi * 3 + 2] = 0
    positions[ii * 3] = cx * rInner
    positions[ii * 3 + 1] = cy * rInner
    positions[ii * 3 + 2] = 0

    const j = (i + 1) % nAzimuth
    indices.push(oi, ii, j * 2)
    indices.push(j * 2, ii, j * 2 + 1)
  }

  const ringGeo = new THREE.BufferGeometry()
  ringGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  ringGeo.setIndex(indices)
  ringGeo.computeVertexNormals()
  return ringGeo
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ComplianceLabel({
  displayDist,
  poleH,
  isCompliant,
}: {
  displayDist: number
  poleH: number
  isCompliant: boolean
}) {
  return (
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
}

// ---------------------------------------------------------------------------
// Render helpers
// ---------------------------------------------------------------------------

interface RingColors { discColor: string; discOpacity: number; ringColor: string }

function resolveRingColors(isCompliant: boolean): RingColors {
  return {
    discColor: isCompliant ? '#16a34a' : '#dc2626',
    discOpacity: isCompliant ? 0.06 : 0.10,
    ringColor: isCompliant ? '#4ade80' : '#f87171',
  }
}

function CircularBoundary({
  centerX, centerZ, minCompliantDist, colors, poleH, displayDist, isCompliant, ringGroupRef,
}: {
  centerX: number; centerZ: number; minCompliantDist: number
  colors: RingColors; poleH: number; displayDist: number; isCompliant: boolean
  ringGroupRef: React.RefObject<THREE.Group | null>
}) {
  return (
    <group position={[centerX, 0.005, centerZ]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[minCompliantDist, 64]} />
        <meshBasicMaterial color={colors.discColor} transparent opacity={colors.discOpacity} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <group ref={ringGroupRef}>
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[minCompliantDist - RING_THICKNESS, minCompliantDist + RING_THICKNESS, 64]} />
          <meshBasicMaterial color={colors.ringColor} transparent opacity={0.5} side={THREE.DoubleSide} depthWrite={false} />
        </mesh>
      </group>
      <ComplianceLabel displayDist={displayDist} poleH={poleH} isCompliant={isCompliant} />
    </group>
  )
}

function DirectionalBoundary({
  centerX, centerZ, discGeo, ringGeo, colors, poleH, displayDist, isCompliant, ringGroupRef,
}: {
  centerX: number; centerZ: number
  discGeo: THREE.BufferGeometry | null; ringGeo: THREE.BufferGeometry | null
  colors: RingColors; poleH: number; displayDist: number; isCompliant: boolean
  ringGroupRef: React.RefObject<THREE.Group | null>
}) {
  return (
    <group position={[centerX, 0.005, centerZ]}>
      {discGeo && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} geometry={discGeo}>
          <meshBasicMaterial color={colors.discColor} transparent opacity={colors.discOpacity} side={THREE.DoubleSide} depthWrite={false} />
        </mesh>
      )}
      <group ref={ringGroupRef}>
        {ringGeo && (
          <mesh rotation={[-Math.PI / 2, 0, 0]} geometry={ringGeo}>
            <meshBasicMaterial color={colors.ringColor} transparent opacity={0.5} side={THREE.DoubleSide} depthWrite={false} />
          </mesh>
        )}
      </group>
      <ComplianceLabel displayDist={displayDist} poleH={poleH} isCompliant={isCompliant} />
    </group>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

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

  const minCompliantDist = useMemo(() => {
    if (marginDb == null || distanceM == null || distanceM <= 0) return null
    if (!Number.isFinite(marginDb)) return null
    const d = distanceM * Math.pow(10, -marginDb / 20)
    if (d < 0.1 || d > 500) return null
    return d
  }, [marginDb, distanceM])

  const boundary = useMemo(() => {
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

    const { gains, gMean, gMax, gMin } = sampleHorizontalGains(
      N_AZIMUTH, useApplied, appliedPattern, type, elements,
    )

    if (gMean <= 0 || gMax <= 0 || (gMax - gMin) / gMax < 0.02) {
      return { discGeo: null, ringGeo: null, maxDist: minCompliantDist, isCircular: true }
    }

    smoothGains(gains, SMOOTHING_PASSES)
    const { radii, maxR } = buildRadii(gains, minCompliantDist)

    const discGeo = buildDiscGeometry(radii, N_AZIMUTH)
    const ringGeo = buildRingGeometry(radii, N_AZIMUTH)

    prevDiscRef.current = discGeo
    prevRingRef.current = ringGeo

    return { discGeo, ringGeo, maxDist: maxR, isCircular: false }
  }, [minCompliantDist, config, appliedPattern, appliedPatternMeta])

  useEffect(() => () => {
    prevDiscRef.current?.dispose()
    prevRingRef.current?.dispose()
  }, [])

  useFrame(({ clock }) => {
    if (!ringGroupRef.current) return
    const s = 1 + 0.015 * Math.sin(clock.getElapsedTime() * 1.5)
    ringGroupRef.current.scale.set(s, s, s)
  })

  if (!complianceRingVisible || !antennaPos || minCompliantDist == null) return null

  const poleH = config?.antenna?.pole_height ?? 2
  const centerX = antennaPos[0]
  const centerZ = antennaPos[2]
  const isCompliant = compliance?.overall_pass ?? false
  const colors = resolveRingColors(isCompliant)
  const displayDist = boundary.isCircular ? minCompliantDist : boundary.maxDist

  const sharedProps = { centerX, centerZ, colors, poleH, displayDist, isCompliant, ringGroupRef }

  if (boundary.isCircular) {
    return <CircularBoundary {...sharedProps} minCompliantDist={minCompliantDist} />
  }
  return <DirectionalBoundary {...sharedProps} discGeo={boundary.discGeo} ringGeo={boundary.ringGeo} />
}
