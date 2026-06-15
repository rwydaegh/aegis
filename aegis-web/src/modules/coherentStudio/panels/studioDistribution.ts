// Pure helpers for the studio exposure-distribution panel: a cumulative
// distribution (what fraction of the body absorbs at or below a level) derived
// from the histogram bins, plus the area / fraction above a threshold. Kept
// separate from the recharts component so the maths is unit-testable.

export interface HistBin {
  x0: number
  x1: number
  count: number
  label: string
}

export interface DistPoint extends HistBin {
  /** Cumulative fraction of triangles with value <= this bin's upper edge. */
  cdf: number
  /** Bin-centre value, for colouring the bar by the active colormap. */
  center: number
}

/**
 * Attach a cumulative fraction to each histogram bin (0..1, monotone, ending at
 * 1). cdf[i] is the fraction of all counts in bins 0..i, i.e. the fraction of
 * triangles whose value is at or below bin i's upper edge.
 */
export function withCdf(bins: HistBin[]): DistPoint[] {
  const total = bins.reduce((a, b) => a + b.count, 0)
  let run = 0
  return bins.map((b) => {
    run += b.count
    return { ...b, cdf: total > 0 ? run / total : 0, center: 0.5 * (b.x0 + b.x1) }
  })
}

/** Fraction of values strictly greater than `threshold` (0..1). */
export function fractionAbove(values: ArrayLike<number>, threshold: number): number {
  if (values.length === 0) return 0
  let n = 0
  for (let i = 0; i < values.length; i++) if (values[i] > threshold) n++
  return n / values.length
}
