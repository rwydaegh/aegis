import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useClickToPlace } from '@/hooks/useClickToPlace'

export default function SceneGeometry() {
  const sceneGeometry = useSceneStore(s => s.sceneGeometry)
  const visible = useSceneStore(s => s.sceneGeometryVisible)
  const wireframe = useUIStore(s => s.wireframe)
  const clickHandlers = useClickToPlace()

  const { geometry, hasVertexColors } = useMemo(() => {
    if (!sceneGeometry) return { geometry: null, hasVertexColors: false }

    const { vertices, indices, faceColors } = sceneGeometry

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(vertices, 3))
    geo.setIndex(new THREE.BufferAttribute(new Uint32Array(indices), 1))

    if (faceColors) {
      const nonIndexed = geo.toNonIndexed()
      nonIndexed.computeVertexNormals()
      const nFaces = faceColors.length / 3
      const colorAttr = new Float32Array(nFaces * 9)
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
      return { geometry: nonIndexed, hasVertexColors: true }
    }

    geo.computeVertexNormals()
    return { geometry: geo, hasVertexColors: false }
  }, [sceneGeometry])

  useEffect(() => () => { geometry?.dispose() }, [geometry])

  if (!geometry || !visible) return null

  return (
    <mesh geometry={geometry} {...clickHandlers}>
      {hasVertexColors ? (
        <meshStandardMaterial vertexColors wireframe={wireframe} roughness={0.7} side={THREE.DoubleSide} />
      ) : (
        <meshStandardMaterial color="#888" wireframe={wireframe} roughness={0.7} side={THREE.DoubleSide} />
      )}
    </mesh>
  )
}
