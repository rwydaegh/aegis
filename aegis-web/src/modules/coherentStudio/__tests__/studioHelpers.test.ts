import { describe, it, expect } from 'vitest'
import {
  scalarToLutIndex,
  expandTriangleValues,
  snapFocusToSkin,
  coolwarmColor,
  isSignedQuantity,
  resolveSliceDisplay,
  rayWidth,
  rayOpacity,
  rayHeadScale,
} from '../scene/studioHelpers'

describe('scalarToLutIndex', () => {
  const N = 256

  it('linear: vmin maps to index 0', () => {
    expect(scalarToLutIndex(2, 2, 10, N, false)).toBe(0)
  })

  it('linear: vmax maps to the last index', () => {
    expect(scalarToLutIndex(10, 2, 10, N, false)).toBe(N - 1)
  })

  it('linear: midpoint maps to the middle of the LUT', () => {
    const mid = scalarToLutIndex(6, 2, 10, N, false)
    expect(Math.abs(mid - (N - 1) / 2)).toBeLessThanOrEqual(1)
  })

  it('linear: clamps below vmin and above vmax', () => {
    expect(scalarToLutIndex(-5, 2, 10, N, false)).toBe(0)
    expect(scalarToLutIndex(100, 2, 10, N, false)).toBe(N - 1)
  })

  it('log: endpoints map to 0 and last index', () => {
    expect(scalarToLutIndex(1, 1, 1000, N, true)).toBe(0)
    expect(scalarToLutIndex(1000, 1, 1000, N, true)).toBe(N - 1)
  })

  it('log: is monotonically non-decreasing across the range', () => {
    let prev = -1
    for (let v = 1; v <= 1000; v += 7) {
      const idx = scalarToLutIndex(v, 1, 1000, N, true)
      expect(idx).toBeGreaterThanOrEqual(prev)
      prev = idx
    }
  })

  it('log: midpoint in log space sits near the LUT middle', () => {
    // Geometric mean of [1, 1000] is ~31.6; in log space that is the midpoint.
    const idx = scalarToLutIndex(Math.sqrt(1000), 1, 1000, N, true)
    expect(Math.abs(idx - (N - 1) / 2)).toBeLessThanOrEqual(1)
  })

  it('degenerate range returns index 0', () => {
    expect(scalarToLutIndex(5, 5, 5, N, false)).toBe(0)
    expect(scalarToLutIndex(5, 5, 5, N, true)).toBe(0)
  })
})

describe('expandTriangleValues', () => {
  it('expands per-triangle (8000) to per-vertex (24000)', () => {
    const perTri = new Float32Array(8000)
    for (let i = 0; i < 8000; i++) perTri[i] = i * 0.5
    const out = expandTriangleValues(perTri)
    expect(out.length).toBe(24000)
  })

  it('each triangle contributes three equal vertex values', () => {
    const perTri = [3, 7, 11, 13]
    const out = expandTriangleValues(perTri)
    expect(out.length).toBe(12)
    for (let f = 0; f < perTri.length; f++) {
      expect(out[f * 3]).toBe(perTri[f])
      expect(out[f * 3 + 1]).toBe(perTri[f])
      expect(out[f * 3 + 2]).toBe(perTri[f])
    }
  })
})

describe('snapFocusToSkin', () => {
  // Three centroids; the focus should land on the nearest one.
  const centroids = new Float32Array([0, 0, 0, 1, 0, 0, 0, 2, 0])

  it('snaps to the nearest centroid', () => {
    expect(snapFocusToSkin([0.9, 0.1, 0], centroids)).toEqual([1, 0, 0])
    expect(snapFocusToSkin([0.1, 1.9, 0], centroids)).toEqual([0, 2, 0])
  })

  it('returns the focus unchanged when there are no centroids', () => {
    expect(snapFocusToSkin([3, 3, 3], null)).toEqual([3, 3, 3])
    expect(snapFocusToSkin([3, 3, 3], new Float32Array([]))).toEqual([3, 3, 3])
  })
})

describe('coolwarmColor', () => {
  it('is blue at 0, near-neutral at 0.5, red at 1', () => {
    const lo = coolwarmColor(0)
    const mid = coolwarmColor(0.5)
    const hi = coolwarmColor(1)
    expect(lo[2]).toBeGreaterThan(lo[0]) // blue dominates at the low end
    expect(hi[0]).toBeGreaterThan(hi[2]) // red dominates at the high end
    expect(mid[0]).toBeGreaterThan(180) // light neutral centre
    expect(mid[1]).toBeGreaterThan(180)
  })

  it('clamps out-of-range t', () => {
    expect(coolwarmColor(-1)).toEqual(coolwarmColor(0))
    expect(coolwarmColor(2)).toEqual(coolwarmColor(1))
  })
})

describe('ray power -> visual encodings', () => {
  it('rayWidth: strong rays are far bolder than weak ones, and scale with thickness', () => {
    expect(rayWidth(1)).toBeGreaterThan(rayWidth(0) * 5) // strong/weak contrast is large
    expect(rayWidth(0.5, 2)).toBeCloseTo(2 * rayWidth(0.5, 1)) // thickness is a linear multiplier
    expect(rayWidth(1)).toBeGreaterThan(rayWidth(0.5)) // monotonic in power
  })

  it('rayWidth: clamps out-of-range t', () => {
    expect(rayWidth(-1)).toBe(rayWidth(0))
    expect(rayWidth(2)).toBe(rayWidth(1))
  })

  it('rayOpacity: faint paths recede but stay visible, strong paths near-solid', () => {
    expect(rayOpacity(0)).toBeGreaterThan(0.2)
    expect(rayOpacity(0)).toBeLessThan(rayOpacity(1))
    expect(rayOpacity(1)).toBeLessThanOrEqual(1)
  })

  it('rayHeadScale: weak heads shrink but never vanish', () => {
    expect(rayHeadScale(0)).toBeGreaterThan(0)
    expect(rayHeadScale(1)).toBeGreaterThan(rayHeadScale(0))
  })
})

describe('isSignedQuantity', () => {
  it('flags the real field components', () => {
    expect(isSignedQuantity('ReEx')).toBe(true)
    expect(isSignedQuantity('ReEy')).toBe(true)
    expect(isSignedQuantity('ReEz')).toBe(true)
  })
  it('does not flag magnitude quantities', () => {
    expect(isSignedQuantity('S')).toBe(false)
    expect(isSignedQuantity('absE')).toBe(false)
    expect(isSignedQuantity('poynting')).toBe(false)
  })
})

describe('resolveSliceDisplay', () => {
  it('keeps the user scale for magnitude quantities', () => {
    const d = resolveSliceDisplay({ quantity: 'S', vmin: 2, vmax: 10, colormap: 'jet', logMode: true })
    expect(d).toEqual({ colormap: 'jet', vmin: 2, vmax: 10, logMode: true })
  })

  it('forces a symmetric diverging scale for signed components', () => {
    const d = resolveSliceDisplay({ quantity: 'ReEx', vmin: -3, vmax: 7, colormap: 'viridis', logMode: true })
    expect(d.colormap).toBe('coolwarm')
    expect(d.vmin).toBe(-7)
    expect(d.vmax).toBe(7)
    expect(d.logMode).toBe(false) // signed has no log scale
  })

  it('falls back to a unit range when the slice is flat', () => {
    const d = resolveSliceDisplay({ quantity: 'ReEz', vmin: 0, vmax: 0, colormap: 'viridis', logMode: false })
    expect(d.vmin).toBe(-1)
    expect(d.vmax).toBe(1)
  })
})
