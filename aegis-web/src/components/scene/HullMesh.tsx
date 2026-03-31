import { useEffect, useMemo, useState } from 'react'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { fetchHullMesh } from '@/api/client'

interface HullData {
  vertices: Float32Array
  indices: Int32Array
  faceColors: Float32Array | null
}

export default function HullMesh() {
  const envMode = useSceneStore(s => s.envDisplayMode)
  const wireframe = useUIStore(s => s.wireframe)
  const [data, setData] = useState<HullData | null>(null)

  useEffect(() => {
    if (envMode !== 'hull') return
    let cancelled = false
    fetchHullMesh()
      .then(d => { if (!cancelled) setData(d) })
      .catch(err => console.error('Hull mesh fetch failed:', err))
    return () => { cancelled = true }
  }, [envMode])

  const { geometry, hasVertexColors } = useMemo(() => {
    if (!data) return { geometry: null, hasVertexColors: false }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(data.vertices, 3))
    geo.setIndex(new THREE.BufferAttribute(new Uint32Array(data.indices), 1))

    if (data.faceColors) {
      const nonIndexed = geo.toNonIndexed()
      nonIndexed.computeVertexNormals()
      const nFaces = data.faceColors.length / 3
      const colorAttr = new Float32Array(nFaces * 9)
      for (let f = 0; f < nFaces; f++) {
        const r = data.faceColors[f * 3]
        const g = data.faceColors[f * 3 + 1]
        const b = data.faceColors[f * 3 + 2]
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
  }, [data])

  if (envMode !== 'hull' || !geometry) return null

  return (
    <mesh geometry={geometry}>
      {hasVertexColors ? (
        <meshStandardMaterial vertexColors wireframe={wireframe} roughness={0.7} side={THREE.DoubleSide} />
      ) : (
        <meshStandardMaterial color="#888" wireframe={wireframe} roughness={0.7} side={THREE.DoubleSide} />
      )}
    </mesh>
  )
}
