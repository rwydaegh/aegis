// Pure, testable core of the studio's colour-scale system. No THREE, no DOM, no
// store: it turns the user's scale choices (mode / scope / colormap / dynamic
// range / robust clip / fixed range) plus the data ranges of the rendered
// surfaces into a single resolved scale that the slice, body map, volume, and
// legend all consume identically. Keeping it here (rather than scattered across
// the shader, the body mesh, and the HUD) is what lets "shared scope" make equal
// colours mean equal values, and what makes the legend honest.

import { signedSymmetricRange, isSignedQuantity } from './studioHelpers'

export type StudioScaleMode = 'auto' | 'fixed' | 'log'
export type StudioScaleScope = 'surface' | 'shared'

export interface Range {
  vmin: number
  vmax: number
}

export interface ResolvedScale {
  colormap: string
  vmin: number
  vmax: number
  logMode: boolean
  dynamicRangeDb: number
  /** True when the resolved scale is the diverging signed map (slice ReE only). */
  signed: boolean
}

// Default robust-clip percentiles: keep the dynamic range honest by ignoring the
// most extreme half-percent at each end (a single hot triangle / voxel otherwise
// compresses the whole map into the floor).
export const ROBUST_LO = 0.005
export const ROBUST_HI = 0.995

/** Min/max of a value array, skipping non-finite entries. null if empty. */
export function minMax(values: ArrayLike<number>): Range | null {
  let vmin = Infinity
  let vmax = -Infinity
  for (let i = 0; i < values.length; i++) {
    const v = values[i]
    if (!Number.isFinite(v)) continue
    if (v < vmin) vmin = v
    if (v > vmax) vmax = v
  }
  if (vmin === Infinity) return null
  return { vmin, vmax }
}

/**
 * Percentile range [p(loFrac), p(hiFrac)] of a value array (linear interpolation
 * between order statistics). Copies and sorts, so call it once per data fetch and
 * memoise, not per frame. null for an empty array.
 */
export function percentileRange(values: ArrayLike<number>, loFrac: number, hiFrac: number): Range | null {
  const finite: number[] = []
  for (let i = 0; i < values.length; i++) {
    if (Number.isFinite(values[i])) finite.push(values[i])
  }
  if (finite.length === 0) return null
  finite.sort((a, b) => a - b)
  const pick = (frac: number): number => {
    const clamped = Math.min(1, Math.max(0, frac))
    const idx = clamped * (finite.length - 1)
    const lo = Math.floor(idx)
    const hi = Math.ceil(idx)
    if (lo === hi) return finite[lo]
    return finite[lo] + (idx - lo) * (finite[hi] - finite[lo])
  }
  return { vmin: pick(loFrac), vmax: pick(hiFrac) }
}

/** Data range of a surface: percentile-clipped when robust, raw min/max otherwise. */
export function rangeOf(values: ArrayLike<number> | null | undefined, robust: boolean): Range | null {
  if (!values || values.length === 0) return null
  return robust ? percentileRange(values, ROBUST_LO, ROBUST_HI) : minMax(values)
}

/** Tightest range covering every input range (null inputs ignored). */
export function unionRange(ranges: (Range | null | undefined)[]): Range | null {
  let vmin = Infinity
  let vmax = -Infinity
  for (const r of ranges) {
    if (!r) continue
    if (r.vmin < vmin) vmin = r.vmin
    if (r.vmax > vmax) vmax = r.vmax
  }
  if (vmin === Infinity) return null
  return { vmin, vmax }
}

export interface ScaleInputs {
  /** Field/body quantity. Signed slice components force the diverging map. */
  quantity: string
  mode: StudioScaleMode
  scope: StudioScaleScope
  colormap: string
  dynamicRangeDb: number
  /** User-locked range, used only in 'fixed' mode. */
  fixedRange: Range | null
  /** This surface's own (already robust-clipped) data range. */
  surfaceRange: Range | null
  /** Union of every visible surface's range, used in 'shared' scope. */
  sharedRange: Range | null
}

const FALLBACK: Range = { vmin: 0, vmax: 1 }

/**
 * Resolve the colour scale a surface renders with. Precedence:
 *
 *  1. Signed slice components (ReEx/y/z) always use a diverging coolwarm map over
 *     a symmetric range centred on zero, ignoring scope/mode (a signed field has
 *     no shared-with-Sab scale and no log scale).
 *  2. 'fixed' mode uses the user's locked range verbatim.
 *  3. otherwise the range is the shared-union range ('shared' scope) or this
 *     surface's own range ('surface' scope).
 *
 * For non-signed quantities the linear floor is pinned to 0 (power densities are
 * non-negative and the body map normalises from 0), so a colour means the same
 * value on the slice, the body, and the volume. 'log' keeps a dynamic-range
 * window below vmax (see scaleNormalise), so vmin is informational there.
 */
export function resolveScale(a: ScaleInputs): ResolvedScale {
  const dr = a.dynamicRangeDb
  if (isSignedQuantity(a.quantity)) {
    const base = a.surfaceRange ?? FALLBACK
    const sym = signedSymmetricRange(base.vmin, base.vmax)
    return { colormap: 'coolwarm', vmin: sym.vmin, vmax: sym.vmax, logMode: false, dynamicRangeDb: dr, signed: true }
  }

  const logMode = a.mode === 'log'
  if (a.mode === 'fixed' && a.fixedRange) {
    return { colormap: a.colormap, vmin: a.fixedRange.vmin, vmax: a.fixedRange.vmax, logMode, dynamicRangeDb: dr, signed: false }
  }

  const base = (a.scope === 'shared' ? a.sharedRange : a.surfaceRange) ?? FALLBACK
  // Non-negative quantity: pin the linear floor to 0 so slice / body / volume
  // share an identical 0..vmax mapping (the body mesh normalises from 0).
  const vmax = base.vmax > 0 ? base.vmax : 1
  return { colormap: a.colormap, vmin: 0, vmax, logMode, dynamicRangeDb: dr, signed: false }
}

/**
 * The single normalisation t in [0, 1] for a value under a resolved scale, shared
 * by the volume (JS) and mirrored by the slice shader (GLSL) and body mesh (dB).
 * Linear: (v - vmin) / (vmax - vmin). Log: a dynamic-range window of `dr` dB below
 * vmax, so all three surfaces and the legend agree on what "log" means.
 */
export function scaleNormalise(v: number, s: ResolvedScale): number {
  if (s.logMode) {
    const gMax = Math.max(s.vmax, 1e-30)
    const gMin = gMax * Math.pow(10, -s.dynamicRangeDb / 10)
    const lo = Math.log10(gMin)
    const hi = Math.log10(Math.max(gMax, gMin * 1.0001))
    const vv = Math.min(Math.max(v, gMin), gMax)
    return clamp01((Math.log10(vv) - lo) / (hi - lo))
  }
  if (s.vmax <= s.vmin) return 0
  return clamp01((v - s.vmin) / (s.vmax - s.vmin))
}

/** Low edge of the log dynamic-range window (vmax * 10^(-dr/10)); for legend ticks. */
export function logFloor(s: ResolvedScale): number {
  return Math.max(s.vmax, 1e-30) * Math.pow(10, -s.dynamicRangeDb / 10)
}

function clamp01(t: number): number {
  return Math.min(1, Math.max(0, t))
}
