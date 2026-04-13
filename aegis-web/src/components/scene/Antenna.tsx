import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { jetColor, gainTFromLinear } from '@/lib/colormap'

/** Scalar radiation gain for a direction vector (Y-up scene coords). */
function scalarRadiationGain(
  dir: THREE.Vector3,
  type: string,
  elements: Array<{ offset?: number[]; weight?: number[]; axis?: number[] }>,
): number {
  if (type === 'isotropic') {
    let s = 0
    for (const el of elements) {
      const w = el.weight ?? [1, 0]
      s += w[0] * w[0] + (w[1] ?? 0) * (w[1] ?? 0)
    }
    return Math.max(s, 1e-9)
  }
  if (type === 'patch') {
    // cos^q(theta) pattern where theta is angle from boresight (default -Z in Y-up)
    const q = 1.5
    let gsum = 0
    for (const el of elements) {
      const w = el.weight ?? [1, 0]
      const w2 = w[0] * w[0] + (w[1] ?? 0) * (w[1] ?? 0)
      // Boresight is perpendicular to dipole axis: for default vertical dipole [0,1,0],
      // boresight is -Z direction [0,0,-1] in Y-up coords
      const ax = new THREE.Vector3(...(el.axis ?? [0, 1, 0]))
      if (ax.lengthSq() < 1e-12) ax.set(0, 1, 0)
      ax.normalize()
      // Boresight = direction perpendicular to dipole axis (pick -Z component)
      const boresight = new THREE.Vector3(0, 0, -1)
      const cosTheta = dir.dot(boresight)
      gsum += w2 * Math.max(cosTheta, 0) ** q
    }
    return Math.max(gsum, 1e-12)
  }
  // short_dipole (default): 1.5 * sin^2(alpha) where alpha is angle from dipole axis
  let gsum = 0
  for (const el of elements) {
    const w = el.weight ?? [1, 0]
    const w2 = w[0] * w[0] + (w[1] ?? 0) * (w[1] ?? 0)
    const ax = new THREE.Vector3(...(el.axis ?? [0, 1, 0]))
    if (ax.lengthSq() < 1e-12) ax.set(0, 1, 0)
    ax.normalize()
    const c = dir.dot(ax)
    gsum += w2 * Math.max(0, 1 - c * c)
  }
  return Math.max(gsum, 1e-12)
}

/**
 * Bilinear interpolation of gain from a (181, 360) dBi grid.
 * Direction vector is in Y-up scene coords (Three.js convention).
 * Grid layout: row 0 = elevation -90° (nadir), row 180 = +90° (zenith).
 * Col 0 = azimuth -180°, col 180 = azimuth 0° (boresight).
 */
function interpolatePatternGain(dir: THREE.Vector3, data: Float32Array): number {
  const elevDeg = Math.asin(Math.max(-1, Math.min(1, dir.y))) * (180 / Math.PI)
  const azimDeg = Math.atan2(dir.x, dir.z) * (180 / Math.PI)

  const row = elevDeg + 90
  const col = ((azimDeg + 180) % 360 + 360) % 360

  const r0 = Math.floor(row)
  const r1 = Math.min(r0 + 1, 180)
  const c0 = Math.floor(col)
  const c1 = c0 + 1 >= 360 ? 0 : c0 + 1
  const fr = row - r0
  const fc = col - c0

  // Interpolate in linear domain (not dB) to avoid bias near nulls
  const toLinear = (dbi: number) => dbi <= -199 ? 1e-20 : Math.pow(10, dbi / 10)
  const g = toLinear(data[r0 * 360 + c0]) * (1 - fr) * (1 - fc)
    + toLinear(data[r0 * 360 + c1]) * (1 - fr) * fc
    + toLinear(data[r1 * 360 + c0]) * fr * (1 - fc)
    + toLinear(data[r1 * 360 + c1]) * fr * fc
  return Math.max(g, 1e-20)
}

interface AntennaProps {
  position: [number, number, number]
  selected?: boolean
  elementPattern?: string
}

export default function Antenna({ position, selected = true, elementPattern }: AntennaProps) {
  const config = useSceneStore(s => s.viewerConfig)
  const wireframe = useUIStore(s => s.wireframe)
  const cameraMode = useUIStore(s => s.cameraMode)
  const appliedPattern = useSimulationStore(s => s.appliedPattern)
  const appliedPatternMeta = useSimulationStore(s => s.appliedPatternMeta)

  const prevGeoRef = useRef<THREE.BufferGeometry | null>(null)

  const patternGeo = useMemo(() => {
    prevGeoRef.current?.dispose()
    prevGeoRef.current = null
    if (!config) return null
    const rp = config.antenna.radiation_pattern
    if (!rp || rp.enabled === false) return null

    const detail = Math.min(rp.ico_detail ?? 5, 6)
    const base = new THREE.IcosahedronGeometry(1, detail)
    const posAttr = base.attributes.position as THREE.BufferAttribute
    const nV = posAttr.count

    const type = elementPattern ?? rp.type ?? 'short_dipole'
    const elements = rp.elements?.length
      ? rp.elements
      : [{ offset: [0, 0, 0], weight: [1, 0], axis: [0, 1, 0] }]
    const dynDb = rp.dynamic_range_db ?? 36
    const lobeG = rp.lobe_gamma ?? 0.42
    const rad = rp.radius ?? 0.9

    const useLoadedPattern = appliedPattern && appliedPatternMeta
    const gains = new Float32Array(nV)
    const dirs: THREE.Vector3[] = []
    let gMax = 0
    for (let i = 0; i < nV; i++) {
      const x = posAttr.getX(i)
      const y = posAttr.getY(i)
      const z = posAttr.getZ(i)
      const dir = new THREE.Vector3(x, y, z).normalize()
      dirs.push(dir)
      const g = useLoadedPattern
        ? interpolatePatternGain(dir, appliedPattern)
        : scalarRadiationGain(dir, type, elements)
      gains[i] = g
      if (g > gMax) gMax = g
    }
    if (gMax < 1e-12) gMax = 1

    const colors = new Float32Array(nV * 3)
    for (let i = 0; i < nV; i++) {
      const gn = gains[i] / gMax
      const rr = rad * (Math.max(gn, 1e-9) ** lobeG)
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

    prevGeoRef.current = base
    return base
  }, [config, appliedPattern, appliedPatternMeta, elementPattern])

  useEffect(() => () => { prevGeoRef.current?.dispose() }, [])

  if (!config) return null

  const ant = config.antenna
  const rp = ant.radiation_pattern
  const usePattern = rp && rp.enabled !== false && cameraMode === 'orbit'

  const poleH = ant.pole_height ?? 2
  const poleR = ant.pole_radius ?? 0.015
  const coneH = ant.cone_height ?? 0.15
  const coneR = ant.cone_radius ?? 0.05
  const coneYOff = ant.cone_y_offset ?? -0.12

  // Antenna tip height: top of the pole
  const tipY = poleH

  return (
    <group position={position}>
      {/* Pole: base at y=0 (click point), extends upward */}
      <mesh position={[0, poleH / 2, 0]}>
        <cylinderGeometry args={[poleR, poleR, poleH, ant.pole_segments ?? 8]} />
        <meshStandardMaterial color={selected ? (ant.color ?? '#ff3333') : (ant.pole_color ?? '#888888')} />
      </mesh>

      {/* Radiation pattern mesh at top of pole */}
      {usePattern && patternGeo && (
        <group position={[0, tipY, 0]}>
          <mesh geometry={patternGeo}>
            <meshStandardMaterial
              vertexColors
              transparent
              opacity={(rp.opacity ?? 0.94) * (selected ? 1.0 : 0.5)}
              metalness={rp.metalness ?? 0.12}
              roughness={rp.roughness ?? 0.5}
              side={THREE.DoubleSide}
              wireframe={wireframe}
            />
          </mesh>
          {/* Hub sphere at center of pattern */}
          <mesh>
            <sphereGeometry args={[rp.hub_radius ?? 0.055, 18, 18]} />
            <meshStandardMaterial
              color={rp.hub_color ?? '#aa2222'}
              emissive={rp.hub_emissive ?? '#441010'}
              emissiveIntensity={0.6}
              metalness={0.35}
              roughness={0.35}
            />
          </mesh>
        </group>
      )}

      {/* Fallback: simple sphere + cone at top of pole */}
      {!usePattern && (
        <group position={[0, tipY, 0]}>
          <mesh>
            <sphereGeometry args={[ant.sphere_radius ?? 0.08, ant.sphere_segments ?? 16, ant.sphere_segments ?? 16]} />
            <meshStandardMaterial color={ant.color ?? '#ff3333'} emissive={ant.emissive_color ?? '#881111'} />
          </mesh>
          <mesh position={[0, coneYOff, 0]} rotation={[Math.PI, 0, 0]}>
            <coneGeometry args={[coneR, coneH, ant.cone_segments ?? 16]} />
            <meshStandardMaterial color={ant.color ?? '#ff3333'} emissive={ant.emissive_color ?? '#881111'} />
          </mesh>
        </group>
      )}
    </group>
  )
}
