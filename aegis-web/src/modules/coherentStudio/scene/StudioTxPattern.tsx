import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { jetColor, gainTFromLinear } from '@/lib/colormap'
import { toScene } from '@/api/coordinates'
import type { PrecoderResult } from '../api'

// The realised transmit radiation pattern of the base-station array under the
// synthesised precoder x, drawn as a lobe at the panel. Vertex radius tracks
// |AF(d)|^2 = |sum_j x_j exp(+i k0 r_j . d)|^2, so it is literally the beam the
// selected precoder forms: MRT points at the focus, ECBF tapers to dodge the
// body, worstcase / unfocused look different again. This replaces the
// uniform-excitation stand-in whenever the backend returns a precoder.
//
// The array is a uniform planar lattice, so the element phase factors separate
// along the two panel axes (a product of per-axis sums), which keeps the
// per-vertex cost ~n_h + n_v trig calls instead of n_h*n_v.

interface StudioTxPatternProps {
  precoder: PrecoderResult
  /** Panel centre in scene (Y-up) coordinates. */
  position: [number, number, number]
  /** Cosmetic magnification of the lobe (the panel is ~14 m from the body). */
  scale?: number
  screenshot?: boolean
}

const C0 = 299792458
const RADIUS = 0.6
const LOBE_GAMMA = 0.42
const DYN_DB = 36
const DETAIL = 30

function toSceneDir(v: number[]): THREE.Vector3 {
  // toScene is a pure rotation, so it carries a direction without translation.
  const [x, y, z] = toScene([v[0], v[1], v[2]])
  return new THREE.Vector3(x, y, z)
}

function buildTxGeometry(p: PrecoderResult): THREE.BufferGeometry {
  const nH = p.n_h ?? 0
  const nV = p.n_v ?? 0
  const re = p.real ?? []
  const im = p.imag ?? []
  const axisH = toSceneDir(p.axis_h ?? [0, 1, 0])
  const axisV = toSceneDir(p.axis_v ?? [0, 0, 1])
  const k0 = (2 * Math.PI * (p.freq_hz ?? C0)) / C0
  const step = k0 * (p.spacing_m ?? 0) // phase per unit index along an axis, times the axis projection
  const midH = (nH - 1) / 2
  const midV = (nV - 1) / 2

  const base = new THREE.IcosahedronGeometry(1, DETAIL)
  const posAttr = base.attributes.position as THREE.BufferAttribute
  const nVerts = posAttr.count

  // Scratch per-axis phasor tables, reused across vertices.
  const ehRe = new Float64Array(nH)
  const ehIm = new Float64Array(nH)
  const evRe = new Float64Array(nV)
  const evIm = new Float64Array(nV)

  const gains = new Float32Array(nVerts)
  const dirs: THREE.Vector3[] = []
  let gMax = 0

  for (let i = 0; i < nVerts; i++) {
    const dir = new THREE.Vector3(posAttr.getX(i), posAttr.getY(i), posAttr.getZ(i)).normalize()
    dirs.push(dir)
    const uH = axisH.dot(dir)
    const uV = axisV.dot(dir)
    for (let b = 0; b < nH; b++) {
      const ph = step * (b - midH) * uH
      ehRe[b] = Math.cos(ph)
      ehIm[b] = Math.sin(ph)
    }
    for (let a = 0; a < nV; a++) {
      const ph = step * (a - midV) * uV
      evRe[a] = Math.cos(ph)
      evIm[a] = Math.sin(ph)
    }
    // AF = sum_a Ev[a] * (sum_b x[a,b] Eh[b]); element order k = a*nH + b.
    let afRe = 0
    let afIm = 0
    for (let a = 0; a < nV; a++) {
      let rowRe = 0
      let rowIm = 0
      const off = a * nH
      for (let b = 0; b < nH; b++) {
        const xr = re[off + b]
        const xi = im[off + b]
        // x * Eh
        rowRe += xr * ehRe[b] - xi * ehIm[b]
        rowIm += xr * ehIm[b] + xi * ehRe[b]
      }
      // rowSum * Ev[a]
      afRe += rowRe * evRe[a] - rowIm * evIm[a]
      afIm += rowRe * evIm[a] + rowIm * evRe[a]
    }
    const g = afRe * afRe + afIm * afIm
    gains[i] = g
    if (g > gMax) gMax = g
  }
  if (gMax < 1e-12) gMax = 1

  const colors = new Float32Array(nVerts * 3)
  for (let i = 0; i < nVerts; i++) {
    const gn = gains[i] / gMax
    const rr = RADIUS * Math.max(gn, 1e-9) ** LOBE_GAMMA
    const d = dirs[i]
    posAttr.setXYZ(i, d.x * rr, d.y * rr, d.z * rr)
    const [cr, cg, cb] = jetColor(gainTFromLinear(gains[i], gMax, DYN_DB))
    colors[i * 3] = cr
    colors[i * 3 + 1] = cg
    colors[i * 3 + 2] = cb
  }
  posAttr.needsUpdate = true
  base.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  base.computeVertexNormals()
  return base
}

export default function StudioTxPattern({ precoder, position, scale = 1, screenshot }: StudioTxPatternProps) {
  const geo = useMemo(() => buildTxGeometry(precoder), [precoder])
  useEffect(() => () => geo.dispose(), [geo])

  return (
    <group position={position}>
      <mesh geometry={geo} scale={scale}>
        <meshStandardMaterial
          vertexColors
          transparent
          opacity={0.85}
          metalness={0.12}
          roughness={0.5}
          side={THREE.DoubleSide}
        />
      </mesh>
      {!screenshot && (
        <mesh>
          <sphereGeometry args={[0.04, 16, 16]} />
          <meshStandardMaterial color="#aa2222" emissive="#441010" emissiveIntensity={0.6} />
        </mesh>
      )}
    </group>
  )
}
