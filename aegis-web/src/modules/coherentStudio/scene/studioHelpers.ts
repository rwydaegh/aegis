import { jetColor, sampleNamedStops, viridisColor } from '@/lib/colormap'

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
 * Map a ray's linear power to a colormap parameter t in [0, 1] on a dB scale
 * relative to the strongest path. The strongest ray (power == pMax) maps to
 * t = 1 (the warm/high end of the colormap); a ray `rangeDb` below the peak
 * maps to t = 0. A plain linear power map collapses everything but the few
 * dominant paths to the cold end, so the dB spread is what makes the weaker
 * arrivals legible. Power is clamped to a tiny floor so a zero-power ray is
 * well defined rather than -infinity.
 */
export function rayPowerToColorT(power: number, pMax: number, rangeDb = 40): number {
  if (rangeDb <= 0) return 0
  const peak = pMax > 0 ? pMax : 1
  const pdb = 10 * Math.log10(Math.max(power, 1e-30) / peak)
  const t = 1 + pdb / rangeDb
  return Math.min(1, Math.max(0, t))
}

/**
 * Map a ray's normalised power t (0 = faintest, 1 = strongest path) to a
 * screen-space line width. Quadratic so the strong arrivals read as bold trunks
 * while the weak ones taper to hairlines; `thickness` is the user multiplier on
 * top, so the strong / weak contrast is what lets the eye pick out what is
 * actually impinging hardest.
 */
export function rayWidth(t: number, thickness = 1): number {
  const x = Math.min(1, Math.max(0, t))
  return thickness * (0.5 + 6 * x * x)
}

/** Per-ray opacity from normalised power: faint paths recede, strong ones stay solid. */
export function rayOpacity(t: number): number {
  const x = Math.min(1, Math.max(0, t))
  return 0.28 + 0.62 * x
}

/** Arrowhead size multiplier from normalised power; weak heads shrink but never vanish. */
export function rayHeadScale(t: number): number {
  const x = Math.min(1, Math.max(0, t))
  return 0.55 + 0.95 * x
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

// Diverging coolwarm control points (blue -> near-white -> red), the standard
// choice for signed fields where zero must read as the neutral centre.
const COOLWARM_STOPS: [number, number, number][] = [
  [59, 76, 192],
  [221, 221, 221],
  [180, 4, 38],
]

/** Diverging coolwarm ramp; t in [0, 1] with 0.5 the neutral centre. [r,g,b] 0..255. */
export function coolwarmColor(t: number): [number, number, number] {
  const x = Math.min(1, Math.max(0, t))
  const [a, b] = x < 0.5 ? [COOLWARM_STOPS[0], COOLWARM_STOPS[1]] : [COOLWARM_STOPS[1], COOLWARM_STOPS[2]]
  const f = x < 0.5 ? x / 0.5 : (x - 0.5) / 0.5
  return [
    Math.round(a[0] + (b[0] - a[0]) * f),
    Math.round(a[1] + (b[1] - a[1]) * f),
    Math.round(a[2] + (b[2] - a[2]) * f),
  ]
}

/** Colormap lookup returning [r, g, b] in 0..255 for a normalised t in [0, 1]. */
export function colormapRgb(name: string, t: number): [number, number, number] {
  if (name === 'jet') {
    const [r, g, b] = jetColor(t)
    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)]
  }
  if (name === 'coolwarm') return coolwarmColor(t)
  // Perceptually-uniform family (plasma / inferno / magma / cividis / turbo).
  const named = sampleNamedStops(name, t)
  if (named) return named
  // Viridis is the default and the fallback for any unknown name.
  return viridisColor(t)
}

/** The signed field components, which read best on a diverging map centred at zero. */
export function isSignedQuantity(quantity: string): boolean {
  return quantity === 'ReEx' || quantity === 'ReEy' || quantity === 'ReEz'
}

/** Symmetric range [-m, m] (m = max|vmin|,|vmax|, never 0) for a signed field. */
export function signedSymmetricRange(vmin: number, vmax: number): { vmin: number; vmax: number } {
  const m = Math.max(Math.abs(vmin), Math.abs(vmax)) || 1
  return { vmin: -m, vmax: m }
}

export interface SliceDisplay {
  colormap: string
  vmin: number
  vmax: number
  logMode: boolean
}

/**
 * Resolve the colour-scale a slice should render with. Signed quantities
 * (ReEx/y/z) get a diverging coolwarm map over a symmetric range so zero lands
 * on the neutral centre (and log mode is forced off, since a signed field has
 * no log scale); everything else keeps the user's colormap and scale mode.
 */
export function resolveSliceDisplay(args: {
  quantity: string
  vmin: number
  vmax: number
  colormap: string
  logMode: boolean
}): SliceDisplay {
  const { quantity, vmin, vmax, colormap, logMode } = args
  if (!isSignedQuantity(quantity)) return { colormap, vmin, vmax, logMode }
  const sym = signedSymmetricRange(vmin, vmax)
  return { colormap: 'coolwarm', vmin: sym.vmin, vmax: sym.vmax, logMode: false }
}
