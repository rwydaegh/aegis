import { describe, it, expect, beforeEach } from 'vitest'
import { handleDoneEvent, handleIterationEvent } from '@/hooks/useOptimization'
import { useOptimizeStore } from '@/stores/optimize'
import type { SSEEvent } from '@/api/optimize'

// Summary-text shape is user-facing. Before this test existed, tilt_power
// reported "% reduction" of a signed penalty (could be negative or >100%),
// which was nonsense. Lock in mode-specific formatting.

function resetOptimizeStore() {
  useOptimizeStore.setState({
    mode: null,
    running: false,
    currentIter: 0,
    history: [],
    summary: null,
    placementCenter: null,
    playbackIter: null,
  })
}

function emptyPeaks() {
  return { firstPeak: null, lastPeak: null, firstSab: null, lastSab: null, lastParams: null }
}

describe('handleDoneEvent summary', () => {
  beforeEach(resetOptimizeStore)

  it('placement uses percent-reduction of objective (peak SAB)', () => {
    let peaks = emptyPeaks()
    peaks = handleIterationEvent(
      { iter: 1, objective: 0.1, params: {}, stats: { peak_sab: 0.1 } } as SSEEvent,
      peaks,
    )
    peaks = handleIterationEvent(
      { iter: 2, objective: 0.04, params: {}, stats: { peak_sab: 0.04 } } as SSEEvent,
      peaks,
    )
    handleDoneEvent(
      { done: true, reason: 'grid_done', total_iters: 2 } as SSEEvent,
      peaks,
      'placement',
    )
    const summary = useOptimizeStore.getState().summary ?? ''
    expect(summary).toMatch(/grid_done after 2 iterations/)
    expect(summary).toMatch(/60% reduction/)
  })

  it('mimo_peak uses percent-reduction of objective', () => {
    let peaks = emptyPeaks()
    peaks = handleIterationEvent({ iter: 1, objective: 2.0, params: {} } as SSEEvent, peaks)
    peaks = handleIterationEvent({ iter: 2, objective: 1.0, params: {} } as SSEEvent, peaks)
    handleDoneEvent(
      { done: true, reason: 'converged', total_iters: 2 } as SSEEvent,
      peaks,
      'mimo_peak',
    )
    expect(useOptimizeStore.getState().summary).toMatch(/50% reduction/)
  })

  it('tilt_power reports final tilt, power, peak — not a reduction percent', () => {
    let peaks = emptyPeaks()
    // Objective is −power + λ·violation²; can go negative and flip sign.
    peaks = handleIterationEvent(
      {
        iter: 1,
        objective: -40,
        params: { tilt_deg: 0, power_dbm: 40 },
        stats: { peak_sab: 2.5 },
      } as SSEEvent,
      peaks,
    )
    peaks = handleIterationEvent(
      {
        iter: 2,
        objective: -55,
        params: { tilt_deg: 12.3, power_dbm: 55.6 },
        stats: { peak_sab: 1.8 },
      } as SSEEvent,
      peaks,
    )
    handleDoneEvent(
      { done: true, reason: 'converged', total_iters: 2 } as SSEEvent,
      peaks,
      'tilt_power',
    )
    const summary = useOptimizeStore.getState().summary ?? ''
    expect(summary).not.toMatch(/reduction/)
    expect(summary).toMatch(/tilt 12\.3°/)
    expect(summary).toMatch(/power 55\.6 dBm/)
    expect(summary).toMatch(/peak/)
  })

  it('cancelled runs say "Cancelled" instead of the reason', () => {
    let peaks = emptyPeaks()
    peaks = handleIterationEvent({ iter: 1, objective: 0.1, params: {} } as SSEEvent, peaks)
    handleDoneEvent(
      { done: true, cancelled: true, iter: 1 } as SSEEvent,
      peaks,
      'placement',
    )
    expect(useOptimizeStore.getState().summary).toMatch(/^Cancelled after 1 iterations/)
  })
})
