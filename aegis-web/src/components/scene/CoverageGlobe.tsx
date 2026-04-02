import { useRef, useMemo, useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Html, Line } from '@react-three/drei'
import * as THREE from 'three'
import { useCoverageStore } from '@/stores/coverage'
import { latLonToECEF, ecefToLatLon, WGS84_A } from '@/lib/geo'

const TIER1_ALTITUDE_M = 2_000_000
const TIER2_ALTITUDE_M = 200_000

const COMPLETENESS_COLORS: Record<string, string> = {
  high: '#22c55e',
  medium: '#f59e0b',
  low: '#ef4444',
}

function completenessColor(c: number): string {
  if (c > 0.8) return COMPLETENESS_COLORS.high
  if (c > 0.4) return COMPLETENESS_COLORS.medium
  return COMPLETENESS_COLORS.low
}

/** Tier 1: region boundary rectangles and floating labels. */
function RegionBoundaries() {
  const regions = useCoverageStore(s => s.regions)

  return (
    <>
      {regions.map(r => {
        if (!r.bbox) return null
        const [minLon, maxLon, minLat, maxLat] = r.bbox
        const alt = 1000 // slightly above surface
        const corners = [
          latLonToECEF(minLat, minLon, alt),
          latLonToECEF(minLat, maxLon, alt),
          latLonToECEF(maxLat, maxLon, alt),
          latLonToECEF(maxLat, minLon, alt),
          latLonToECEF(minLat, minLon, alt), // close
        ]
        const points = corners.map(v => [v.x, v.y, v.z] as [number, number, number])
        const center = latLonToECEF(
          (minLat + maxLat) / 2,
          (minLon + maxLon) / 2,
          alt + 5000,
        )

        return (
          <group key={r.name}>
            <Line
              points={points}
              color={completenessColor(r.completeness)}
              lineWidth={2}
            />
            <Html position={[center.x, center.y, center.z]} center distanceFactor={1_000_000}>
              <div className="pointer-events-auto whitespace-nowrap rounded bg-zinc-900/90 px-2 py-1 text-xs text-white shadow-lg border border-zinc-700">
                <div className="font-medium">{r.label}</div>
                <div className="text-zinc-400">{r.count.toLocaleString()} antennas</div>
              </div>
            </Html>
          </group>
        )
      })}
    </>
  )
}

/** Tier 2: instanced cluster markers. */
function ClusterMarkers() {
  const clusters = useCoverageStore(s => s.clusters)
  const operatorNames = useCoverageStore(s => s.operatorNames)
  const meshRef = useRef<THREE.InstancedMesh>(null)

  const OPERATOR_COLORS: [number, number, number][] = useMemo(() => [
    [0.23, 0.51, 0.96], [0.96, 0.51, 0.11], [0.18, 0.76, 0.49],
    [0.66, 0.33, 0.83], [0.91, 0.30, 0.24], [0.10, 0.74, 0.81],
    [0.98, 0.75, 0.18], [0.55, 0.34, 0.16], [0.44, 0.50, 0.56],
    [0.84, 0.37, 0.65], [0.40, 0.65, 0.12], [0.70, 0.20, 0.36],
  ], [])

  useEffect(() => {
    const mesh = meshRef.current
    if (!mesh || clusters.length === 0) return

    const dummy = new THREE.Object3D()
    const color = new THREE.Color()
    const up = new THREE.Vector3()
    const quat = new THREE.Quaternion()
    const defaultUp = new THREE.Vector3(0, 0, 1)

    for (let i = 0; i < clusters.length; i++) {
      const c = clusters[i]
      const pos = latLonToECEF(c.lat, c.lon, 500)
      const scale = Math.max(1, Math.log2(c.count)) * 5000

      dummy.position.copy(pos)
      // Orient circle tangent to globe surface
      up.copy(pos).normalize()
      quat.setFromUnitVectors(defaultUp, up)
      dummy.quaternion.copy(quat)
      dummy.scale.set(scale, scale, 1)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)

      const opIdx = operatorNames.indexOf(c.operator)
      const rgb = OPERATOR_COLORS[Math.max(0, opIdx) % OPERATOR_COLORS.length]
      color.setRGB(rgb[0], rgb[1], rgb[2])
      mesh.setColorAt(i, color)
    }

    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  }, [clusters, operatorNames, OPERATOR_COLORS])

  if (clusters.length === 0) return null

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, clusters.length]}>
      <circleGeometry args={[1, 16]} />
      <meshBasicMaterial transparent opacity={0.7} side={THREE.DoubleSide} />
    </instancedMesh>
  )
}

/** Tier 3: site point cloud. */
function SitePoints() {
  const positions = useCoverageStore(s => s.sitePositions)
  const colors = useCoverageStore(s => s.siteColors)

  if (!positions || !colors) return null

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" array={positions} count={positions.length / 3} itemSize={3} />
        <bufferAttribute attach="attributes-color" array={colors} count={colors.length / 3} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={3000} sizeAttenuation vertexColors transparent opacity={0.8} />
    </points>
  )
}

/** Camera-controlled initial position for coverage globe. */
function CoverageCamera() {
  const { camera } = useThree()
  const initialized = useRef(false)

  useFrame(() => {
    if (initialized.current) return
    initialized.current = true
    // Position camera high above equator for full-Earth view
    const pos = latLonToECEF(20, 10, 20_000_000)
    camera.position.set(pos.x, pos.y, pos.z)
    camera.lookAt(0, 0, 0)
    camera.updateProjectionMatrix()
  })

  return null
}

export function CoverageGlobe() {
  const enabled = useCoverageStore(s => s.enabled)
  const loaded = useCoverageStore(s => s.loaded)
  const activeTier = useCoverageStore(s => s.activeTier)
  const { camera } = useThree()

  // Update active tier and camera lat/lon each frame
  useFrame(() => {
    if (!enabled) return
    const store = useCoverageStore.getState()
    const altitude = camera.position.length() - WGS84_A

    let tier: 1 | 2 | 3
    if (altitude > TIER1_ALTITUDE_M) tier = 1
    else if (altitude > TIER2_ALTITUDE_M) tier = 2
    else tier = 3
    if (tier !== store.activeTier) store.setActiveTier(tier)

    // Write camera altitude and lat/lon to store for HUD to read
    store.setCameraAltitude(altitude)
    if (altitude < TIER2_ALTITUDE_M) {
      const ll = ecefToLatLon(camera.position)
      store.setCameraLatLon(ll)
    }
  })

  if (!enabled || !loaded) return null

  return (
    <group>
      <CoverageCamera />
      {/* Region boundaries visible at tier 1 and 2 */}
      <group visible={activeTier <= 2}>
        <RegionBoundaries />
      </group>
      <group visible={activeTier === 2}>
        <ClusterMarkers />
      </group>
      <group visible={activeTier === 3}>
        <SitePoints />
      </group>
    </group>
  )
}
