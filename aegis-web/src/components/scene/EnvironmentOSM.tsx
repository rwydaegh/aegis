import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { useEnvironmentStore } from '@/stores/environment'
import { useClickToPlace } from '@/hooks/useClickToPlace'

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
  10: [0.65, 0.35, 0.25], // roof tile
  11: [0.45, 0.35, 0.25], // soil
  12: [0.15, 0.45, 0.1], // vegetation dense
  13: [0.9, 0.87, 0.82], // plaster
}

export function EnvironmentOSM() {
  const meshData = useEnvironmentStore((s) => s.osmMeshData)
  const clickHandlers = useClickToPlace()

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

  useEffect(() => {
    return () => { geometry?.dispose() }
  }, [geometry])

  if (!geometry) return null

  return (
    <mesh geometry={geometry} receiveShadow castShadow {...clickHandlers}>
      <meshStandardMaterial vertexColors side={THREE.DoubleSide} />
    </mesh>
  )
}
