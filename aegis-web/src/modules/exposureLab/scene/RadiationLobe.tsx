import { useEffect, useMemo, useState } from 'react'
import * as Sentry from '@sentry/react'
import * as THREE from 'three'
import { useLabStore } from '../store'
import { getPatternLobe, type PatternLobe } from '../api'

// Visual scale: directivity (linear) is multiplied by this so a directivity of
// ~1.6 produces a lobe ~0.25 m long, sitting nicely next to the ~0.15 m phone.
const LOBE_SCALE = 0.15

// Build a closed parametric surface from the (theta, phi) directivity grid.
// r is [n_phi][n_theta]; each grid point maps to a radius in the antenna local
// frame using the pattern convention (theta from +z, phi from +x):
//   p = r * [sin(theta)cos(phi), sin(theta)sin(phi), cos(theta)]
function buildLobeGeometry(lobe: PatternLobe): THREE.BufferGeometry {
  const { theta, phi, r } = lobe
  const nTheta = theta.length
  const nPhi = phi.length

  const positions = new Float32Array(nPhi * nTheta * 3)
  for (let ip = 0; ip < nPhi; ip++) {
    const cphi = Math.cos(phi[ip])
    const sphi = Math.sin(phi[ip])
    for (let it = 0; it < nTheta; it++) {
      const radius = (r[ip]?.[it] ?? 0) * LOBE_SCALE
      const stheta = Math.sin(theta[it])
      const ctheta = Math.cos(theta[it])
      const base = (ip * nTheta + it) * 3
      positions[base + 0] = radius * stheta * cphi
      positions[base + 1] = radius * stheta * sphi
      positions[base + 2] = radius * ctheta
    }
  }

  // Two triangles per quad, wrapping phi so the lobe closes into a full surface.
  const indices: number[] = []
  for (let ip = 0; ip < nPhi; ip++) {
    const ipNext = (ip + 1) % nPhi
    for (let it = 0; it < nTheta - 1; it++) {
      const a = ip * nTheta + it
      const b = ipNext * nTheta + it
      const c = ipNext * nTheta + (it + 1)
      const d = ip * nTheta + (it + 1)
      indices.push(a, b, d)
      indices.push(b, c, d)
    }
  }

  const geom = new THREE.BufferGeometry()
  geom.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geom.setIndex(indices)
  geom.computeVertexNormals()
  return geom
}

// Antenna radiation lobe in the antenna LOCAL frame. Mount inside a group that
// carries the phone position and Z-Y-X orientation so the lobe rigidly follows
// the phone.
export default function RadiationLobe() {
  const patternId = useLabStore((s) => s.patternId)
  const freqMhz = useLabStore((s) => s.freqMhz)
  const [lobe, setLobe] = useState<PatternLobe | null>(null)

  useEffect(() => {
    let cancelled = false
    getPatternLobe(patternId, freqMhz)
      .then((data) => {
        if (!cancelled) setLobe(data)
      })
      .catch((err) => {
        if (!cancelled) Sentry.captureException(err)
      })
    return () => {
      cancelled = true
    }
  }, [patternId, freqMhz])

  const geometry = useMemo(() => (lobe ? buildLobeGeometry(lobe) : null), [lobe])

  // Dispose the geometry whenever it is replaced or the component unmounts.
  useEffect(() => {
    return () => {
      geometry?.dispose()
    }
  }, [geometry])

  if (!geometry) return null

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color="#4cc9f0"
        emissive="#1b6fa8"
        emissiveIntensity={0.6}
        transparent
        opacity={0.35}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  )
}
