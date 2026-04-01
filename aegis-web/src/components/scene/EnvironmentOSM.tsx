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
    const nVerts = meshData.positions.length / 3

    // --- Expand indexed geometry to non-indexed for per-face vertex colors ---
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

    // --- Compute smooth vertex normals ---
    // Accumulate face normals onto the original shared vertices, then map
    // back to the expanded non-indexed layout. This eliminates visible
    // triangle edges on coplanar faces (flat roofs) that computeVertexNormals()
    // on non-indexed geometry would create.
    const smoothNormals = new Float32Array(nTris * 9)
    const vertexNormals = new Float32Array(nVerts * 3) // accumulator per original vertex

    // Pass 1: compute face normals and accumulate onto shared vertices
    for (let t = 0; t < nTris; t++) {
      const i0 = meshData.indices[t * 3]
      const i1 = meshData.indices[t * 3 + 1]
      const i2 = meshData.indices[t * 3 + 2]

      // Triangle edges
      const ax = meshData.positions[i1 * 3] - meshData.positions[i0 * 3]
      const ay = meshData.positions[i1 * 3 + 1] - meshData.positions[i0 * 3 + 1]
      const az = meshData.positions[i1 * 3 + 2] - meshData.positions[i0 * 3 + 2]
      const bx = meshData.positions[i2 * 3] - meshData.positions[i0 * 3]
      const by = meshData.positions[i2 * 3 + 1] - meshData.positions[i0 * 3 + 1]
      const bz = meshData.positions[i2 * 3 + 2] - meshData.positions[i0 * 3 + 2]

      // Cross product (area-weighted face normal)
      const nx = ay * bz - az * by
      const ny = az * bx - ax * bz
      const nz = ax * by - ay * bx

      // Accumulate onto each vertex of this face
      for (const idx of [i0, i1, i2]) {
        vertexNormals[idx * 3] += nx
        vertexNormals[idx * 3 + 1] += ny
        vertexNormals[idx * 3 + 2] += nz
      }
    }

    // Normalize accumulated vertex normals
    for (let i = 0; i < nVerts; i++) {
      const x = vertexNormals[i * 3]
      const y = vertexNormals[i * 3 + 1]
      const z = vertexNormals[i * 3 + 2]
      const len = Math.sqrt(x * x + y * y + z * z) || 1
      vertexNormals[i * 3] = x / len
      vertexNormals[i * 3 + 1] = y / len
      vertexNormals[i * 3 + 2] = z / len
    }

    // Pass 2: expand smooth normals to non-indexed layout
    for (let t = 0; t < nTris; t++) {
      for (let v = 0; v < 3; v++) {
        const srcIdx = meshData.indices[t * 3 + v]
        const dstIdx = t * 9 + v * 3
        smoothNormals[dstIdx] = vertexNormals[srcIdx * 3]
        smoothNormals[dstIdx + 1] = vertexNormals[srcIdx * 3 + 1]
        smoothNormals[dstIdx + 2] = vertexNormals[srcIdx * 3 + 2]
      }
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geo.setAttribute('normal', new THREE.BufferAttribute(smoothNormals, 3))

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
