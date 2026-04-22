import React, { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import type { AntennaElement } from '@/lib/antennaGain'
import {
  computeComplianceFootprint,
  smoothRadii,
  DEFAULT_OBSERVER_HEIGHT_M,
  DEFAULT_MAX_RADIUS_M,
  type FootprintResult,
} from '@/lib/complianceFootprint'

const N_AZIMUTH = 128
const RING_THICKNESS = 0.04
const SMOOTHING_PASSES = 2
// Head-of-standing-adult estimate: the body centre in scene coords
// is bodyOffset.y + 0.6, matching DistanceLine.
const BODY_CENTER_Y_OFFSET = 0.6

// ---------------------------------------------------------------------------
// Geometry builders
// ---------------------------------------------------------------------------

function buildDiscGeometry(radii: Float32Array): THREE.ShapeGeometry {
  const shape = new THREE.Shape()
  const n = radii.length
  for (let i = 0; i <= n; i++) {
    const idx = i % n
    const az = (idx / n) * 2 * Math.PI
    const r = radii[idx]
    const sx = Math.sin(az) * r
    const sy = -Math.cos(az) * r
    if (i === 0) shape.moveTo(sx, sy)
    else shape.lineTo(sx, sy)
  }
  return new THREE.ShapeGeometry(shape, 1)
}

function buildRingGeometry(radii: Float32Array): THREE.BufferGeometry {
  const n = radii.length
  const nVerts = n * 2
  const positions = new Float32Array(nVerts * 3)
  const indices: number[] = []

  for (let i = 0; i < n; i++) {
    const az = (i / n) * 2 * Math.PI
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

    const j = (i + 1) % n
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
 * Renders a ground-plane ICNIRP compliance footprint around the antenna.
 *
 * Solves per-azimuth for the horizontal radius where the incident power
 * density equals the compliance limit, at an observer height of 1.5 m. Uses
 * the full 3-D antenna pattern (so vertical pattern and antenna height are
 * honoured) and the body compute's margin_db as the reference. For a
 * uniform pattern the footprint collapses to a circle.
 */
export default function ComplianceRing() {
  const stats = useSimulationStore(s => s.stats)
  const compliance = useSimulationStore(s => s.compliance)
  const antennaPos = useSimulationStore(s => s.antennaPos)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const appliedPattern = useSimulationStore(s => s.appliedPattern)
  const appliedPatternMeta = useSimulationStore(s => s.appliedPatternMeta)
  const config = useSceneStore(s => s.viewerConfig)
  const complianceRingVisible = useSceneStore(s => s.complianceRingVisible)

  const ringGroupRef = useRef<THREE.Group>(null)
  const prevDiscRef = useRef<THREE.BufferGeometry | null>(null)
  const prevRingRef = useRef<THREE.BufferGeometry | null>(null)

  const distanceM = stats?.distance_m
  const marginDb = compliance?.margin_db

  const footprint: FootprintResult | null = useMemo(() => {
    if (marginDb == null || !Number.isFinite(marginDb)) return null
    if (distanceM == null || !(distanceM > 0)) return null
    if (!antennaPos || !bodyOffset || !config) return null

    const poleH = config.antenna?.pole_height ?? 2
    const rp = config.antenna?.radiation_pattern
    const type = rp?.type ?? 'short_dipole'
    const elements: AntennaElement[] = rp?.elements?.length
      ? rp.elements
      : [{ offset: [0, 0, 0], weight: [1, 0], axis: [0, 1, 0] }]
    const useApplied = !!(appliedPattern && appliedPatternMeta)

    return computeComplianceFootprint({
      antennaRadiatorPos: [antennaPos[0], antennaPos[1] + poleH, antennaPos[2]],
      bodyCenterPos: [bodyOffset[0], bodyOffset[1] + BODY_CENTER_Y_OFFSET, bodyOffset[2]],
      marginDb,
      observerHeightM: DEFAULT_OBSERVER_HEIGHT_M,
      patternType: type,
      elements,
      appliedPattern: useApplied ? appliedPattern : null,
      nAzimuth: N_AZIMUTH,
      maxRadiusM: DEFAULT_MAX_RADIUS_M,
    })
  }, [marginDb, distanceM, antennaPos, bodyOffset, appliedPattern, appliedPatternMeta, config])

  const boundary = useMemo(() => {
    prevDiscRef.current?.dispose()
    prevRingRef.current?.dispose()
    prevDiscRef.current = null
    prevRingRef.current = null

    if (!footprint) {
      return { discGeo: null, ringGeo: null, displayDist: 0, isCircular: true }
    }

    // Degenerate means the 3-D iso-S_inc surface never intersects the observer
    // plane (common for tall antennas with a comfortable compliance margin).
    // Fall back to the horizontal-slice approximation: the radius at which
    // S_inc = S_limit ignoring the vertical geometry.
    if (footprint.degenerate) {
      if (marginDb == null || distanceM == null || !(distanceM > 0)) {
        return { discGeo: null, ringGeo: null, displayDist: 0, isCircular: true }
      }
      const r = distanceM * Math.pow(10, -marginDb / 20)
      if (!(r >= 0.1) || r > DEFAULT_MAX_RADIUS_M) {
        return { discGeo: null, ringGeo: null, displayDist: 0, isCircular: true }
      }
      return { discGeo: null, ringGeo: null, displayDist: r, isCircular: true }
    }

    // For uniform patterns the solver already returns near-equal radii; render
    // a proper circleGeometry at the footprint radius for smoother edges.
    if (footprint.isCircular) {
      return { discGeo: null, ringGeo: null, displayDist: footprint.maxR, isCircular: true }
    }

    // Sanity clamp: if the ring is under 0.1 m or over the safety cap, bail out.
    if (footprint.maxR < 0.1) {
      return { discGeo: null, ringGeo: null, displayDist: 0, isCircular: true }
    }

    const smoothed = smoothRadii(footprint.radii, SMOOTHING_PASSES)
    const discGeo = buildDiscGeometry(smoothed)
    const ringGeo = buildRingGeometry(smoothed)

    prevDiscRef.current = discGeo
    prevRingRef.current = ringGeo

    return { discGeo, ringGeo, displayDist: footprint.maxR, isCircular: false }
  }, [footprint, marginDb, distanceM])

  useEffect(() => () => {
    prevDiscRef.current?.dispose()
    prevRingRef.current?.dispose()
  }, [])

  useFrame(({ clock }) => {
    if (!ringGroupRef.current) return
    const s = 1 + 0.015 * Math.sin(clock.getElapsedTime() * 1.5)
    ringGroupRef.current.scale.set(s, s, s)
  })

  if (!complianceRingVisible || !antennaPos || !footprint) return null
  if (boundary.displayDist <= 0) return null

  const poleH = config?.antenna?.pole_height ?? 2
  const centerX = antennaPos[0]
  const centerZ = antennaPos[2]
  const isCompliant = compliance?.overall_pass ?? false
  const colors = resolveRingColors(isCompliant)

  const sharedProps = { centerX, centerZ, colors, poleH, displayDist: boundary.displayDist, isCompliant, ringGroupRef }

  if (boundary.isCircular) {
    return <CircularBoundary {...sharedProps} minCompliantDist={boundary.displayDist} />
  }
  return <DirectionalBoundary {...sharedProps} discGeo={boundary.discGeo} ringGeo={boundary.ringGeo} />
}
