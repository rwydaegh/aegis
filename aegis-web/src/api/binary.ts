import { toScene } from './coordinates'

export function parseBodyBinary(buffer: ArrayBuffer, nVertices: number) {
  const floats = new Float32Array(buffer)
  const rawPositions = floats.subarray(0, nVertices * 3)
  const rawNormals = floats.subarray(nVertices * 3, nVertices * 6)

  const positions = new Float32Array(nVertices * 3)
  const normals = new Float32Array(nVertices * 3)

  for (let i = 0; i < nVertices; i++) {
    const [x, y, z] = toScene([rawPositions[i * 3], rawPositions[i * 3 + 1], rawPositions[i * 3 + 2]])
    positions[i * 3] = x
    positions[i * 3 + 1] = y
    positions[i * 3 + 2] = z

    const [nx, ny, nz] = toScene([rawNormals[i * 3], rawNormals[i * 3 + 1], rawNormals[i * 3 + 2]])
    normals[i * 3] = nx
    normals[i * 3 + 1] = ny
    normals[i * 3 + 2] = nz
  }

  return { positions, normals }
}

export function parseVoxelBinary(buffer: ArrayBuffer, nVoxels: number) {
  const posBytes = nVoxels * 3 * 4
  const sizeBytes = nVoxels * 4
  const colorBytes = nVoxels * 3

  const rawPositions = new Float32Array(buffer, 0, nVoxels * 3)
  const sizes = new Float32Array(buffer, posBytes, nVoxels)
  const colors = new Uint8Array(buffer, posBytes + sizeBytes, colorBytes)
  const materialIndices = new Uint8Array(buffer, posBytes + sizeBytes + colorBytes)

  const positions = new Float32Array(nVoxels * 3)
  for (let i = 0; i < nVoxels; i++) {
    const [x, y, z] = toScene([rawPositions[i * 3], rawPositions[i * 3 + 1], rawPositions[i * 3 + 2]])
    positions[i * 3] = x
    positions[i * 3 + 1] = y
    positions[i * 3 + 2] = z
  }

  return { positions, sizes: new Float32Array(sizes), colors: new Uint8Array(colors), materialIndices: new Uint8Array(materialIndices) }
}

export function parseSceneBinary(buffer: ArrayBuffer, nVertices: number, nTriangles: number, hasFaceColors: boolean) {
  const vertBytes = nVertices * 3 * 4
  const idxBytes = nTriangles * 3 * 4

  const rawVertices = new Float32Array(buffer, 0, nVertices * 3)
  const indices = new Int32Array(buffer, vertBytes, nTriangles * 3)

  const vertices = new Float32Array(nVertices * 3)
  for (let i = 0; i < nVertices; i++) {
    const [x, y, z] = toScene([rawVertices[i * 3], rawVertices[i * 3 + 1], rawVertices[i * 3 + 2]])
    vertices[i * 3] = x
    vertices[i * 3 + 1] = y
    vertices[i * 3 + 2] = z
  }

  let faceColors: Float32Array | null = null
  if (hasFaceColors) {
    faceColors = new Float32Array(buffer, vertBytes + idxBytes, nTriangles * 3)
  }

  return { vertices, indices: new Int32Array(indices), faceColors }
}

export function parseSabBinary(buffer: ArrayBuffer): Float32Array {
  return new Float32Array(buffer)
}
