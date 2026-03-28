import { useMemo } from 'react'
import * as THREE from 'three'
import { useEnvironmentStore } from '@/stores/environment'

const MATERIAL_COLORS: Record<number, [number, number, number]> = {
  0: [0.7, 0.7, 0.7], // concrete
  1: [0.7, 0.3, 0.2], // brick
  2: [0.6, 0.8, 0.9], // glass
  3: [0.8, 0.8, 0.85], // metal
  4: [0.3, 0.3, 0.3], // asphalt
  5: [0.3, 0.6, 0.2], // vegetation
  6: [0.2, 0.4, 0.8], // water
  7: [0.6, 0.4, 0.2], // wood
  8: [0.5, 0.45, 0.35], // ground
  9: [0.5, 0.5, 0.5], // unknown
}

export function EnvironmentOSM() {
  const meshData = useEnvironmentStore((s) => s.osmMeshData)

  const geometry = useMemo(() => {
    if (!meshData) return null

    const nTris = meshData.indices.length / 3
    const positions = new Float32Array(nTris * 9)
    const colors = new Float32Array(nTris * 9)

    for (let t = 0; t < nTris; t++) {
      const mat = meshData.materials[t]
      const color = MATERIAL_COLORS[mat] || MATERIAL_COLORS[9]
      for (let v = 0; v < 3; v++) {
        const srcIdx = meshData.indices[t * 3 + v]
        const dstIdx = t * 9 + v * 3
        positions[dstIdx] = meshData.positions[srcIdx * 3]
        positions[dstIdx + 1] = meshData.positions[srcIdx * 3 + 1]
        positions[dstIdx + 2] = meshData.positions[srcIdx * 3 + 2]
        colors[dstIdx] = color[0]
        colors[dstIdx + 1] = color[1]
        colors[dstIdx + 2] = color[2]
      }
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geo.computeVertexNormals()

    return geo
  }, [meshData])

  if (!geometry) return null

  return (
    <mesh geometry={geometry} receiveShadow castShadow>
      <meshStandardMaterial vertexColors side={THREE.DoubleSide} />
    </mesh>
  )
}
