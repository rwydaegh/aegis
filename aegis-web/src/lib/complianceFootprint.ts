import * as THREE from 'three'
import { scalarRadiationGain, interpolatePatternGain, type AntennaElement } from './antennaGain'

// Iso-S_inc contour for the ICNIRP compliance ring, evaluated at a fixed
// observer height above ground. Solves per-azimuth for the horizontal radius
// where the incident power density equals the compliance limit, given the
// scene's current compute result (margin_db at the body).
//
// Physics. Let A be the antenna radiator position and B the body centre.
// At B, S_body is the incident power density and the compliance margin is
//   margin_db = 10 * log10(S_limit / S_body).
// Assume S_inc(r_cand, az) = (P_tx * G(dir_cand)) / (4*pi * d_slant²),
// where dir_cand is the unit antenna-to-candidate direction and d_slant the
// 3-D slant distance. Iso condition S_inc = S_limit gives
//   d_slant² = d_body² * (G_cand / G_body) * 10^(margin_db / 10).
// Because G_cand depends on elevation, which depends on r, we iterate.
//
// Inputs are expressed in world scene coordinates with y = 0 at ground.
// The antenna radiator Y is `antennaPos.y + pole_height`. Body centre is
// approximated as (bodyOffset.x, bodyOffset.y + 0.6, bodyOffset.z), matching
// the existing DistanceLine convention.
//
// The reference direction and G_body are what makes the ring consistent
// with the compute result: at the body direction, r collapses to the body's
// horizontal distance, regardless of the pattern shape. If the body sits in
// a deep pattern null we floor G_body at `gainFloorFraction * G_peak` so
// the normalization remains finite and the ring shape remains informative.

export const DEFAULT_OBSERVER_HEIGHT_M = 1.5
export const DEFAULT_MAX_RADIUS_M = 500
export const DEFAULT_GAIN_FLOOR_FRACTION = 0.02
const MAX_ITER = 12
const TOL_M = 0.02
const PEAK_SEARCH_THETA = 17
const PEAK_SEARCH_PHI = 32

export interface FootprintInputs {
  antennaRadiatorPos: [number, number, number]
  bodyCenterPos: [number, number, number]
  marginDb: number
  patternType: string
  elements: AntennaElement[]
  appliedPattern?: Float32Array | null
  observerHeightM?: number
  maxRadiusM?: number
  nAzimuth: number
  gainFloorFraction?: number
}

export interface FootprintResult {
  radii: Float32Array
  azimuthsRad: Float32Array
  maxR: number
  meanR: number
  validAzimuths: number
  isCircular: boolean
  referenceValid: boolean
  degenerate: boolean
}

function evaluateGain(
  dir: THREE.Vector3,
  patternType: string,
  elements: AntennaElement[],
  appliedPattern: Float32Array | null | undefined,
): number {
  if (appliedPattern) return interpolatePatternGain(dir, appliedPattern)
  return scalarRadiationGain(dir, patternType, elements)
}

function findPeakGain(
  patternType: string,
  elements: AntennaElement[],
  appliedPattern: Float32Array | null | undefined,
): number {
  const d = new THREE.Vector3()
  let peak = 0
  // Uniform grid over the sphere, dense enough to catch narrow main lobes.
  for (let i = 0; i < PEAK_SEARCH_THETA; i++) {
    const theta = (i / (PEAK_SEARCH_THETA - 1)) * Math.PI
    const sinT = Math.sin(theta)
    const cosT = Math.cos(theta)
    for (let j = 0; j < PEAK_SEARCH_PHI; j++) {
      const phi = (j / PEAK_SEARCH_PHI) * 2 * Math.PI
      d.set(sinT * Math.sin(phi), cosT, sinT * Math.cos(phi))
      const g = evaluateGain(d, patternType, elements, appliedPattern)
      if (g > peak) peak = g
    }
  }
  return Math.max(peak, 1e-20)
}

export function computeComplianceFootprint(inputs: FootprintInputs): FootprintResult {
  const {
    antennaRadiatorPos,
    bodyCenterPos,
    marginDb,
    patternType,
    elements,
    appliedPattern,
  } = inputs
  const observerHeightM = inputs.observerHeightM ?? DEFAULT_OBSERVER_HEIGHT_M
  const maxRadiusM = inputs.maxRadiusM ?? DEFAULT_MAX_RADIUS_M
  const gainFloorFraction = inputs.gainFloorFraction ?? DEFAULT_GAIN_FLOOR_FRACTION
  const nAzimuth = Math.max(4, Math.floor(inputs.nAzimuth))

  const azimuths = new Float32Array(nAzimuth)
  const radii = new Float32Array(nAzimuth)
  const empty: FootprintResult = {
    radii,
    azimuthsRad: azimuths,
    maxR: 0,
    meanR: 0,
    validAzimuths: 0,
    isCircular: true,
    referenceValid: false,
    degenerate: true,
  }

  if (!Number.isFinite(marginDb)) return empty

  const dxB = bodyCenterPos[0] - antennaRadiatorPos[0]
  const dyB = bodyCenterPos[1] - antennaRadiatorPos[1]
  const dzB = bodyCenterPos[2] - antennaRadiatorPos[2]
  const dBody3d = Math.sqrt(dxB * dxB + dyB * dyB + dzB * dzB)
  if (!(dBody3d > 0)) return empty

  const dirBody = new THREE.Vector3(dxB / dBody3d, dyB / dBody3d, dzB / dBody3d)
  const gPeak = findPeakGain(patternType, elements, appliedPattern)
  const gBodyRaw = evaluateGain(dirBody, patternType, elements, appliedPattern)
  const gBodyFloor = gPeak * gainFloorFraction
  const gBody = Math.max(gBodyRaw, gBodyFloor, 1e-20)
  const referenceValid = gBodyRaw >= gBodyFloor

  // dh > 0 means the antenna is above the observer plane.
  const dh = antennaRadiatorPos[1] - observerHeightM
  const dhSq = dh * dh
  // Positive margin_db => compliant at body => iso contour is closer in than
  // the body. S_limit / S_body = 10^(margin_db/10). Since S ∝ 1/d², the slant
  // distance at which S = S_limit scales as d_body * 10^(-margin_db/20).
  const scale = Math.pow(10, -marginDb / 20)
  const scalePowSq = Math.pow(10, -marginDb / 10)

  const candDir = new THREE.Vector3()
  let maxR = 0
  let sumR = 0
  let validCount = 0
  let minNonZero = Infinity

  for (let i = 0; i < nAzimuth; i++) {
    const az = (i / nAzimuth) * 2 * Math.PI
    azimuths[i] = az
    const sinAz = Math.sin(az)
    const cosAz = Math.cos(az)

    // Initial guess: horizontal slice through the antenna, ignoring dh.
    candDir.set(sinAz, 0, cosAz)
    const gH = evaluateGain(candDir, patternType, elements, appliedPattern)
    let r = dBody3d * Math.sqrt(Math.max(gH, 1e-20) / gBody) * scale
    r = Math.min(Math.max(r, 0), maxRadiusM)

    for (let iter = 0; iter < MAX_ITER; iter++) {
      const dSlant = Math.sqrt(r * r + dhSq)
      candDir.set(r * sinAz / dSlant, -dh / dSlant, r * cosAz / dSlant)
      const gCand = evaluateGain(candDir, patternType, elements, appliedPattern)
      const dSlantNewSq = dBody3d * dBody3d * (Math.max(gCand, 1e-20) / gBody) * scalePowSq
      let rNew: number
      if (dSlantNewSq <= dhSq) {
        rNew = 0
      } else {
        rNew = Math.sqrt(dSlantNewSq - dhSq)
      }
      rNew = Math.min(Math.max(rNew, 0), maxRadiusM)

      if (Math.abs(rNew - r) < TOL_M) {
        r = rNew
        break
      }
      // Light damping keeps iteration stable across sharp pattern transitions.
      r = 0.7 * rNew + 0.3 * r
    }

    radii[i] = r
    if (r > maxR) maxR = r
    if (r > 0) {
      validCount++
      sumR += r
      if (r < minNonZero) minNonZero = r
    }
  }

  const degenerate = validCount === 0
  const meanR = degenerate ? 0 : sumR / validCount
  const rangeR = maxR - (degenerate ? 0 : minNonZero)
  const isCircular = !degenerate && maxR > 0 && rangeR / Math.max(maxR, 1e-9) < 0.02

  return {
    radii,
    azimuthsRad: azimuths,
    maxR,
    meanR,
    validAzimuths: validCount,
    isCircular,
    referenceValid,
    degenerate,
  }
}

export function smoothRadii(radii: Float32Array, passes: number): Float32Array {
  if (passes <= 0) return radii
  const n = radii.length
  const out = new Float32Array(radii)
  const scratch = new Float32Array(n)
  for (let pass = 0; pass < passes; pass++) {
    for (let i = 0; i < n; i++) {
      const prev = out[(i - 1 + n) % n]
      const next = out[(i + 1) % n]
      scratch[i] = 0.25 * prev + 0.5 * out[i] + 0.25 * next
    }
    out.set(scratch)
  }
  return out
}

// Full 3-D iso-S_inc surface around the antenna. Same physics as the ring,
// but sampled on an azimuth × elevation grid so the surface traces the whole
// sphere where S_inc = S_limit, not just its intersection with the observer
// plane. No Picard iteration is needed: once (az, el) are chosen, the direction
// is fixed and the iso-condition gives a closed-form slant radius
//   r(az, el) = d_body * sqrt(G(az, el) / G_body) * 10^(-margin_db / 20).
//
// Output is a flat-packed (nAzimuth × nElevation) grid of slant radii. Vertex
// positions relative to the antenna radiator follow
//   x =  r * cos(el) * sin(az)
//   y =  r * sin(el)          (Y-up, Three.js convention)
//   z =  r * cos(el) * cos(az)
// so the caller can triangulate the surface directly.

export interface VolumeInputs {
  antennaRadiatorPos: [number, number, number]
  bodyCenterPos: [number, number, number]
  marginDb: number
  patternType: string
  elements: AntennaElement[]
  appliedPattern?: Float32Array | null
  nAzimuth: number
  nElevation: number
  maxRadiusM?: number
  gainFloorFraction?: number
}

export interface VolumeResult {
  // Row-major (i_az * nElevation + j_el) slant radii in meters.
  radii: Float32Array
  azimuthsRad: Float32Array
  elevationsRad: Float32Array
  nAzimuth: number
  nElevation: number
  maxR: number
  meanR: number
  validSamples: number
  referenceValid: boolean
  degenerate: boolean
}

export function computeComplianceVolume(inputs: VolumeInputs): VolumeResult {
  const {
    antennaRadiatorPos,
    bodyCenterPos,
    marginDb,
    patternType,
    elements,
    appliedPattern,
  } = inputs
  const maxRadiusM = inputs.maxRadiusM ?? DEFAULT_MAX_RADIUS_M
  const gainFloorFraction = inputs.gainFloorFraction ?? DEFAULT_GAIN_FLOOR_FRACTION
  const nAzimuth = Math.max(4, Math.floor(inputs.nAzimuth))
  const nElevation = Math.max(3, Math.floor(inputs.nElevation))

  const azimuths = new Float32Array(nAzimuth)
  const elevations = new Float32Array(nElevation)
  const radii = new Float32Array(nAzimuth * nElevation)

  const empty: VolumeResult = {
    radii,
    azimuthsRad: azimuths,
    elevationsRad: elevations,
    nAzimuth,
    nElevation,
    maxR: 0,
    meanR: 0,
    validSamples: 0,
    referenceValid: false,
    degenerate: true,
  }

  if (!Number.isFinite(marginDb)) return empty

  const dxB = bodyCenterPos[0] - antennaRadiatorPos[0]
  const dyB = bodyCenterPos[1] - antennaRadiatorPos[1]
  const dzB = bodyCenterPos[2] - antennaRadiatorPos[2]
  const dBody3d = Math.sqrt(dxB * dxB + dyB * dyB + dzB * dzB)
  if (!(dBody3d > 0)) return empty

  const dirBody = new THREE.Vector3(dxB / dBody3d, dyB / dBody3d, dzB / dBody3d)
  const gPeak = findPeakGain(patternType, elements, appliedPattern)
  const gBodyRaw = evaluateGain(dirBody, patternType, elements, appliedPattern)
  const gBodyFloor = gPeak * gainFloorFraction
  const gBody = Math.max(gBodyRaw, gBodyFloor, 1e-20)
  const referenceValid = gBodyRaw >= gBodyFloor

  const scale = Math.pow(10, -marginDb / 20)

  for (let i = 0; i < nAzimuth; i++) {
    azimuths[i] = (i / nAzimuth) * 2 * Math.PI
  }
  for (let j = 0; j < nElevation; j++) {
    // Inclusive endpoints: -π/2 (nadir) to +π/2 (zenith).
    elevations[j] = -Math.PI / 2 + (j / (nElevation - 1)) * Math.PI
  }

  const candDir = new THREE.Vector3()
  let maxR = 0
  let sumR = 0
  let validCount = 0

  for (let j = 0; j < nElevation; j++) {
    const el = elevations[j]
    const cosEl = Math.cos(el)
    const sinEl = Math.sin(el)
    for (let i = 0; i < nAzimuth; i++) {
      const az = azimuths[i]
      const sinAz = Math.sin(az)
      const cosAz = Math.cos(az)
      candDir.set(cosEl * sinAz, sinEl, cosEl * cosAz)
      const gCand = evaluateGain(candDir, patternType, elements, appliedPattern)
      let r = dBody3d * Math.sqrt(Math.max(gCand, 1e-20) / gBody) * scale
      if (!Number.isFinite(r) || r < 0) r = 0
      if (r > maxRadiusM) r = maxRadiusM
      radii[i * nElevation + j] = r
      if (r > 0) {
        validCount++
        sumR += r
        if (r > maxR) maxR = r
      }
    }
  }

  const degenerate = validCount === 0 || maxR <= 0
  const meanR = degenerate ? 0 : sumR / validCount

  return {
    radii,
    azimuthsRad: azimuths,
    elevationsRad: elevations,
    nAzimuth,
    nElevation,
    maxR,
    meanR,
    validSamples: validCount,
    referenceValid,
    degenerate,
  }
}
