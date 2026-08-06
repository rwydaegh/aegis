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

// Perceptually-uniform colormap anchor stops (matplotlib plasma/inferno/magma/
// cividis + Google turbo), evenly spaced t with rgb in 0..255. Eight to nine
// anchors track the luminance ramp closely enough for field visualisation; the
// generic sampleInferno interpolates between them.
function evenStops(rgb: [number, number, number][]): ColorStops {
  return rgb.map(([r, g, b], i) => [i / (rgb.length - 1), r, g, b])
}

export const COLORMAP_STOPS: Record<string, ColorStops> = {
  plasma: evenStops([
    [13, 8, 135], [84, 2, 163], [139, 10, 165], [185, 50, 137],
    [219, 92, 104], [244, 136, 73], [254, 188, 43], [240, 249, 33],
  ]),
  inferno: evenStops([
    [0, 0, 4], [40, 11, 84], [101, 21, 110], [159, 42, 99],
    [212, 72, 66], [245, 125, 21], [250, 193, 39], [252, 255, 164],
  ]),
  magma: evenStops([
    [0, 0, 4], [28, 16, 68], [79, 18, 123], [129, 37, 129], [181, 54, 122],
    [229, 80, 100], [251, 135, 97], [254, 194, 135], [252, 253, 191],
  ]),
  cividis: evenStops([
    [0, 32, 76], [0, 67, 110], [71, 92, 108], [124, 121, 107],
    [178, 150, 90], [238, 184, 52], [253, 231, 55],
  ]),
  turbo: evenStops([
    [48, 18, 59], [50, 123, 252], [26, 228, 182], [133, 249, 57],
    [249, 213, 40], [246, 107, 21], [122, 4, 3],
  ]),
}

/** Sample a registered perceptually-uniform colormap, or null if unknown. [r,g,b] 0..255. */
export function sampleNamedStops(name: string, t: number): [number, number, number] | null {
  const stops = COLORMAP_STOPS[name]
  if (!stops) return null
  const [r, g, b] = sampleInferno(t, stops)
  return [Math.round(r), Math.round(g), Math.round(b)]
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
