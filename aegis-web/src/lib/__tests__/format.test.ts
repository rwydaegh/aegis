import { describe, it, expect } from 'vitest'
import { formatSab, formatPower, formatDistance } from '../format'

describe('formatSab', () => {
  it('uses fixed notation for normal values', () => {
    expect(formatSab(2.48)).toBe('2.48 W/m\u00b2')
  })

  it('uses scientific notation for small values', () => {
    expect(formatSab(0.00012)).toBe('1.2e-4 W/m\u00b2')
  })

  it('handles zero', () => {
    expect(formatSab(0)).toBe('0 W/m\u00b2')
  })

  it('handles values at the boundary (exactly 0.01)', () => {
    // 0.01 is NOT < 0.01, so it uses fixed notation
    expect(formatSab(0.01)).toBe('0.01 W/m\u00b2')
  })

  it('handles negative small values', () => {
    const result = formatSab(-0.001)
    expect(result).toContain('e')
    expect(result).toContain('W/m\u00b2')
  })
})

describe('formatPower', () => {
  it('formats milliwatts', () => {
    expect(formatPower(0.23)).toBe('0.23 mW')
  })

  it('uses scientific notation for tiny values', () => {
    const result = formatPower(0.001)
    expect(result).toContain('e')
    expect(result).toContain('mW')
  })

  it('formats whole milliwatts', () => {
    expect(formatPower(1.5)).toBe('1.50 mW')
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
