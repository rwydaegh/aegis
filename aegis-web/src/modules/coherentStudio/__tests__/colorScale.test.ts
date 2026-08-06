import { describe, it, expect } from 'vitest'
import {
  logFloor,
  minMax,
  percentileRange,
  rangeOf,
  resolveScale,
  scaleNormalise,
  unionRange,
  type ScaleInputs,
} from '../scene/colorScale'
import { sampleNamedStops } from '@/lib/colormap'

describe('minMax', () => {
  it('finds the range, skipping non-finite values', () => {
    expect(minMax([3, 1, 2])).toEqual({ vmin: 1, vmax: 3 })
    expect(minMax([NaN, 5, Infinity, -2])).toEqual({ vmin: -2, vmax: 5 })
  })
  it('returns null for an empty array', () => {
    expect(minMax([])).toBeNull()
  })
})

describe('percentileRange', () => {
  it('clips the extremes (a lone hot value does not set vmax)', () => {
    // 1000 ones and a single 1000: p99.5 sits among the ones, not the outlier.
    const vals = [...Array(1000).fill(1), 1000]
    const r = percentileRange(vals, 0.005, 0.995)!
    expect(r.vmax).toBeLessThan(1000)
    expect(r.vmax).toBeCloseTo(1, 0)
  })
  it('interpolates between order statistics', () => {
    const r = percentileRange([0, 10], 0, 1)!
    expect(r).toEqual({ vmin: 0, vmax: 10 })
    expect(percentileRange([0, 10], 0.5, 0.5)!.vmin).toBeCloseTo(5)
  })
})

describe('rangeOf', () => {
  it('uses raw min/max when not robust', () => {
    expect(rangeOf([1, 2, 1000], false)).toEqual({ vmin: 1, vmax: 1000 })
  })
  it('clips the top when robust', () => {
    expect(rangeOf([...Array(100).fill(1), 1000], true)!.vmax).toBeLessThan(1000)
  })
  it('is null for empty / missing data', () => {
    expect(rangeOf(null, false)).toBeNull()
    expect(rangeOf([], true)).toBeNull()
  })
})

describe('unionRange', () => {
  it('covers every input range and ignores nulls', () => {
    expect(unionRange([{ vmin: 1, vmax: 5 }, null, { vmin: -2, vmax: 3 }])).toEqual({ vmin: -2, vmax: 5 })
  })
  it('is null when nothing is present', () => {
    expect(unionRange([null, undefined])).toBeNull()
  })
})

function inputs(over: Partial<ScaleInputs> = {}): ScaleInputs {
  return {
    quantity: 'S',
    mode: 'auto',
    scope: 'surface',
    colormap: 'viridis',
    dynamicRangeDb: 30,
    fixedRange: null,
    surfaceRange: { vmin: 0.001, vmax: 0.05 },
    sharedRange: { vmin: 0, vmax: 0.2 },
    ...over,
  }
}

describe('resolveScale', () => {
  it('pins the linear floor to 0 for a non-signed quantity (surface scope)', () => {
    const s = resolveScale(inputs())
    expect(s).toMatchObject({ colormap: 'viridis', vmin: 0, vmax: 0.05, logMode: false, signed: false })
  })

  it('shared scope uses the union range so colours are comparable across surfaces', () => {
    const s = resolveScale(inputs({ scope: 'shared' }))
    expect(s.vmax).toBe(0.2)
  })

  it('fixed mode uses the locked range verbatim (vmin not pinned to 0)', () => {
    const s = resolveScale(inputs({ mode: 'fixed', fixedRange: { vmin: 0.01, vmax: 0.1 } }))
    expect(s).toMatchObject({ vmin: 0.01, vmax: 0.1 })
  })

  it('fixed mode without a locked range falls back to the surface range', () => {
    const s = resolveScale(inputs({ mode: 'fixed', fixedRange: null }))
    expect(s.vmax).toBe(0.05)
  })

  it('log mode sets logMode and carries the dynamic range', () => {
    const s = resolveScale(inputs({ mode: 'log', dynamicRangeDb: 40 }))
    expect(s.logMode).toBe(true)
    expect(s.dynamicRangeDb).toBe(40)
  })

  it('signed components force the diverging symmetric scale, ignoring scope/mode', () => {
    const s = resolveScale(inputs({ quantity: 'ReEx', mode: 'log', scope: 'shared', surfaceRange: { vmin: -3, vmax: 7 } }))
    expect(s.colormap).toBe('coolwarm')
    expect(s.vmin).toBe(-7)
    expect(s.vmax).toBe(7)
    expect(s.logMode).toBe(false)
    expect(s.signed).toBe(true)
  })

  it('never produces a degenerate vmax', () => {
    const s = resolveScale(inputs({ surfaceRange: { vmin: 0, vmax: 0 } }))
    expect(s.vmax).toBeGreaterThan(0)
  })
})

describe('scaleNormalise', () => {
  const lin = resolveScale(inputs({ surfaceRange: { vmin: 0, vmax: 10 } }))
  it('maps linearly onto [0, 1] and clamps', () => {
    expect(scaleNormalise(0, lin)).toBe(0)
    expect(scaleNormalise(5, lin)).toBeCloseTo(0.5)
    expect(scaleNormalise(10, lin)).toBe(1)
    expect(scaleNormalise(-1, lin)).toBe(0)
    expect(scaleNormalise(99, lin)).toBe(1)
  })

  it('log mode: vmax maps to 1 and the dynamic-range floor maps to 0', () => {
    const s = resolveScale(inputs({ mode: 'log', dynamicRangeDb: 30, surfaceRange: { vmin: 0, vmax: 1 } }))
    expect(scaleNormalise(1, s)).toBeCloseTo(1, 5)
    expect(scaleNormalise(logFloor(s), s)).toBeCloseTo(0, 5)
    // A value one decade below vmax sits at 1 - 10/30 of the window.
    expect(scaleNormalise(0.1, s)).toBeCloseTo(1 - 10 / 30, 5)
  })
})

describe('perceptually-uniform colormaps', () => {
  it('every new colormap resolves to a finite rgb at both ends', () => {
    for (const name of ['plasma', 'inferno', 'magma', 'cividis', 'turbo']) {
      for (const t of [0, 0.5, 1]) {
        const rgb = sampleNamedStops(name, t)!
        expect(rgb).toHaveLength(3)
        rgb.forEach((c) => expect(c).toBeGreaterThanOrEqual(0))
        rgb.forEach((c) => expect(c).toBeLessThanOrEqual(255))
      }
    }
  })
  it('returns null for an unregistered name (caller falls back to viridis)', () => {
    expect(sampleNamedStops('viridis', 0.5)).toBeNull()
    expect(sampleNamedStops('nope', 0.5)).toBeNull()
  })
})
