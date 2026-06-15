// Pure core of the antenna-pattern cut. The studio's base station is a uniform
// rectangular array (URA) of N x N elements at half-wavelength spacing, steered
// broadside toward the focus. Its principal-plane array factor then has the
// classic closed form
//
//   AF(psi) = | sin(N pi d sin psi) / (N sin(pi d sin psi)) |
//
// (the Dirichlet kernel), normalised to unity at boresight. An optional patch
// element factor cos(psi) rolls the gain off toward the array horizon. This is
// the geometric array factor of the uniform-amplitude steered array, a faithful
// stand-in for the MRT / broadside beam; the true ECBF pattern (amplitude-tapered
// to dodge the body) differs, which is why the panel labels it as the array
// factor rather than the realised beam. All client-side, no backend.

export interface PatternPoint {
  /** Angle off boresight in the cut plane, degrees (-90..90). */
  angleDeg: number
  /** Normalised power, dB (0 dB at boresight, floored). */
  db: number
}

export interface PatternCut {
  points: PatternPoint[]
  /** Half-power (-3 dB) beamwidth, degrees (NaN if it never drops 3 dB). */
  hpbwDeg: number
  /** First sidelobe level relative to the main lobe, dB (negative; NaN if none). */
  sidelobeDb: number
  /** dB floor the curve is clamped to (for the chart y-domain). */
  floorDb: number
}

/** Normalised array-factor magnitude (0..1) at angle psi (radians) off boresight. */
function afMag(psi: number, n: number, d: number): number {
  const u = Math.sin(psi)
  const x = Math.PI * d * u
  // Dirichlet kernel limit at x -> 0 is 1.
  if (Math.abs(Math.sin(x)) < 1e-9) return 1
  return Math.abs(Math.sin(n * x) / (n * Math.sin(x)))
}

/**
 * Principal-plane pattern cut of an N-element uniform line of the URA at spacing
 * `dWavelengths`, sampled over -90..90 degrees. `withElement` multiplies in a
 * cos(psi) patch element factor. Power is in dB, clamped to `floorDb`.
 */
export function arrayFactorCut(
  n: number,
  dWavelengths: number,
  nSamples = 361,
  withElement = true,
  floorDb = -40,
): PatternCut {
  const points: PatternPoint[] = []
  for (let s = 0; s < nSamples; s++) {
    const deg = -90 + (180 * s) / (nSamples - 1)
    const psi = (deg * Math.PI) / 180
    let amp = afMag(psi, n, dWavelengths)
    if (withElement) amp *= Math.max(Math.cos(psi), 0)
    const power = amp * amp
    const db = power > 0 ? Math.max(10 * Math.log10(power), floorDb) : floorDb
    points.push({ angleDeg: deg, db })
  }

  // HPBW: total angular width where the curve is within 3 dB of the boresight peak.
  const mid = (nSamples - 1) / 2
  let left = NaN
  let right = NaN
  for (let s = Math.floor(mid); s > 0; s--) {
    if (points[s - 1].db <= -3) {
      left = interpCross(points[s - 1], points[s], -3)
      break
    }
  }
  for (let s = Math.ceil(mid); s < nSamples - 1; s++) {
    if (points[s + 1].db <= -3) {
      right = interpCross(points[s + 1], points[s], -3)
      break
    }
  }
  const hpbwDeg = isFinite(left) && isFinite(right) ? right - left : NaN

  // First sidelobe: the highest local maximum outside the main lobe.
  let sidelobeDb = NaN
  for (let s = 1; s < nSamples - 1; s++) {
    const a = points[s]
    if (a.db > points[s - 1].db && a.db >= points[s + 1].db) {
      // Skip the main lobe (near boresight, within HPBW or first few degrees).
      if (Math.abs(a.angleDeg) < (isFinite(hpbwDeg) ? hpbwDeg : 4)) continue
      if (isNaN(sidelobeDb) || a.db > sidelobeDb) sidelobeDb = a.db
    }
  }
  return { points, hpbwDeg, sidelobeDb, floorDb }
}

/** Angle where the segment a..b crosses `level` dB (linear interp in dB vs deg). */
function interpCross(a: PatternPoint, b: PatternPoint, level: number): number {
  const denom = b.db - a.db
  if (Math.abs(denom) < 1e-30) return a.angleDeg
  return a.angleDeg + ((level - a.db) / denom) * (b.angleDeg - a.angleDeg)
}
