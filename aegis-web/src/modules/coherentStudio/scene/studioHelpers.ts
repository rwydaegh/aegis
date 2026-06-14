import { jetColor, viridisColor } from '@/lib/colormap'

// Pure (no THREE, no DOM) helpers for the studio scene. Kept separate from the
// React/Three components so they can be unit tested in the node vitest env.

/**
 * Map a scalar value to an integer index into a colormap LUT of `lutSize` stops.
 *
 * This is the CPU reference for the GLSL normalisation in StudioSlicePlane: the
 * fragment shader performs the identical (vmin, vmax) -> t mapping and then a
 * texture lookup, so the LUT row this returns matches the colour the shader
 * samples. Linear mode is a plain (value - vmin) / (vmax - vmin); log mode uses
 * a log ratio (base independent, so natural log on the GPU matches log10 here).
 */
export function scalarToLutIndex(
  value: number,
  vmin: number,
  vmax: number,
  lutSize: number,
  logMode = false,
): number {
  if (lutSize <= 1) return 0

  let t: number
  if (logMode) {
    const eps = 1e-12
    const lo = Math.log10(Math.max(vmin, eps))
    const hi = Math.log10(Math.max(vmax, Math.max(vmin, eps) * 1.0001))
    if (hi <= lo) return 0
    const v = Math.min(Math.max(value, Math.max(vmin, eps)), Math.max(vmax, eps))
    t = (Math.log10(v) - lo) / (hi - lo)
  } else {
    if (vmax <= vmin) return 0
    t = (value - vmin) / (vmax - vmin)
  }

  t = Math.min(1, Math.max(0, t))
  return Math.round(t * (lutSize - 1))
}

/**
 * Expand a per-triangle scalar array (length nFaces) into a per-vertex array
 * (length nFaces * 3) where the three vertices of each triangle share the
 * triangle's value. Used when a per-vertex consumer is needed; note that
 * BodyMeshInstance instead consumes the per-face array directly.
 */
export function expandTriangleValues(perTri: Float32Array | number[]): Float32Array {
  const n = perTri.length
  const out = new Float32Array(n * 3)
  for (let f = 0; f < n; f++) {
    const v = perTri[f]
    out[f * 3] = v
    out[f * 3 + 1] = v
    out[f * 3 + 2] = v
  }
  return out
}

/**
 * Snap a focus point to the nearest body-surface triangle centroid. Mirrors the
 * backend's `_phantom.snap_focus_to_skin` so the focus marker and beam axis the
 * scene draws agree with the steering focus the slice endpoint actually uses.
 * `centroids` is the flat per-triangle array (length nFaces * 3). Returns the
 * input unchanged when there are no centroids.
 */
export function snapFocusToSkin(
  focus: [number, number, number],
  centroids: Float32Array | null | undefined,
): [number, number, number] {
  if (!centroids || centroids.length < 3) return focus
  const [fx, fy, fz] = focus
  let best = 0
  let bestD2 = Infinity
  for (let i = 0; i < centroids.length; i += 3) {
    const dx = centroids[i] - fx
    const dy = centroids[i + 1] - fy
    const dz = centroids[i + 2] - fz
    const d2 = dx * dx + dy * dy + dz * dz
    if (d2 < bestD2) {
      bestD2 = d2
      best = i
    }
  }
  return [centroids[best], centroids[best + 1], centroids[best + 2]]
}

/** Colormap lookup returning [r, g, b] in 0..255 for a normalised t in [0, 1]. */
export function colormapRgb(name: string, t: number): [number, number, number] {
  if (name === 'jet') {
    const [r, g, b] = jetColor(t)
    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)]
  }
  // Viridis is the default and the fallback for any unknown name.
  return viridisColor(t)
}
