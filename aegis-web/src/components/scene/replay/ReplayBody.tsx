import { useMemo, useEffect } from 'react'
import * as THREE from 'three'
import { jetColor } from '@/lib/colormap'
import { toScene } from '@/api/coordinates'
import type { ReplayBodyMesh } from '@/api/replayTypes'

/**
 * Body mesh colored per-vertex by the current frame's Sab. Geometry is built
 * once from the artifact; colors are re-written whenever the frame's sab
 * array changes. Coloring matches the live viewer (jet colormap, normalised
 * to the per-frame max).
 */
export default function ReplayBody({ body, sab }: { body: ReplayBodyMesh; sab?: number[] }) {
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
      const inv = max > 0 ? 1 / max : 0
      const n = Math.min(sab.length, buf.length / 3)
      for (let i = 0; i < n; i++) {
        const [r, g, b] = jetColor(sab[i] * inv)
        buf[i * 3] = r
        buf[i * 3 + 1] = g
        buf[i * 3 + 2] = b
      }
    }
    colorAttr.needsUpdate = true
  }, [geometry, sab])

  return (
    <mesh geometry={geometry} castShadow>
      <meshStandardMaterial vertexColors roughness={0.7} metalness={0.1} />
    </mesh>
  )
}
