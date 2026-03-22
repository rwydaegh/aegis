import { describe, it, expect } from 'vitest'
import { formatSab, formatPower, formatDistance } from '../format'

describe('formatSab', () => {
  it('uses fixed notation for normal values', () => {
    expect(formatSab(2.48)).toBe('2.48 W/m\u00b2')
  })

  it('uses mW/m\u00b2 for small values', () => {
    expect(formatSab(0.01)).toBe('10.00 mW/m\u00b2')
    expect(formatSab(0.00012)).toBe('0.12 mW/m\u00b2')
  })

  it('uses scientific notation for very small values', () => {
    expect(formatSab(0.00005)).toBe('5.00e-5 W/m\u00b2')
  })

  it('handles zero', () => {
    expect(formatSab(0)).toBe('0 W/m\u00b2')
  })

  it('handles boundary at 0.1', () => {
    expect(formatSab(0.1)).toBe('0.10 W/m\u00b2')
  })
})

describe('formatPower', () => {
  it('formats milliwatts', () => {
    expect(formatPower(0.23)).toBe('0.23 mW')
  })

  it('uses microwatts for small values', () => {
    expect(formatPower(0.001)).toBe('1.00 \u00b5W')
    expect(formatPower(0.01)).toBe('10.00 \u00b5W')
  })

  it('uses nanowatts for very small values', () => {
    expect(formatPower(0.000001)).toBe('1.00 nW')
  })

  it('uses scientific notation for extremely small values', () => {
    const result = formatPower(1e-9)
    expect(result).toContain('e')
    expect(result).toContain('mW')
  })

  it('formats whole milliwatts', () => {
    expect(formatPower(1.5)).toBe('1.50 mW')
  })

  it('handles zero', () => {
    expect(formatPower(0)).toBe('0 mW')
  })
})

describe('formatDistance', () => {
  it('formats meters to 1 decimal', () => {
    expect(formatDistance(3.21)).toBe('3.2 m')
  })

  it('rounds correctly', () => {
    // 2.16 unambiguously rounds to 2.2
    expect(formatDistance(2.16)).toBe('2.2 m')
  })

  it('handles zero', () => {
    expect(formatDistance(0)).toBe('0.0 m')
  })
})
