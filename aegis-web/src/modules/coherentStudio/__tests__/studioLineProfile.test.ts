import { describe, it, expect } from 'vitest'
import { centerLineProfile, type SliceLike } from '../panels/studioLineProfile'

// A 5x5 slice, 0.08 m x 0.08 m, scalar[i, j] row-major (i -> e1, j -> e2).
function slice(fill: (i: number, j: number) => number): SliceLike {
  const n1 = 5
  const n2 = 5
  const scalar = new Float32Array(n1 * n2)
  for (let i = 0; i < n1; i++) for (let j = 0; j < n2; j++) scalar[i * n2 + j] = fill(i, j)
  return { scalar, shape: [n1, n2], world: { extent: [0.08, 0.08] } }
}

describe('centerLineProfile', () => {
  it('samples the centre row for an e1 cut and centre column for e2', () => {
    // Value encodes which row/col it came from: i*10 + j.
    const s = slice((i, j) => i * 10 + j)
    const e1 = centerLineProfile(s, 'e1') // centre column jMid = 2, varies in i
    expect(e1.points.map((p) => p.value)).toEqual([2, 12, 22, 32, 42])
    const e2 = centerLineProfile(s, 'e2') // centre row iMid = 2, varies in j
    expect(e2.points.map((p) => p.value)).toEqual([20, 21, 22, 23, 24])
  })

  it('centres the offset axis on zero spanning the full extent', () => {
    const s = slice(() => 1)
    const e1 = centerLineProfile(s, 'e1')
    expect(e1.points[0].t).toBeCloseTo(-0.04, 6)
    expect(e1.points[2].t).toBeCloseTo(0, 6)
    expect(e1.points[4].t).toBeCloseTo(0.04, 6)
  })

  it('finds the peak offset and value', () => {
    // Peak at i = 3 (offset +0.02) along e1.
    const s = slice((i) => (i === 3 ? 9 : 1))
    const e1 = centerLineProfile(s, 'e1')
    expect(e1.peakValue).toBe(9)
    expect(e1.peakOffset).toBeCloseTo(0.02, 6)
  })

  it('measures a finite FWHM for a peaked cut', () => {
    // Triangular-ish peak at the centre.
    const s = slice((i) => [1, 4, 8, 4, 1][i])
    const e1 = centerLineProfile(s, 'e1')
    expect(e1.fwhm).toBeGreaterThan(0)
    expect(e1.fwhm).toBeLessThanOrEqual(0.08)
  })
})
