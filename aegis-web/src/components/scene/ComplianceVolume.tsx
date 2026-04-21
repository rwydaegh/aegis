import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import type { AntennaElement } from '@/lib/antennaGain'
import {
  computeComplianceVolume,
  DEFAULT_MAX_RADIUS_M,
  type VolumeResult,
} from '@/lib/complianceFootprint'

const N_AZIMUTH = 64
const N_ELEVATION = 33
// Body centre y-offset in scene coords; matches DistanceLine / ComplianceRing.
const BODY_CENTER_Y_OFFSET = 0.6

// Builds a triangulated UV-sphere-style surface from a row-major (az × el)
// radii grid. Each (i, j) is placed at
//   r * (cos(el) sin(az), sin(el), cos(el) cos(az))
// relative to the antenna. Triangles connect neighbouring (az, el) quads;
// the azimuth index wraps modulo N. Vertex y is clamped to world y >= 0 so
// the surface drapes the ground instead of clipping through it.
function buildVolumeGeometry(
  result: VolumeResult,
  antennaWorldPos: [number, number, number],
): THREE.BufferGeometry {
  const { radii, azimuthsRad, elevationsRad, nAzimuth, nElevation } = result
  const [ax, ay, az] = antennaWorldPos

  const positions = new Float32Array(nAzimuth * nElevation * 3)
  const colors = new Float32Array(nAzimuth * nElevation * 3)
  let rMaxForColor = 0
  for (let k = 0; k < radii.length; k++) {
    if (radii[k] > rMaxForColor) rMaxForColor = radii[k]
  }
  const rMaxSafe = Math.max(rMaxForColor, 1e-6)

  for (let i = 0; i < nAzimuth; i++) {
    const azim = azimuthsRad[i]
    const sinAz = Math.sin(azim)
    const cosAz = Math.cos(azim)
    for (let j = 0; j < nElevation; j++) {
      const el = elevationsRad[j]
      const cosEl = Math.cos(el)
      const sinEl = Math.sin(el)
      const r = radii[i * nElevation + j]
      const x = ax + r * cosEl * sinAz
      const yRaw = ay + r * sinEl
      const y = Math.max(yRaw, 0) // drape the ground, don't clip through
      const z = az + r * cosEl * cosAz
      const vi = (i * nElevation + j) * 3
      positions[vi] = x
      positions[vi + 1] = y
      positions[vi + 2] = z

      // Height-based tint: low samples (near ground) get cooler, high samples
      // (near zenith) get warmer. Multiplied into the material base colour so
      // the viewer can read vertical extent at a glance.
      const t = Math.min(Math.max((r / rMaxSafe) * 0.6 + 0.4, 0.4), 1.0)
      colors[vi] = t
      colors[vi + 1] = t
      colors[vi + 2] = t
    }
  }

  const indices: number[] = []
  // For each quad (i, j)-(i+1, j)-(i+1, j+1)-(i, j+1), emit two triangles.
  // Skip quads that would be fully degenerate (all four radii ≤ 0) to avoid
  // littering the depth buffer with zero-area slivers at the antenna origin.
  for (let i = 0; i < nAzimuth; i++) {
    const iNext = (i + 1) % nAzimuth
    for (let j = 0; j < nElevation - 1; j++) {
      const a = i * nElevation + j
      const b = iNext * nElevation + j
      const c = iNext * nElevation + (j + 1)
      const d = i * nElevation + (j + 1)
      if (radii[a] <= 0 && radii[b] <= 0 && radii[c] <= 0 && radii[d] <= 0) continue
      indices.push(a, b, c)
      indices.push(a, c, d)
    }
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
  geo.setIndex(indices)
  geo.computeVertexNormals()
  return geo
}

export default function ComplianceVolume() {
  const stats = useSimulationStore(s => s.stats)
  const compliance = useSimulationStore(s => s.compliance)
  const antennaPos = useSimulationStore(s => s.antennaPos)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const appliedPattern = useSimulationStore(s => s.appliedPattern)
  const appliedPatternMeta = useSimulationStore(s => s.appliedPatternMeta)
  const config = useSceneStore(s => s.viewerConfig)
  const visible = useSceneStore(s => s.complianceVolumeVisible)

  const prevGeoRef = useRef<THREE.BufferGeometry | null>(null)
  const prevWireRef = useRef<THREE.WireframeGeometry | null>(null)

  const distanceM = stats?.distance_m
  const marginDb = compliance?.margin_db

  const volume: VolumeResult | null = useMemo(() => {
    if (!visible) return null
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

    return computeComplianceVolume({
      antennaRadiatorPos: [antennaPos[0], antennaPos[1] + poleH, antennaPos[2]],
      bodyCenterPos: [bodyOffset[0], bodyOffset[1] + BODY_CENTER_Y_OFFSET, bodyOffset[2]],
      marginDb,
      patternType: type,
      elements,
      appliedPattern: useApplied ? appliedPattern : null,
      nAzimuth: N_AZIMUTH,
      nElevation: N_ELEVATION,
      maxRadiusM: DEFAULT_MAX_RADIUS_M,
    })
  }, [visible, marginDb, distanceM, antennaPos, bodyOffset, appliedPattern, appliedPatternMeta, config])

  const { surface, wireframe } = useMemo(() => {
    prevGeoRef.current?.dispose()
    prevWireRef.current?.dispose()
    prevGeoRef.current = null
    prevWireRef.current = null

    if (!volume || volume.degenerate || !antennaPos || !config) {
      return { surface: null, wireframe: null }
    }
    if (volume.maxR < 0.1) {
      return { surface: null, wireframe: null }
    }
    const poleH = config.antenna?.pole_height ?? 2
    const antennaWorld: [number, number, number] = [antennaPos[0], antennaPos[1] + poleH, antennaPos[2]]
    const geo = buildVolumeGeometry(volume, antennaWorld)
    const wire = new THREE.WireframeGeometry(geo)
    prevGeoRef.current = geo
    prevWireRef.current = wire
    return { surface: geo, wireframe: wire }
  }, [volume, antennaPos, config])

  useEffect(() => () => {
    prevGeoRef.current?.dispose()
    prevWireRef.current?.dispose()
  }, [])

  if (!visible || !surface || !wireframe) return null

  const isCompliant = compliance?.overall_pass ?? false
  // Matches ComplianceRing palette: green when compliant, red when exceeded.
  const surfaceColor = isCompliant ? '#22c55e' : '#dc2626'
  const edgeColor = isCompliant ? '#4ade80' : '#f87171'

  return (
    <group>
      <mesh geometry={surface}>
        <meshBasicMaterial
          color={surfaceColor}
          vertexColors
          transparent
          opacity={0.16}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
      <lineSegments geometry={wireframe}>
        <lineBasicMaterial color={edgeColor} transparent opacity={0.25} depthWrite={false} />
      </lineSegments>
    </group>
  )
}
