import { describe, it, expect } from 'vitest'
import { rayPowerToColorT } from '../scene/studioHelpers'

describe('rayPowerToColorT', () => {
  it('maps the strongest path to the warm end (t = 1)', () => {
    expect(rayPowerToColorT(1, 1)).toBe(1)
    expect(rayPowerToColorT(5, 5)).toBe(1)
  })

  it('maps a ray rangeDb below the peak to the cold end (t = 0)', () => {
    // 40 dB below peak = factor 1e-4 in linear power.
    expect(rayPowerToColorT(1e-4, 1, 40)).toBeCloseTo(0, 6)
  })

  it('places a 20 dB-down ray at the midpoint for a 40 dB range', () => {
    expect(rayPowerToColorT(1e-2, 1, 40)).toBeCloseTo(0.5, 6)
  })

  it('clamps anything fainter than the range to 0 rather than going negative', () => {
    expect(rayPowerToColorT(1e-9, 1, 40)).toBe(0)
    expect(rayPowerToColorT(0, 1, 40)).toBe(0)
  })

  it('is monotonic in power', () => {
    const a = rayPowerToColorT(0.1, 1)
    const b = rayPowerToColorT(0.3, 1)
    const c = rayPowerToColorT(0.9, 1)
    expect(a).toBeLessThan(b)
    expect(b).toBeLessThan(c)
  })

  it('handles a non-positive peak without NaN', () => {
    expect(Number.isFinite(rayPowerToColorT(0, 0))).toBe(true)
    expect(rayPowerToColorT(0, 0)).toBe(0)
  })
})
