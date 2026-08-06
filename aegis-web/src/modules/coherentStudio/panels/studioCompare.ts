// Pure core of the A/B beam comparison. Capture one body map as a reference (A),
// then compare the live body map (B) against it triangle by triangle. The signed
// delta B - A is what tells the paper's story: how much a body-aware beam (ECBF)
// lowers the deposited power relative to a matched-filter beam (MRT). Summary
// statistics plus the per-triangle delta for a diverging histogram.

import { percentileRange } from '../scene/colorScale'

function p95(values: ArrayLike<number>): number {
  const r = percentileRange(values, 0.95, 0.95)
  return r ? r.vmax : 0
}

function mean(values: ArrayLike<number>): number {
  let sum = 0
  let n = 0
  for (let i = 0; i < values.length; i++) {
    if (Number.isFinite(values[i])) {
      sum += values[i]
      n++
    }
  }
  return n > 0 ? sum / n : 0
}

function peak(values: ArrayLike<number>): number {
  let m = -Infinity
  for (let i = 0; i < values.length; i++) if (values[i] > m) m = values[i]
  return m === -Infinity ? 0 : m
}

export interface CompareStats {
  /** Triangle count (both maps must match). */
  n: number
  meanA: number
  meanB: number
  p95A: number
  p95B: number
  peakA: number
  peakB: number
  /** Percent change of B relative to A (negative = B lower than A). */
  meanPct: number
  p95Pct: number
  peakPct: number
  /** Fraction of triangles where B is strictly below A (exposure reduced). */
  reducedFrac: number
  /** Per-triangle signed delta B - A. */
  delta: Float32Array
  /** Largest |delta|, for a symmetric diverging colour range. */
  maxAbsDelta: number
}

function pct(a: number, b: number): number {
  if (a === 0) return b === 0 ? 0 : Infinity
  return (100 * (b - a)) / a
}

/**
 * Compare a reference body map A against the current map B (same triangle order).
 * Returns null if the lengths differ (different mesh / array). delta is B - A, so
 * negative means B deposits less than A on that triangle.
 */
export function compareMaps(reference: ArrayLike<number>, current: ArrayLike<number>): CompareStats | null {
  if (reference.length === 0 || reference.length !== current.length) return null
  const n = reference.length
  const delta = new Float32Array(n)
  let reduced = 0
  let maxAbsDelta = 0
  for (let i = 0; i < n; i++) {
    const d = current[i] - reference[i]
    delta[i] = d
    if (current[i] < reference[i]) reduced++
    const ad = Math.abs(d)
    if (ad > maxAbsDelta) maxAbsDelta = ad
  }
  const meanA = mean(reference)
  const meanB = mean(current)
  const p95A = p95(reference)
  const p95B = p95(current)
  const peakA = peak(reference)
  const peakB = peak(current)
  return {
    n,
    meanA,
    meanB,
    p95A,
    p95B,
    peakA,
    peakB,
    meanPct: pct(meanA, meanB),
    p95Pct: pct(p95A, p95B),
    peakPct: pct(peakA, peakB),
    reducedFrac: reduced / n,
    delta,
    maxAbsDelta,
  }
}
