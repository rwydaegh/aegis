import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { useTerrainStore } from '@/stores/terrain'

export function EnvironmentTerrain() {
  const enabled = useTerrainStore((s) => s.enabled)
  const meshData = useTerrainStore((s) => s.meshData)

  const geometry = useMemo(() => {
    if (!meshData) return null

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(meshData.positions, 3))
    geo.setIndex(new THREE.BufferAttribute(meshData.indices, 1))
    geo.computeVertexNormals()

    return geo
  }, [meshData])

  useEffect(() => {
    return () => { geometry?.dispose() }
  }, [geometry])

  if (!enabled || !geometry) return null

  return (
    <mesh geometry={geometry} receiveShadow>
      <meshStandardMaterial
        color="#5a7a3a"
        roughness={0.9}
        metalness={0.0}
        side={THREE.DoubleSide}
      />
    </mesh>
  )
}
