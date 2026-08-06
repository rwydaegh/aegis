import { describe, it, expect } from 'vitest'
import { withCdf, fractionAbove, type HistBin } from '../panels/studioDistribution'

const bins: HistBin[] = [
  { x0: 0, x1: 1, count: 2, label: 'a' },
  { x0: 1, x1: 2, count: 6, label: 'b' },
  { x0: 2, x1: 3, count: 2, label: 'c' },
]

describe('withCdf', () => {
  it('produces a monotone cumulative fraction ending at 1', () => {
    const d = withCdf(bins)
    expect(d.map((p) => p.cdf)).toEqual([0.2, 0.8, 1])
    expect(d[d.length - 1].cdf).toBe(1)
  })
  it('sets the bin centre', () => {
    expect(withCdf(bins)[1].center).toBe(1.5)
  })
  it('handles an all-zero histogram without dividing by zero', () => {
    const z = withCdf([{ x0: 0, x1: 1, count: 0, label: 'a' }])
    expect(z[0].cdf).toBe(0)
  })
})

describe('fractionAbove', () => {
  it('counts the fraction strictly above the threshold', () => {
    expect(fractionAbove([1, 2, 3, 4], 2)).toBe(0.5)
    expect(fractionAbove([1, 1, 1], 5)).toBe(0)
    expect(fractionAbove([], 0)).toBe(0)
  })
})
