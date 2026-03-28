import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { useBaseStationsStore } from '@/stores/basestations'
import type { BaseStationData } from '@/api/basestations'

const OPERATOR_COLORS: Record<string, string> = {
  Proximus: '#4488ff',
  Orange: '#f97316',
  Telenet: '#22c55e',
  'Citymesh Mobile (Insky)': '#e879f9',
}
const DEFAULT_COLOR = '#a855f7'

const POLE_RADIUS = 0.08
const SPHERE_RADIUS = 0.4

function bsToScenePos(
  bs: BaseStationData,
  origin: { lat: number; lon: number },
): [number, number, number] {
  const R = 6_371_000
  const dlat = ((bs.latitude - origin.lat) * Math.PI) / 180
  const dlon = ((bs.longitude - origin.lon) * Math.PI) / 180
  const cosLat = Math.cos((origin.lat * Math.PI) / 180)
  const east = R * dlon * cosLat
  const north = R * dlat
  return [east, bs.height_m, -north]
}

export default function BaseStationMarkers() {
  const basestations = useBaseStationsStore((s) => s.basestations)
  const origin = useBaseStationsStore((s) => s.origin)
  const enabledOperators = useBaseStationsStore((s) => s.enabledOperators)
  const enabledTechnologies = useBaseStationsStore((s) => s.enabledTechnologies)
  const groupRef = useRef<THREE.Group>(null)

  useEffect(() => {
    const group = groupRef.current
    if (!group || !origin) return

    // Clear previous
    while (group.children.length > 0) group.remove(group.children[0])

    const active = basestations.filter(
      (bs) => enabledOperators.has(bs.operator) && enabledTechnologies.has(bs.technology),
    )
    if (active.length === 0) return

    // Build instanced meshes
    const poleGeo = new THREE.CylinderGeometry(POLE_RADIUS, POLE_RADIUS, 1, 6)
    const sphereGeo = new THREE.SphereGeometry(SPHERE_RADIUS, 8, 6)
    const mat = new THREE.MeshStandardMaterial({ roughness: 0.6, metalness: 0.3 })

    const poles = new THREE.InstancedMesh(poleGeo, mat.clone(), active.length)
    const spheres = new THREE.InstancedMesh(sphereGeo, mat.clone(), active.length)

    const dummy = new THREE.Object3D()
    const color = new THREE.Color()

    for (let i = 0; i < active.length; i++) {
      const bs = active[i]
      const [x, y, z] = bsToScenePos(bs, origin)

      // Pole from ground to height
      dummy.position.set(x, y / 2, z)
      dummy.scale.set(1, Math.max(y, 0.5), 1)
      dummy.rotation.set(0, 0, 0)
      dummy.updateMatrix()
      poles.setMatrixAt(i, dummy.matrix)

      // Sphere at top
      dummy.position.set(x, y, z)
      dummy.scale.set(1, 1, 1)
      dummy.updateMatrix()
      spheres.setMatrixAt(i, dummy.matrix)

      // Color by operator
      color.set(OPERATOR_COLORS[bs.operator] ?? DEFAULT_COLOR)
      poles.setColorAt(i, color)
      spheres.setColorAt(i, color)
    }

    poles.instanceMatrix.needsUpdate = true
    spheres.instanceMatrix.needsUpdate = true
    if (poles.instanceColor) poles.instanceColor.needsUpdate = true
    if (spheres.instanceColor) spheres.instanceColor.needsUpdate = true

    group.add(poles)
    group.add(spheres)

    return () => {
      poleGeo.dispose()
      sphereGeo.dispose()
      mat.dispose()
    }
  }, [basestations, origin, enabledOperators, enabledTechnologies])

  if (!origin || basestations.length === 0) return null

  return <group ref={groupRef} />
}
