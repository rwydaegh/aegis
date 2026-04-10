export type ColorStops = [t: number, r: number, g: number, b: number][]

/** Safe max for large typed arrays (avoids stack overflow from spread). */
export function arrayMax(arr: Float32Array | number[]): number {
  let max = -Infinity
  for (let i = 0; i < arr.length; i++) {
    if (arr[i] > max) max = arr[i]
  }
  return max
}

/** Safe min for large typed arrays. */
export function arrayMin(arr: Float32Array | number[]): number {
  let min = Infinity
  for (let i = 0; i < arr.length; i++) {
    if (arr[i] < min) min = arr[i]
  }
  return min
}

export function sampleInferno(t: number, stops: ColorStops): [number, number, number] {
  t = Math.max(0, Math.min(1, t))
  for (let i = 0; i < stops.length - 1; i++) {
    if (t <= stops[i + 1][0]) {
      const u = (t - stops[i][0]) / (stops[i + 1][0] - stops[i][0])
      return [
        stops[i][1] + u * (stops[i + 1][1] - stops[i][1]),
        stops[i][2] + u * (stops[i + 1][2] - stops[i][2]),
        stops[i][3] + u * (stops[i + 1][3] - stops[i][3]),
      ]
    }
  }
  const last = stops[stops.length - 1]
  return [last[1], last[2], last[3]]
}

export function jetColor(t: number): [number, number, number] {
  t = Math.max(0, Math.min(1, t))
  let r: number, g: number, b: number
  if (t < 0.125) {
    const u = t / 0.125; r = 0; g = 0; b = 0.5 + 0.5 * u
  } else if (t < 0.375) {
    const u = (t - 0.125) / 0.25; r = 0; g = u; b = 1
  } else if (t < 0.625) {
    const u = (t - 0.375) / 0.25; r = u; g = 1; b = 1 - u
  } else if (t < 0.875) {
    const u = (t - 0.625) / 0.25; r = 1; g = 1 - u; b = 0
  } else {
    const u = (t - 0.875) / 0.125; r = 1 - 0.5 * u; g = 0; b = 0
  }
  return [r, g, b]
}

// Viridis colormap: 11 perceptually uniform stops (dark purple -> yellow)
const VIRIDIS: [number, number, number][] = [
  [68, 1, 84], [72, 35, 116], [64, 67, 135], [52, 94, 141],
  [41, 120, 142], [32, 144, 140], [34, 167, 132], [68, 190, 112],
  [121, 209, 81], [189, 222, 38], [253, 231, 37],
]

/** Interpolate the viridis colormap at parameter t in [0, 1]. Returns [r, g, b] in [0, 255]. */
export function viridisColor(t: number): [number, number, number] {
  t = Math.max(0, Math.min(1, t))
  const idx = Math.min(t * (VIRIDIS.length - 1), VIRIDIS.length - 1.001)
  const lo = Math.floor(idx)
  const hi = Math.ceil(idx)
  const f = idx - lo
  return [
    Math.round(VIRIDIS[lo][0] * (1 - f) + VIRIDIS[hi][0] * f),
    Math.round(VIRIDIS[lo][1] * (1 - f) + VIRIDIS[hi][1] * f),
    Math.round(VIRIDIS[lo][2] * (1 - f) + VIRIDIS[hi][2] * f),
  ]
}

/** CSS linear-gradient string for viridis (top = max/yellow, bottom = min/purple). */
export const VIRIDIS_GRADIENT_CSS =
  `linear-gradient(to bottom, ${[...VIRIDIS].reverse().map(([r, g, b]) => `rgb(${r},${g},${b})`).join(', ')})`

/** Log-scale gain mapping with dynamic range. */
export function gainTFromLinear(g: number, gMax: number, dynamicRangeDb: number): number {
  if (gMax <= 0) return 0.5
  const gMin = gMax * Math.pow(10, -dynamicRangeDb / 10)
  const lnMax = Math.log10(Math.max(gMax, gMin * 1.0001))
  const lnMin = Math.log10(gMin)
  const gg = Math.max(g, gMin)
  const t = (Math.log10(gg) - lnMin) / (lnMax - lnMin)
  return Math.max(0, Math.min(1, t))
}
