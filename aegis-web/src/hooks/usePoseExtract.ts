// aegis-web/src/hooks/usePoseExtract.ts
import * as THREE from 'three'
import { toServer } from '@/api/coordinates'

export interface PosedMeshData {
  /** Triangle soup positions, Z-up (server coords). N_triangles * 9 floats. */
  positions: Float32Array
  /** Per-face normals repeated 3x per triangle, Z-up. N_triangles * 9 floats. */
  normals: Float32Array
  /** Number of triangles. */
  nTriangles: number
}

/**
 * Extract deformed triangle-soup mesh from a SkinnedMesh.
 * Applies bone transforms to rest-pose vertices, de-indexes into triangle soup,
 * computes face normals from cross products, and converts Y-up to Z-up.
 */
export function extractPosedMesh(skinnedMesh: THREE.SkinnedMesh): PosedMeshData {
  const geo = skinnedMesh.geometry
  const posAttr = geo.getAttribute('position')
  const index = geo.getIndex()

  if (!index) {
    throw new Error('SkinnedMesh must have an index buffer')
  }

  const uniqueCount = posAttr.count
  const triCount = index.count / 3

  // Step 1: Bone-transform all unique vertices (Y-up, local space)
  const deformed = new Float32Array(uniqueCount * 3)
  const target = new THREE.Vector3()
  for (let i = 0; i < uniqueCount; i++) {
    skinnedMesh.boneTransform(i, target)
    deformed[i * 3] = target.x
    deformed[i * 3 + 1] = target.y
    deformed[i * 3 + 2] = target.z
  }

  // Step 2: De-index into triangle soup + compute face normals
  const positions = new Float32Array(triCount * 9)
  const normals = new Float32Array(triCount * 9)
  const indices = index.array

  const edge1 = new THREE.Vector3()
  const edge2 = new THREE.Vector3()
  const faceNormal = new THREE.Vector3()

  for (let f = 0; f < triCount; f++) {
    const i0 = indices[f * 3]
    const i1 = indices[f * 3 + 1]
    const i2 = indices[f * 3 + 2]

    // Convert Y-up -> Z-up (server coords) via toServer
    const [sx0, sy0, sz0] = toServer([deformed[i0 * 3], deformed[i0 * 3 + 1], deformed[i0 * 3 + 2]])
    const [sx1, sy1, sz1] = toServer([deformed[i1 * 3], deformed[i1 * 3 + 1], deformed[i1 * 3 + 2]])
    const [sx2, sy2, sz2] = toServer([deformed[i2 * 3], deformed[i2 * 3 + 1], deformed[i2 * 3 + 2]])

    // Triangle soup positions (Z-up)
    positions[f * 9 + 0] = sx0; positions[f * 9 + 1] = sy0; positions[f * 9 + 2] = sz0
    positions[f * 9 + 3] = sx1; positions[f * 9 + 4] = sy1; positions[f * 9 + 5] = sz1
    positions[f * 9 + 6] = sx2; positions[f * 9 + 7] = sy2; positions[f * 9 + 8] = sz2

    // Face normal from cross product (in Z-up space)
    edge1.set(sx1 - sx0, sy1 - sy0, sz1 - sz0)
    edge2.set(sx2 - sx0, sy2 - sy0, sz2 - sz0)
    faceNormal.crossVectors(edge1, edge2).normalize()

    const nx = faceNormal.x, ny = faceNormal.y, nz = faceNormal.z
    normals[f * 9 + 0] = nx; normals[f * 9 + 1] = ny; normals[f * 9 + 2] = nz
    normals[f * 9 + 3] = nx; normals[f * 9 + 4] = ny; normals[f * 9 + 5] = nz
    normals[f * 9 + 6] = nx; normals[f * 9 + 7] = ny; normals[f * 9 + 8] = nz
  }

  return { positions, normals, nTriangles: triCount }
}

/**
 * Pack PosedMeshData into the binary format expected by the backend.
 * Layout: [positions (N*3 float32) | normals (N*3 float32)]
 */
export function packMeshBinary(data: PosedMeshData): ArrayBuffer {
  const buf = new ArrayBuffer((data.positions.length + data.normals.length) * 4)
  const view = new Float32Array(buf)
  view.set(data.positions, 0)
  view.set(data.normals, data.positions.length)
  return buf
}
