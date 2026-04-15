import * as THREE from 'three'

export interface AntennaElement {
  offset?: number[]
  weight?: number[]
  axis?: number[]
}

const _dir = new THREE.Vector3()

/**
 * Scalar radiation gain for a direction vector (Y-up scene coords).
 * Supports isotropic, patch (cos^q boresight), and short_dipole (sin^2 from axis).
 */
export function scalarRadiationGain(
  dir: THREE.Vector3,
  type: string,
  elements: AntennaElement[],
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
    const q = 1.5
    let gsum = 0
    for (const el of elements) {
      const w = el.weight ?? [1, 0]
      const w2 = w[0] * w[0] + (w[1] ?? 0) * (w[1] ?? 0)
      const ax = _dir.set(...(el.axis ?? [0, 1, 0]) as [number, number, number])
      if (ax.lengthSq() < 1e-12) ax.set(0, 1, 0)
      ax.normalize()
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
    const ax = _dir.set(...(el.axis ?? [0, 1, 0]) as [number, number, number])
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
 * Grid layout: row 0 = elevation -90 (nadir), row 180 = +90 (zenith).
 * Col 0 = azimuth -180, col 180 = azimuth 0 (boresight).
 */
export function interpolatePatternGain(dir: THREE.Vector3, data: Float32Array): number {
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

  const toLinear = (dbi: number) => dbi <= -199 ? 1e-20 : Math.pow(10, dbi / 10)
  const g = toLinear(data[r0 * 360 + c0]) * (1 - fr) * (1 - fc)
    + toLinear(data[r0 * 360 + c1]) * (1 - fr) * fc
    + toLinear(data[r1 * 360 + c0]) * fr * (1 - fc)
    + toLinear(data[r1 * 360 + c1]) * fr * fc
  return Math.max(g, 1e-20)
}
