import { useMemo } from 'react'
import * as THREE from 'three'
import { toScene } from '@/api/coordinates'
import type { ReplayArraySpec, Vec3 } from '@/api/replayTypes'

/** A server-space direction (no translation) expressed in scene coords. */
function dirToScene(v: Vec3): THREE.Vector3 {
  const s = toScene(v)
  return new THREE.Vector3(s[0], s[1], s[2]).normalize()
}

/**
 * Base-station URA marker: a flat panel whose broad face points along the
 * array boresight (toward the served UEs), with an n_h x n_v grid of element
 * dots on that face. The panel size is exaggerated for visibility; element
 * spacing at 28 GHz is ~5 mm, far too small to see at room scale.
 */
export default function ReplayArray({ array }: { array: ReplayArraySpec }) {
  const p = toScene(array.position)
  const nH = array.n_h ?? 8
  const nV = array.n_v ?? 8
  const w = array.panel_w ?? 0.9
  const h = array.panel_h ?? 0.9

  // Orient: local +z (panel normal) -> boresight; keep one in-plane axis near vertical.
  const quat = useMemo(() => {
    const n = array.normal ? dirToScene(array.normal) : new THREE.Vector3(0, 0, 1)
    const worldUp = new THREE.Vector3(0, 1, 0)
    let right = new THREE.Vector3().crossVectors(worldUp, n)
    if (right.lengthSq() < 1e-6) right = new THREE.Vector3(1, 0, 0)
    right.normalize()
    const up = new THREE.Vector3().crossVectors(n, right).normalize()
    const m = new THREE.Matrix4().makeBasis(right, up, n)
    return new THREE.Quaternion().setFromRotationMatrix(m)
  }, [array.normal])

  const dots = useMemo(() => {
    const out: [number, number, number][] = []
    for (let j = 0; j < nV; j++) {
      const y = nV > 1 ? (j / (nV - 1) - 0.5) * h * 0.86 : 0
      for (let i = 0; i < nH; i++) {
        const x = nH > 1 ? (i / (nH - 1) - 0.5) * w * 0.86 : 0
        out.push([x, y, 0.03])
      }
    }
    return out
  }, [nH, nV, w, h])

  return (
    <group position={p} quaternion={quat}>
      <mesh>
        <boxGeometry args={[w, h, 0.05]} />
        <meshStandardMaterial color="#3b82f6" emissive="#1e3a8a" emissiveIntensity={0.35} />
      </mesh>
      {dots.map((d, i) => (
        <mesh key={i} position={d}>
          <sphereGeometry args={[0.025, 8, 8]} />
          <meshBasicMaterial color="#bfdbfe" />
        </mesh>
      ))}
    </group>
  )
}
