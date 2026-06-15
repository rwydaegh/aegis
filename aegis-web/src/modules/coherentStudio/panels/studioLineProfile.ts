// Pure core of the slice line-probe: a 1D cut of the field along the horizontal
// (e1) or vertical (e2) centre line of the slice plane. The slice scalar ships
// row-major as scalar[i, j] with i indexing e1 (plane local x) and j indexing e2
// (local y); world.extent is [width along e1, height along e2] in metres. The cut
// is centred so offset 0 is the plane centre.

export type CutAxis = 'e1' | 'e2'

export interface SliceLike {
  scalar: ArrayLike<number>
  /** [n1, n2]: n1 samples along e1, n2 along e2. */
  shape: [number, number]
  world: { extent: [number, number] }
}

export interface ProfilePoint {
  /** Signed offset from the plane centre along the cut axis, metres. */
  t: number
  value: number
}

export interface LineProfile {
  points: ProfilePoint[]
  /** Offset of the largest value along the cut, metres. */
  peakOffset: number
  peakValue: number
  /** Full-width at half maximum of the cut, metres (NaN if it never halves). */
  fwhm: number
}

function centredOffsets(n: number, extent: number): number[] {
  if (n <= 1) return [0]
  const out = new Array<number>(n)
  for (let i = 0; i < n; i++) out[i] = (i / (n - 1) - 0.5) * extent
  return out
}

/** Full-width at half maximum of a sampled curve about its peak, metres. */
function fwhmOf(points: ProfilePoint[], peakIdx: number, peakValue: number): number {
  if (points.length < 2 || peakValue <= 0) return NaN
  const half = 0.5 * peakValue
  const cross = (a: ProfilePoint, b: ProfilePoint): number => {
    const denom = b.value - a.value
    if (Math.abs(denom) < 1e-30) return a.t
    return a.t + ((half - a.value) / denom) * (b.t - a.t)
  }
  let left = NaN
  for (let i = peakIdx; i > 0; i--) {
    if (points[i - 1].value <= half) {
      left = cross(points[i - 1], points[i])
      break
    }
  }
  let right = NaN
  for (let i = peakIdx; i < points.length - 1; i++) {
    if (points[i + 1].value <= half) {
      right = cross(points[i + 1], points[i])
      break
    }
  }
  // Require a genuine half-crossing on both flanks; otherwise the focal spot is
  // wider than the slice window and the width is undefined (reported as --).
  if (!isFinite(left) || !isFinite(right)) return NaN
  const w = right - left
  return w > 0 ? w : NaN
}

/**
 * Extract the centre-line cut of the slice along `axis`. 'e1' is the horizontal
 * cut (centre row, j = n2/2); 'e2' is the vertical cut (centre column, i = n1/2).
 */
export function centerLineProfile(slice: SliceLike, axis: CutAxis): LineProfile {
  const [n1, n2] = slice.shape
  const s = slice.scalar
  const points: ProfilePoint[] = []
  if (axis === 'e1') {
    const jMid = Math.floor((n2 - 1) / 2)
    const offsets = centredOffsets(n1, slice.world.extent[0])
    for (let i = 0; i < n1; i++) points.push({ t: offsets[i], value: s[i * n2 + jMid] })
  } else {
    const iMid = Math.floor((n1 - 1) / 2)
    const offsets = centredOffsets(n2, slice.world.extent[1])
    for (let j = 0; j < n2; j++) points.push({ t: offsets[j], value: s[iMid * n2 + j] })
  }

  let peakIdx = 0
  let peakValue = -Infinity
  for (let i = 0; i < points.length; i++) {
    if (Number.isFinite(points[i].value) && points[i].value > peakValue) {
      peakValue = points[i].value
      peakIdx = i
    }
  }
  if (peakValue === -Infinity) peakValue = 0
  return {
    points,
    peakOffset: points.length ? points[peakIdx].t : 0,
    peakValue,
    fwhm: fwhmOf(points, peakIdx, peakValue),
  }
}
