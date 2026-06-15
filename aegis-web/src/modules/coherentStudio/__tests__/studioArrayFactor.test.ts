import { describe, it, expect } from 'vitest'
import { arrayFactorCut } from '../panels/studioArrayFactor'

describe('arrayFactorCut', () => {
  it('peaks at boresight (0 dB) and is symmetric', () => {
    const cut = arrayFactorCut(16, 0.5, 361, false)
    const mid = cut.points[(cut.points.length - 1) / 2]
    expect(mid.angleDeg).toBe(0)
    expect(mid.db).toBeCloseTo(0, 6)
    // Symmetry: +30 deg matches -30 deg.
    const at = (deg: number) => cut.points.find((p) => Math.abs(p.angleDeg - deg) < 1e-6)!.db
    expect(at(30)).toBeCloseTo(at(-30), 6)
  })

  it('narrows the main beam as the array grows', () => {
    const small = arrayFactorCut(8, 0.5, 721, false)
    const big = arrayFactorCut(32, 0.5, 721, false)
    expect(big.hpbwDeg).toBeLessThan(small.hpbwDeg)
  })

  it('matches the broadside HPBW rule of thumb for a uniform array', () => {
    // HPBW ~ 0.886 * lambda / (N d) radians for a uniform broadside array.
    const n = 16
    const d = 0.5
    const cut = arrayFactorCut(n, d, 1441, false)
    const expectedDeg = (0.886 / (n * d)) * (180 / Math.PI)
    expect(cut.hpbwDeg).toBeGreaterThan(expectedDeg * 0.8)
    expect(cut.hpbwDeg).toBeLessThan(expectedDeg * 1.2)
  })

  it('finds a first sidelobe near -13 dB for a uniform array', () => {
    const cut = arrayFactorCut(16, 0.5, 1441, false)
    expect(cut.sidelobeDb).toBeLessThan(-10)
    expect(cut.sidelobeDb).toBeGreaterThan(-16)
  })

  it('clamps to the dB floor and never exceeds 0 dB', () => {
    const cut = arrayFactorCut(16, 0.5, 361, true, -35)
    for (const p of cut.points) {
      expect(p.db).toBeGreaterThanOrEqual(-35)
      expect(p.db).toBeLessThanOrEqual(1e-6)
    }
  })
})
