import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'

export default function SceneGeometry() {
  const sceneGeometry = useSceneStore(s => s.sceneGeometry)
  const wireframe = useUIStore(s => s.wireframe)

  if (!sceneGeometry) return null

  const { vertices, indices, faceColors } = sceneGeometry

  // Build geometry
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3))
  geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(indices), 1))

  if (faceColors) {
    // Convert indexed to non-indexed for per-face colors
    const nonIndexed = geometry.toNonIndexed()
    const nFaces = faceColors.length / 3
    const colorAttr = new Float32Array(nFaces * 9) // 3 verts * 3 RGB per face
    for (let f = 0; f < nFaces; f++) {
      const r = faceColors[f * 3]
      const g = faceColors[f * 3 + 1]
      const b = faceColors[f * 3 + 2]
      for (let v = 0; v < 3; v++) {
        colorAttr[(f * 3 + v) * 3] = r
        colorAttr[(f * 3 + v) * 3 + 1] = g
        colorAttr[(f * 3 + v) * 3 + 2] = b
      }
    }
    nonIndexed.setAttribute('color', new THREE.BufferAttribute(colorAttr, 3))
    return (
      <mesh geometry={nonIndexed}>
        <meshStandardMaterial vertexColors wireframe={wireframe} roughness={0.7} />
      </mesh>
    )
  }

  geometry.computeVertexNormals()

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color="#888" wireframe={wireframe} roughness={0.7} />
    </mesh>
  )
}
