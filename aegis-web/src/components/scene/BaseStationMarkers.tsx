import { useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useBaseStationsStore } from '@/stores/basestations'
import type { BaseStationData } from '@/api/basestations'

const OPERATOR_COLORS: Record<string, string> = {
  Proximus: '#2563eb',
  Orange: '#f97316',
  Telenet: '#22c55e',
  'Base (Telenet)': '#16a34a',
}
const DEFAULT_COLOR = '#a855f7'

const POLE_RADIUS = 0.15
const SPHERE_RADIUS = 0.5

function bsToScenePos(
  bs: BaseStationData,
  origin: { lat: number; lon: number },
): [number, number, number] {
  const R = 6_371_000
  const dlat = (bs.latitude - origin.lat) * Math.PI / 180
  const dlon = (bs.longitude - origin.lon) * Math.PI / 180
  const cosLat = Math.cos(origin.lat * Math.PI / 180)
  const east = R * dlon * cosLat
  const north = R * dlat
  return [east, bs.height_m, -north]
}

function getColor(operator: string): THREE.Color {
  return new THREE.Color(OPERATOR_COLORS[operator] ?? DEFAULT_COLOR)
}

export default function BaseStationMarkers() {
  const basestations = useBaseStationsStore(s => s.basestations)
  const origin = useBaseStationsStore(s => s.origin)
  const enabledOperators = useBaseStationsStore(s => s.enabledOperators)
  const enabledTechnologies = useBaseStationsStore(s => s.enabledTechnologies)

  const poleRef = useRef<THREE.InstancedMesh>(null)
  const sphereRef = useRef<THREE.InstancedMesh>(null)

  const activeStations = useMemo(() => {
    if (!origin) return []
    return basestations
      .map((bs, idx) => ({ bs, idx }))
      .filter(({ bs }) => enabledOperators.has(bs.operator) && enabledTechnologies.has(bs.technology))
  }, [basestations, origin, enabledOperators, enabledTechnologies])

  useMemo(() => {
    if (!origin || activeStations.length === 0) return
    const poleMesh = poleRef.current
    const sphereMesh = sphereRef.current
    if (!poleMesh || !sphereMesh) return

    const dummy = new THREE.Object3D()
    const color = new THREE.Color()

    for (let i = 0; i < activeStations.length; i++) {
      const { bs } = activeStations[i]
      const [x, y, z] = bsToScenePos(bs, origin)

      // Pole: cylinder from ground to height
      dummy.position.set(x, y / 2, z)
      dummy.scale.set(1, y, 1)
      dummy.rotation.set(0, 0, 0)
      dummy.updateMatrix()
      poleMesh.setMatrixAt(i, dummy.matrix)

      // Sphere at top
      dummy.position.set(x, y, z)
      dummy.scale.set(1, 1, 1)
      dummy.updateMatrix()
      sphereMesh.setMatrixAt(i, dummy.matrix)

      // Color
      color.copy(getColor(bs.operator))
      poleMesh.setColorAt(i, color)
      sphereMesh.setColorAt(i, color)
    }

    poleMesh.count = activeStations.length
    sphereMesh.count = activeStations.length
    poleMesh.instanceMatrix.needsUpdate = true
    sphereMesh.instanceMatrix.needsUpdate = true
    if (poleMesh.instanceColor) poleMesh.instanceColor.needsUpdate = true
    if (sphereMesh.instanceColor) sphereMesh.instanceColor.needsUpdate = true
  }, [activeStations, origin])

  if (!origin || activeStations.length === 0) return null

  const maxCount = Math.max(activeStations.length, 1)

  return (
    <>
      <instancedMesh ref={poleRef} args={[undefined, undefined, maxCount]}>
        <cylinderGeometry args={[POLE_RADIUS, POLE_RADIUS, 1, 6]} />
        <meshStandardMaterial />
      </instancedMesh>
      <instancedMesh ref={sphereRef} args={[undefined, undefined, maxCount]}>
        <sphereGeometry args={[SPHERE_RADIUS, 8, 8]} />
        <meshStandardMaterial />
      </instancedMesh>
    </>
  )
}
