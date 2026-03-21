import { describe, it, expect } from 'vitest'
import { sampleInferno, jetColor, gainTFromLinear, type ColorStops } from '../colormap'

const TEST_STOPS: ColorStops = [
  [0.0, 0.001, 0.014, 0.071],
  [0.25, 0.341, 0.063, 0.431],
  [0.5, 0.737, 0.216, 0.329],
  [0.75, 0.976, 0.557, 0.035],
  [1.0, 0.988, 1.0, 0.644],
]

describe('sampleInferno', () => {
  it('returns dark color at t=0', () => {
    const [r] = sampleInferno(0, TEST_STOPS)
    expect(r).toBeLessThan(0.1)
  })

  it('returns bright color at t=1', () => {
    const [r] = sampleInferno(1, TEST_STOPS)
    expect(r).toBeGreaterThan(0.9)
  })

  it('clamps t to [0,1]', () => {
    expect(sampleInferno(-1, TEST_STOPS)).toEqual(sampleInferno(0, TEST_STOPS))
    expect(sampleInferno(2, TEST_STOPS)).toEqual(sampleInferno(1, TEST_STOPS))
  })

  it('interpolates midpoint', () => {
    const [r, g, b] = sampleInferno(0.5, TEST_STOPS)
    expect(r).toBeCloseTo(0.737, 2)
    expect(g).toBeCloseTo(0.216, 2)
    expect(b).toBeCloseTo(0.329, 2)
  })

  it('interpolates between stops', () => {
    const [r] = sampleInferno(0.125, TEST_STOPS)
    // midpoint between stop 0 and stop 1: (0.001 + 0.341) / 2
    expect(r).toBeCloseTo((0.001 + 0.341) / 2, 3)
  })
})

describe('jetColor', () => {
  it('returns blue at t=0', () => {
    const [r, g, b] = jetColor(0)
    expect(b).toBeGreaterThan(0.4)
    expect(r).toBe(0)
  })

  it('returns red at t=1', () => {
    const [r, g, b] = jetColor(1)
    expect(r).toBeGreaterThan(0.4)
    expect(b).toBe(0)
  })

  it('is green-dominant at t=0.5', () => {
    // At t=0.5 jet is in the 0.375-0.625 segment: r=0.5, g=1, b=0.5
    const [r, g, b] = jetColor(0.5)
    expect(g).toBeCloseTo(1, 5)
    expect(r).toBeCloseTo(0.5, 5)
    expect(b).toBeCloseTo(0.5, 5)
  })

  it('clamps below 0', () => {
    expect(jetColor(-0.5)).toEqual(jetColor(0))
  })

  it('clamps above 1', () => {
    expect(jetColor(1.5)).toEqual(jetColor(1))
  })
})

describe('gainTFromLinear', () => {
  it('returns 0.5 when gMax <= 0', () => {
    expect(gainTFromLinear(1, 0, 30)).toBe(0.5)
  })

  it('returns 1 at max gain', () => {
    const t = gainTFromLinear(10, 10, 30)
    expect(t).toBeCloseTo(1, 5)
  })

  it('returns 0 at min gain (bottom of dynamic range)', () => {
    const gMax = 10
    const dr = 30
    const gMin = gMax * Math.pow(10, -dr / 10)
    const t = gainTFromLinear(gMin, gMax, dr)
    expect(t).toBeCloseTo(0, 5)
  })

  it('clamps values below dynamic range to 0', () => {
    const t = gainTFromLinear(0, 10, 30)
    expect(t).toBeGreaterThanOrEqual(0)
    expect(t).toBeLessThanOrEqual(0.01)
  })
})
