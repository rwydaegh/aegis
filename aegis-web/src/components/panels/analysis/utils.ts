// ---------------------------------------------------------------------------
// Shared helpers for the Analysis panel sections
// ---------------------------------------------------------------------------

/** Extract a compliance check value by label from stats. */
export function checkValue(
  stats: { compliance?: { checks: Array<{ label: string; value: number }> } | null } | null,
  label: string,
): number | undefined {
  return stats?.compliance?.checks?.find((c) => c.label === label)?.value
}

/** Map margin_db to a color. Green = compliant, red = exceeded, white = boundary. */
export function marginColor(margin: number): [number, number, number] {
  if (margin >= 0) {
    // Compliant: green, brighter with more margin
    const t = Math.min(margin / 20, 1)
    return [30 + 40 * (1 - t), 160 + 80 * t, 60 + 40 * (1 - t)]
  }
  // Exceeded: red, deeper with larger exceedance
  const t = Math.min(-margin / 20, 1)
  return [180 + 75 * t, 50 * (1 - t), 50 * (1 - t)]
}

/**
 * Format an S_ab value as a pure numeric string (no unit).
 *
 * This differs from `@/lib/format.ts::formatSab` which appends "W/m²".
 * Use this one for histogram bin labels and table cells whose header
 * already carries the unit.
 */
export function formatSabNumber(v: number): string {
  if (v === 0) return '0'
  if (v < 0.01) return v.toExponential(1)
  if (v < 1) return v.toFixed(3)
  if (v < 100) return v.toFixed(2)
  return v.toFixed(1)
}

export function computeHistogram(
  arr: Float32Array,
  nBins: number,
): {
  bins: { x0: number; x1: number; count: number; label: string }[]
  maxCount: number
} {
  // Only histogram positive values (exposed triangles)
  const positive: number[] = []
  for (let i = 0; i < arr.length; i++) {
    if (arr[i] > 0) positive.push(arr[i])
  }
  if (positive.length === 0) return { bins: [], maxCount: 0 }

  // Use log-scale bins for better visualization of power density distributions
  const minVal = Math.min(...positive)
  const maxVal = Math.max(...positive)

  if (minVal === maxVal) {
    return {
      bins: [{ x0: minVal * 0.9, x1: maxVal * 1.1, count: positive.length, label: formatSabNumber(minVal) }],
      maxCount: positive.length,
    }
  }

  const logMin = Math.log10(Math.max(minVal, 1e-12))
  const logMax = Math.log10(maxVal)
  const binWidth = (logMax - logMin) / nBins

  const bins: { x0: number; x1: number; count: number; label: string }[] = []
  for (let i = 0; i < nBins; i++) {
    const x0 = Math.pow(10, logMin + i * binWidth)
    const x1 = Math.pow(10, logMin + (i + 1) * binWidth)
    bins.push({ x0, x1, count: 0, label: formatSabNumber(x0) })
  }

  for (const v of positive) {
    let idx = Math.floor((Math.log10(v) - logMin) / binWidth)
    if (idx < 0) idx = 0
    if (idx >= nBins) idx = nBins - 1
    bins[idx].count++
  }

  const maxCount = Math.max(...bins.map((b) => b.count))
  return { bins, maxCount }
}

// Shared button class names used by sweep section buttons
export const btnClass =
  'text-xs px-3 py-1.5 rounded border border-border transition-colors cursor-pointer hover:bg-muted'
export const btnPrimaryClass =
  'text-xs px-3 py-1.5 rounded border border-primary/40 bg-primary/15 text-primary transition-colors cursor-pointer hover:bg-primary/25'
