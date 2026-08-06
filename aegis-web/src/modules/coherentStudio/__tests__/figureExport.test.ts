import { describe, it, expect } from 'vitest'
import { exportLayout, formatTick } from '../figureExport'

describe('exportLayout', () => {
  it('puts the long edge at longEdgePx and preserves the scene aspect (landscape)', () => {
    const { imgW, imgH, gutter, totalW } = exportLayout(1600, 900, 2000, 0)
    expect(imgW).toBe(2000)
    expect(imgH).toBe(Math.round(2000 / (1600 / 900)))
    expect(gutter).toBe(0)
    expect(totalW).toBe(2000)
  })

  it('puts the long edge on height for a portrait scene', () => {
    const { imgW, imgH } = exportLayout(900, 1600, 2000, 0)
    expect(imgH).toBe(2000)
    expect(imgW).toBe(Math.round(2000 * (900 / 1600)))
  })

  it('adds one gutter column of width per colour bar', () => {
    const one = exportLayout(1600, 900, 2000, 1)
    const two = exportLayout(1600, 900, 2000, 2)
    expect(one.gutter).toBeGreaterThan(0)
    expect(one.totalW).toBe(one.imgW + one.gutter)
    expect(two.totalW).toBe(two.imgW + two.gutter * 2)
    // Same scene -> same per-bar gutter width.
    expect(two.gutter).toBe(one.gutter)
  })
})

describe('formatTick', () => {
  it('renders zero plainly', () => {
    expect(formatTick(0)).toBe('0')
  })
  it('uses exponential for tiny and huge magnitudes', () => {
    expect(formatTick(5e-8)).toBe('5.0e-8')
    expect(formatTick(1.2e5)).toBe('1.2e+5')
  })
  it('uses fixed decimals in the human range', () => {
    expect(formatTick(0.047)).toBe('0.05')
    expect(formatTick(3.1)).toBe('3.1')
    expect(formatTick(250)).toBe('250')
  })
  it('returns empty for non-finite input', () => {
    expect(formatTick(NaN)).toBe('')
    expect(formatTick(Infinity)).toBe('')
  })
})
