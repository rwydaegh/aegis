import { describe, it, expect } from 'vitest'
import { compareMaps } from '../panels/studioCompare'

describe('compareMaps', () => {
  it('returns null for mismatched or empty lengths', () => {
    expect(compareMaps([], [])).toBeNull()
    expect(compareMaps([1, 2], [1])).toBeNull()
  })

  it('computes a signed delta B - A and counts reductions', () => {
    const a = [2, 2, 2, 2]
    const b = [1, 1, 3, 2] // two reduced, one increased, one equal
    const s = compareMaps(a, b)!
    expect(Array.from(s.delta)).toEqual([-1, -1, 1, 0])
    expect(s.reducedFrac).toBe(0.5)
    expect(s.maxAbsDelta).toBe(1)
  })

  it('reports a negative percent change when B is uniformly lower', () => {
    const a = [10, 20, 30, 40]
    const b = a.map((v) => v * 0.5)
    const s = compareMaps(a, b)!
    expect(s.meanPct).toBeCloseTo(-50, 6)
    expect(s.peakPct).toBeCloseTo(-50, 6)
    expect(s.peakA).toBe(40)
    expect(s.peakB).toBe(20)
  })

  it('handles an all-zero reference without NaN in the percent change', () => {
    const s = compareMaps([0, 0], [0, 0])!
    expect(s.meanPct).toBe(0)
  })
})
