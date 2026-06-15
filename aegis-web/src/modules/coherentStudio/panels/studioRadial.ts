// Pure, testable core of the radial falloff curve: how the reconstructed field
// decays with distance from the focal hotspot. A faithful port of the paper
// fork's plot_radial_probability_density_function, computed client-side from the
// field-volume grid already in the store. We bin every voxel by its distance to
// the field peak (which coincides with the steered focus for a focused beam) and
// report the median and inter-quartile band per shell, plus a "reliable radius"
// beyond which the cubic sample box no longer fully surrounds the focus and the
// statistics are biased by missing corners.

export type Vec3 = [number, number, number]

export interface VolumeGrid {
  scalar: ArrayLike<number>
  /** [nx, ny, nz], scalar is row-major [i, j, k] (i->x, j->y, k->z). */
  shape: [number, number, number]
  /** Min-corner voxel centre, server Z-up metres. */
  origin: Vec3
  /** Isotropic voxel pitch, metres. */
  spacing: number
}

export interface RadialBin {
  /** Shell centre radius, metres. */
  r: number
  median: number
  p25: number
  p75: number
  /** p75 - p25, precomputed for the stacked-area band hack in recharts. */
  band: number
  count: number
}

export interface RadialProfile {
  bins: RadialBin[]
  /** Largest radius fully enclosed by the sample box; stats beyond it are biased. */
  reliableRadius: number
  /** Distance from the focus to the farthest sampled voxel, metres. */
  maxRadius: number
}

function quantileSorted(sorted: number[], frac: number): number {
  if (sorted.length === 0) return 0
  const idx = Math.min(1, Math.max(0, frac)) * (sorted.length - 1)
  const lo = Math.floor(idx)
  const hi = Math.ceil(idx)
  if (lo === hi) return sorted[lo]
  return sorted[lo] + (idx - lo) * (sorted[hi] - sorted[lo])
}

/**
 * Distance from `focus` to the nearest face of the box of voxel centres. The
 * largest sphere centred at the focus that stays inside the sampled region; out
 * past it some shells are only partly sampled, so their statistics are biased.
 * Zero (clamped) when the focus sits outside the box.
 */
export function reliableRadius(grid: VolumeGrid, focus: Vec3): number {
  const [nx, ny, nz] = grid.shape
  const n: [number, number, number] = [nx, ny, nz]
  let r = Infinity
  for (let a = 0; a < 3; a++) {
    const lo = grid.origin[a]
    const hi = grid.origin[a] + (n[a] - 1) * grid.spacing
    r = Math.min(r, focus[a] - lo, hi - focus[a])
  }
  return Math.max(0, r)
}

/**
 * Bin the volume voxels by distance from `focus` and return the median and
 * inter-quartile band per shell. `nBins` shells span 0..maxRadius. Empty shells
 * are dropped. Pass the field peak (volumeResult.peakXyz) as the focus so the
 * curve measures falloff from the actual hotspot.
 */
export function radialProfile(grid: VolumeGrid, focus: Vec3, nBins = 30): RadialProfile {
  const [nx, ny, nz] = grid.shape
  const { origin, spacing, scalar } = grid
  // First pass: per-voxel radius and the max, to size the bins.
  const radii = new Float64Array(nx * ny * nz)
  let maxRadius = 0
  let idx = 0
  for (let i = 0; i < nx; i++) {
    const dx = origin[0] + i * spacing - focus[0]
    for (let j = 0; j < ny; j++) {
      const dy = origin[1] + j * spacing - focus[1]
      for (let k = 0; k < nz; k++) {
        const dz = origin[2] + k * spacing - focus[2]
        const r = Math.sqrt(dx * dx + dy * dy + dz * dz)
        radii[idx] = r
        if (r > maxRadius) maxRadius = r
        idx++
      }
    }
  }
  const rad = reliableRadius(grid, focus)
  if (maxRadius <= 0 || nBins < 1) {
    return { bins: [], reliableRadius: rad, maxRadius }
  }

  const buckets: number[][] = Array.from({ length: nBins }, () => [])
  const dr = maxRadius / nBins
  for (let p = 0; p < radii.length; p++) {
    const v = scalar[p]
    if (!Number.isFinite(v)) continue
    let b = Math.floor(radii[p] / dr)
    if (b >= nBins) b = nBins - 1
    buckets[b].push(v)
  }

  const bins: RadialBin[] = []
  for (let b = 0; b < nBins; b++) {
    const vals = buckets[b]
    if (vals.length === 0) continue
    vals.sort((a, c) => a - c)
    const p25 = quantileSorted(vals, 0.25)
    const p75 = quantileSorted(vals, 0.75)
    bins.push({
      r: (b + 0.5) * dr,
      median: quantileSorted(vals, 0.5),
      p25,
      p75,
      band: p75 - p25,
      count: vals.length,
    })
  }
  return { bins, reliableRadius: rad, maxRadius }
}
