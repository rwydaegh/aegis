import { describe, it, expect } from 'vitest'
import { scalarToLutIndex, expandTriangleValues, snapFocusToSkin } from '../scene/studioHelpers'

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
