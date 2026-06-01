import { useMemo } from 'react'
import * as THREE from 'three'
import { toScene } from '@/api/coordinates'
import type { ReplaySceneMesh } from '@/api/replayTypes'

/**
 * The real city geometry the ray tracer uses, rendered as a flat-shaded mesh.
 * This is `CityCache.mesh` (OSM footprints extruded to per-building height with
 * parsed roof shapes), not the axis-aligned bounding boxes the old exporter
 * sent, so the viewer shows the same surfaces the rays bounce off. Built once
 * from the artifact; vertices are converted server (Z-up) -> scene (Y-up) and
 * normals computed for lighting. Double-sided so back-facing walls still shade.
 */
export default function ReplayCityMesh({ mesh }: { mesh: ReplaySceneMesh }) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry()
    const n = mesh.vertices.length
    const pos = new Float32Array(n * 3)
    for (let i = 0; i < n; i++) {
      const s = toScene(mesh.vertices[i])
      pos[i * 3] = s[0]
      pos[i * 3 + 1] = s[1]
      pos[i * 3 + 2] = s[2]
    }
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    const idx = new Uint32Array(mesh.triangles.length * 3)
    for (let f = 0; f < mesh.triangles.length; f++) {
      idx[f * 3] = mesh.triangles[f][0]
      idx[f * 3 + 1] = mesh.triangles[f][1]
      idx[f * 3 + 2] = mesh.triangles[f][2]
    }
    g.setIndex(new THREE.BufferAttribute(idx, 1))
    g.computeVertexNormals()
    return g
  }, [mesh])

  return (
    <mesh geometry={geometry} castShadow receiveShadow>
      <meshStandardMaterial color="#6b7280" roughness={0.95} metalness={0.0} side={THREE.DoubleSide} />
    </mesh>
  )
}
