import { describe, it, expect } from 'vitest'
import { chartValueForIteration } from '@/components/panels/OptimizePanel'
import type { IterationResult } from '@/stores/optimize'

// Chart label says "Peak S_ab per iteration" but tilt_power's `objective` is a
// signed penalty (−power + λ·violation²) that flips sign and scale. Before this
// fix, the chart plotted the penalty on tilt_power, producing a confusing line
// that could go negative. The helper must return stats.peak_sab when present so
// the chart is a peak-exposure trajectory regardless of mode.
describe('chartValueForIteration', () => {
  it('uses stats.peak_sab when present', () => {
    const h: IterationResult = {
      iter: 1,
      objective: -42,
      params: {},
      stats: { peak_sab: 1.23 },
    }
    expect(chartValueForIteration(h)).toBe(1.23)
  })

  it('falls back to objective when stats is missing', () => {
    const h: IterationResult = { iter: 1, objective: 0.5, params: {} }
    expect(chartValueForIteration(h)).toBe(0.5)
  })

  it('falls back to objective when stats.peak_sab is missing', () => {
    const h: IterationResult = {
      iter: 1,
      objective: 0.8,
      params: {},
      stats: { something_else: 1 },
    }
    expect(chartValueForIteration(h)).toBe(0.8)
  })

  it('falls back to objective when stats.peak_sab is non-finite', () => {
    const h: IterationResult = {
      iter: 1,
      objective: 0.25,
      params: {},
      stats: { peak_sab: Number.NaN },
    }
    expect(chartValueForIteration(h)).toBe(0.25)
  })

  it('falls back to objective when stats.peak_sab is the wrong type', () => {
    const h: IterationResult = {
      iter: 1,
      objective: 0.9,
      params: {},
      stats: { peak_sab: 'oops' as unknown as number },
    }
    expect(chartValueForIteration(h)).toBe(0.9)
  })
})
