import { useMemo, useEffect } from 'react'
import * as THREE from 'three'
import { jetColor, gainTFromLinear } from '@/lib/colormap'
import { toScene } from '@/api/coordinates'
import type { ReplayBodyMesh, Vec3 } from '@/api/replayTypes'

// dB dynamic range for coloring. Absorbed power density is sharply peaked, so a
// linear map leaves all but the hotspot black; a log/dB map (as in the live
// viewer's dB legend) renders the whole body's relative pattern.
const DYNAMIC_RANGE_DB = 30

/**
 * Body mesh colored per-vertex by the current frame's Sab. Geometry is built
 * once from the canonical artifact mesh (feet on floor at the origin); the
 * per-frame `bodyPos` translates it to the served UE. Colors are re-written
 * whenever the frame's sab array changes. Coloring matches the live viewer
 * (jet colormap, normalised to the per-frame max). The material is
 * double-sided so triangles are never culled by inconsistent winding.
 */
export default function ReplayBody({ body, sab, bodyPos }: { body: ReplayBodyMesh; sab?: number[]; bodyPos?: Vec3 }) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry()
    const n = body.vertices.length
    const pos = new Float32Array(n * 3)
    for (let i = 0; i < n; i++) {
      const s = toScene(body.vertices[i])
      pos[i * 3] = s[0]
      pos[i * 3 + 1] = s[1]
      pos[i * 3 + 2] = s[2]
    }
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    const idx = new Uint32Array(body.faces.length * 3)
    for (let f = 0; f < body.faces.length; f++) {
      idx[f * 3] = body.faces[f][0]
      idx[f * 3 + 1] = body.faces[f][1]
      idx[f * 3 + 2] = body.faces[f][2]
    }
    g.setIndex(new THREE.BufferAttribute(idx, 1))
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(n * 3), 3))
    g.computeVertexNormals()
    return g
  }, [body])

  useEffect(() => {
    const colorAttr = geometry.getAttribute('color') as THREE.BufferAttribute
    const buf = colorAttr.array as Float32Array
    if (!sab || sab.length === 0) {
      buf.fill(0.5)
    } else {
      let max = 0
      for (let i = 0; i < sab.length; i++) if (sab[i] > max) max = sab[i]
      const nVerts = buf.length / 3
      // Sab may be per-vertex (length == nVerts) or per-face (length == nVerts/3,
      // i.e. one value per soup triangle). Expand per-face to its three verts.
      const perFace = sab.length * 3 === nVerts
      for (let v = 0; v < nVerts; v++) {
        const s = perFace ? sab[(v / 3) | 0] : sab[v]
        const [r, g, b] = jetColor(gainTFromLinear(s ?? 0, max, DYNAMIC_RANGE_DB))
        buf[v * 3] = r
        buf[v * 3 + 1] = g
        buf[v * 3 + 2] = b
      }
    }
    colorAttr.needsUpdate = true
  }, [geometry, sab])

  const pos = bodyPos ? toScene(bodyPos) : ([0, 0, 0] as Vec3)
  return (
    <mesh geometry={geometry} position={pos} castShadow>
      <meshStandardMaterial vertexColors roughness={0.7} metalness={0.1} side={THREE.DoubleSide} />
    </mesh>
  )
}
