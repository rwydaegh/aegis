import { useMemo, useEffect } from 'react'
import * as THREE from 'three'
import type { ArrayConfig } from '@/api/types'
import { jetColor, gainTFromLinear } from '@/lib/colormap'
import PanelAntenna from './PanelAntenna'

interface AntennaArrayProps {
  config: ArrayConfig
  freqHz: number
  showPattern?: boolean
  weights?: { real: number[][]; imag: number[][] } | null
  selected?: boolean
}

const ARROW_COLOR = new THREE.Color(1, 0.4, 0)
const MIN_ELEMENT_RADIUS = 0.005
const MAX_ELEMENT_RADIUS = 0.03

export default function AntennaArray({ config, freqHz, showPattern, weights, selected }: AntennaArrayProps) {
  // Compute element positions in local coords (array-centered)
  // Must match backend array.py axis construction so element indices align with precoder weights
  const localPositions = useMemo(() => {
    const positions: THREE.Vector3[] = []
    const broadside = new THREE.Vector3(...config.broadside).normalize()

    // Convert broadside to Z-up to match backend: [x, y, z] -> [x, -z, y]
    const bZ = [broadside.x, -broadside.z, broadside.y] as const
    const absB = [Math.abs(bZ[0]), Math.abs(bZ[1]), Math.abs(bZ[2])]
    const minIdx = absB[0] <= absB[1] && absB[0] <= absB[2] ? 0
                 : absB[1] <= absB[2] ? 1 : 2
    const ref = [0, 0, 0]
    ref[minIdx] = 1.0

    // e_h = cross(broadside_zup, ref) -- matches backend array.py
    const ehZ = [
      bZ[1] * ref[2] - bZ[2] * ref[1],
      bZ[2] * ref[0] - bZ[0] * ref[2],
      bZ[0] * ref[1] - bZ[1] * ref[0],
    ]
    const ehLen = Math.sqrt(ehZ[0] ** 2 + ehZ[1] ** 2 + ehZ[2] ** 2)
    if (ehLen > 1e-9) { ehZ[0] /= ehLen; ehZ[1] /= ehLen; ehZ[2] /= ehLen }

    // e_v = cross(broadside_zup, e_h)
    const evZ = [
      bZ[1] * ehZ[2] - bZ[2] * ehZ[1],
      bZ[2] * ehZ[0] - bZ[0] * ehZ[2],
      bZ[0] * ehZ[1] - bZ[1] * ehZ[0],
    ]

    // Convert axes back to Y-up: [x, y, z] -> [x, z, -y]
    const hAxis = new THREE.Vector3(ehZ[0], ehZ[2], -ehZ[1])
    const vAxis = new THREE.Vector3(evZ[0], evZ[2], -evZ[1])

    const lambda = 3e8 / freqHz
    const dH = config.d_h_wavelengths * lambda
    const dV = config.d_v_wavelengths * lambda

    for (let iv = 0; iv < config.n_v; iv++) {
      for (let ih = 0; ih < config.n_h; ih++) {
        const oh = (ih - (config.n_h - 1) / 2) * dH
        const ov = (iv - (config.n_v - 1) / 2) * dV
        positions.push(
          new THREE.Vector3()
            .addScaledVector(hAxis, oh)
            .addScaledVector(vAxis, ov)
        )
      }
    }
    return positions
  }, [config.n_h, config.n_v, config.d_h_wavelengths, config.d_v_wavelengths, config.broadside, freqHz])

  const patternGeo = useMemo(() => {
    if (localPositions.length === 0) return null
    const M = localPositions.length

    // Build per-element complex weights: sum all columns of W for total radiated pattern
    // W is (M_ant, K) complex. w_total[m] = sum_k W[m,k]
    const wRe = new Float64Array(M)
    const wIm = new Float64Array(M)
    if (weights && weights.real.length === M) {
      const K = weights.real[0]?.length ?? 0
      for (let m = 0; m < M; m++) {
        for (let k = 0; k < K; k++) {
          wRe[m] += weights.real[m][k]
          wIm[m] += weights.imag[m][k]
        }
      }
    } else {
      // No weights available: equal weights (quiescent pattern)
      for (let m = 0; m < M; m++) { wRe[m] = 1; wIm[m] = 0 }
    }

    const k0 = 2 * Math.PI * freqHz / 3e8
    const detail = 8
    const base = new THREE.IcosahedronGeometry(1, detail)
    const posAttr = base.attributes.position as THREE.BufferAttribute
    const nV = posAttr.count

    const gains = new Float32Array(nV)
    const dirs: THREE.Vector3[] = []
    let gMax = 0

    // Element gain computation
    const isPatch = config.element_pattern === 'patch'
    const isDipole = config.element_pattern === 'short_dipole'
    const bsDir = new THREE.Vector3(...config.broadside).normalize()
    const patchQ = 1.5

    // Dipole axis: perpendicular to broadside, matching backend compute.py logic
    let dipoleAxis: THREE.Vector3 | null = null
    if (isDipole) {
      // Find least-aligned canonical axis for stable cross product
      const absB = [Math.abs(bsDir.x), Math.abs(bsDir.y), Math.abs(bsDir.z)]
      const refVec = new THREE.Vector3(0, 0, 0)
      if (absB[0] <= absB[1] && absB[0] <= absB[2]) refVec.x = 1
      else if (absB[1] <= absB[2]) refVec.y = 1
      else refVec.z = 1
      dipoleAxis = new THREE.Vector3().crossVectors(bsDir, refVec).normalize()
    }

    for (let i = 0; i < nV; i++) {
      const dir = new THREE.Vector3(
        posAttr.getX(i), posAttr.getY(i), posAttr.getZ(i)
      ).normalize()
      dirs.push(dir)

      // Element gain for this direction
      let elementGain = 1.0
      if (isPatch) {
        const cosTheta = dir.dot(bsDir)
        elementGain = cosTheta > 0 ? cosTheta ** patchQ : 0
      } else if (isDipole && dipoleAxis) {
        const cosAlpha = dir.dot(dipoleAxis)
        elementGain = 1.5 * Math.max(0, 1 - cosAlpha * cosAlpha)
      }

      // Weighted array factor: AF = |sum_m w_m * exp(j * k0 * r_m . dir)|^2
      let reSum = 0, imSum = 0
      for (let m = 0; m < M; m++) {
        const phase = k0 * localPositions[m].dot(dir)
        const cosP = Math.cos(phase), sinP = Math.sin(phase)
        reSum += wRe[m] * cosP - wIm[m] * sinP
        imSum += wRe[m] * sinP + wIm[m] * cosP
      }
      const gain = (reSum * reSum + imSum * imSum) * elementGain * elementGain
      gains[i] = gain
      if (gain > gMax) gMax = gain
    }
    if (gMax < 1e-12) gMax = 1

    const radius = 0.6
    const lobeGamma = 0.42
    const dynDb = 36
    const colors = new Float32Array(nV * 3)

    for (let i = 0; i < nV; i++) {
      const gn = gains[i] / gMax
      const rr = radius * Math.max(gn, 1e-9) ** lobeGamma
      const d = dirs[i]
      posAttr.setXYZ(i, d.x * rr, d.y * rr, d.z * rr)

      const t = gainTFromLinear(gains[i], gMax, dynDb)
      const [cr, cg, cb] = jetColor(t)
      colors[i * 3] = cr
      colors[i * 3 + 1] = cg
      colors[i * 3 + 2] = cb
    }

    posAttr.needsUpdate = true
    base.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    base.computeVertexNormals()
    return base
  }, [localPositions, freqHz, weights, config.element_pattern, config.broadside])

  // Dispose old geometry on recompute to prevent GPU memory leak
  useEffect(() => {
    return () => { patternGeo?.dispose() }
  }, [patternGeo])

  // Panel dimensions from wavelength spacing (covers full array extent plus margin)
  const lambda = 3e8 / freqHz
  const minSpacing = Math.min(config.d_h_wavelengths, config.d_v_wavelengths) * lambda
  const elementRadius = Math.max(MIN_ELEMENT_RADIUS, Math.min(MAX_ELEMENT_RADIUS, minSpacing * 0.35))

  const panelSize = useMemo(() => {
    const dH = config.d_h_wavelengths * lambda
    const dV = config.d_v_wavelengths * lambda
    const w = (config.n_h - 1) * dH + elementRadius * 4
    const h = (config.n_v - 1) * dV + elementRadius * 4
    return { w: Math.max(w, 0.05), h: Math.max(h, 0.05) }
  }, [config.n_h, config.n_v, config.d_h_wavelengths, config.d_v_wavelengths, lambda, elementRadius])

  // Convert broadside vector to azimuth and tilt for PanelAntenna
  // In Three.js Y-up: broadside = [bx, by, bz], north = -Z
  const { azimuthDeg, tiltDeg } = useMemo(() => {
    const [bx, by, bz] = config.broadside
    const horLen = Math.sqrt(bx * bx + bz * bz)
    const az = Math.atan2(bx, -bz) * (180 / Math.PI)
    const tilt = Math.atan2(-by, horLen) * (180 / Math.PI)
    return { azimuthDeg: az, tiltDeg: tilt }
  }, [config.broadside])

  const arrowDir = useMemo(
    () => new THREE.Vector3(...config.broadside).normalize(),
    [config.broadside],
  )

  return (
    <>
      {/* Panel body, element dots, and support pole via shared component */}
      <PanelAntenna
        nH={config.n_h}
        nV={config.n_v}
        panelWidth={panelSize.w}
        panelHeight={panelSize.h}
        azimuthDeg={azimuthDeg}
        tiltDeg={tiltDeg}
        position={config.position}
        color="#555555"
        showElements
        elementDotRadius={elementRadius}
        selected={selected}
      />

      {/* Arrow and radiation pattern remain at the array center */}
      <group position={config.position}>
        {/* Broadside direction arrow */}
        <arrowHelper
          args={[arrowDir, new THREE.Vector3(0, 0, 0), 0.4, ARROW_COLOR.getHex(), 0.1, 0.06]}
        />

        {showPattern && patternGeo && (
          <group>
            <mesh geometry={patternGeo}>
              <meshStandardMaterial
                vertexColors
                transparent
                opacity={0.85}
                metalness={0.12}
                roughness={0.5}
                side={THREE.DoubleSide}
              />
            </mesh>
            <mesh>
              <sphereGeometry args={[0.04, 16, 16]} />
              <meshStandardMaterial color="#aa2222" emissive="#441010" emissiveIntensity={0.6} />
            </mesh>
          </group>
        )}
      </group>
    </>
  )
}
