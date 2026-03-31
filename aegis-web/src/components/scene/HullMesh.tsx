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

  const geometry = useMemo(() => {
    if (!data) return null
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(data.vertices, 3))
    geo.setIndex(new THREE.BufferAttribute(data.indices, 1))

    if (data.faceColors) {
      const nonIndexed = geo.toNonIndexed()
      const faceCount = data.faceColors.length / 3
      const vertexColors = new Float32Array(faceCount * 3 * 3)
      for (let f = 0; f < faceCount; f++) {
        const r = data.faceColors[f * 3]
        const g = data.faceColors[f * 3 + 1]
        const b = data.faceColors[f * 3 + 2]
        for (let v = 0; v < 3; v++) {
          vertexColors[(f * 3 + v) * 3] = r
          vertexColors[(f * 3 + v) * 3 + 1] = g
          vertexColors[(f * 3 + v) * 3 + 2] = b
        }
      }
      nonIndexed.setAttribute('color', new THREE.Float32BufferAttribute(vertexColors, 3))
      nonIndexed.computeVertexNormals()
      return nonIndexed
    }

    geo.computeVertexNormals()
    return geo
  }, [data])

  if (envMode !== 'hull' || !geometry) return null

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        vertexColors={!!data?.faceColors}
        color={data?.faceColors ? undefined : '#888888'}
        wireframe={wireframe}
        side={THREE.DoubleSide}
      />
    </mesh>
  )
}
