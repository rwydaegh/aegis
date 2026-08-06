import { describe, it, expect } from 'vitest'
import { rxGain, rxPeakGain } from '../panels/studioRxPattern'

describe('rxGain', () => {
  it('isotropic and vertical are unit-gain spheres', () => {
    for (const kind of ['isotropic', 'vertical']) {
      expect(rxGain(kind, 0, 0, 1)).toBe(1)
      expect(rxGain(kind, 1, 0, 0)).toBe(1)
      expect(rxGain(kind, 0.5, 0.5, Math.SQRT1_2)).toBe(1)
    }
  })

  it('dipole is a donut: nulls along the axis, peak broadside', () => {
    // Axis is +z, so endfire (kz = +/-1) is the null and broadside (kz = 0) the peak.
    expect(rxGain('dipole', 0, 0, 1)).toBe(0)
    expect(rxGain('dipole', 0, 0, -1)).toBe(0)
    expect(rxGain('dipole', 1, 0, 0)).toBeCloseTo(1, 12)
    expect(rxGain('dipole', 0, 1, 0)).toBeCloseTo(1, 12)
  })

  it('dipole is azimuthally symmetric about the axis', () => {
    // Same polar angle (kz) at different azimuths gives the same gain.
    const a = rxGain('dipole', Math.cos(0.3), Math.sin(0.3), 0)
    const b = rxGain('dipole', Math.cos(1.1), Math.sin(1.1), 0)
    expect(a).toBeCloseTo(b, 12)
  })

  it('dipole falls off monotonically from broadside toward the axis', () => {
    // theta measured from +z; sweep cos(theta) = kz from 0 (broadside) to ~1 (axis).
    let prev = rxGain('dipole', 1, 0, 0)
    for (const kz of [0.2, 0.4, 0.6, 0.8, 0.95]) {
      const kx = Math.sqrt(1 - kz * kz)
      const g = rxGain('dipole', kx, 0, kz)
      expect(g).toBeLessThan(prev)
      prev = g
    }
  })

  it('patch is a forward cos^4 lobe with a dead back hemisphere', () => {
    expect(rxGain('patch', 0, 0, 1)).toBeCloseTo(1, 12) // boresight +z
    expect(rxGain('patch', 0, 0, -1)).toBe(0) // back
    expect(rxGain('patch', 1, 0, 0)).toBe(0) // horizon
    // cos^4 at 45 deg from boresight: kz = cos(45) -> (1/sqrt2)^4 = 1/4.
    expect(rxGain('patch', Math.SQRT1_2, 0, Math.SQRT1_2)).toBeCloseTo(0.25, 12)
  })

  it('every kind peaks at gain 1', () => {
    for (const kind of ['isotropic', 'vertical', 'dipole', 'patch']) {
      expect(rxPeakGain(kind)).toBeCloseTo(1, 12)
    }
  })

  it('unknown kind degrades to an isotropic sphere', () => {
    expect(rxGain('mystery', 0.3, 0.4, Math.sqrt(1 - 0.25))).toBe(1)
  })
})
