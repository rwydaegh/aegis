import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { fetchComplianceSweep, type LiveBodyMapParams } from './api'
import { complianceSweepFetchKey, useStudioStore } from './store'

// The budget sweep re-solves ECBF at ~20 budget points server-side, so it is
// heavier than a single compliance read. Debounce focus/scenario changes like the
// other live hooks so a drag collapses to one sweep on settle.
const DEBOUNCE_MS = 220
const SWEEP_POINTS = 20

function buildParams(s: ReturnType<typeof useStudioStore.getState>): LiveBodyMapParams {
  return {
    mesh: s.mesh,
    condition: s.condition,
    arrayN: s.arrayN,
    seed: s.seed,
    beam: s.beam,
    focusMode: s.focusMode,
    focusXyz: s.focusXyz,
    frequencyGhz: s.frequencyGhz,
    ueAntenna: s.ueAntenna,
    ueIdx: s.ueIdx,
  }
}

// Fetch the ECBF budget-sweep curves when the panel is on and the ECBF beam is
// selected. No-ops (and clears) otherwise, so non-ECBF beams pay nothing. A 409
// (no channel / Q pack) clears the curves and flags them unavailable; the chart
// then hides rather than showing a stale Pareto front.
export function useStudioComplianceSweep(): void {
  const key = useStudioStore(complianceSweepFetchKey)
  const latestRef = useRef(0)

  useEffect(() => {
    const s = useStudioStore.getState()
    if (!s.showCompliance || s.beam !== 'ecbf') {
      s.setComplianceSweep(null)
      s.setComplianceSweepNotAvailable(false)
      return
    }
    if (!s.condition) return

    const timer = setTimeout(() => {
      const myId = ++latestRef.current
      const isStale = () => myId !== latestRef.current

      const run = async () => {
        try {
          const store = useStudioStore.getState()
          const res = await fetchComplianceSweep(buildParams(store), SWEEP_POINTS)
          if (isStale()) return
          if (res.ok) {
            store.setComplianceSweep(res.data)
            store.setComplianceSweepNotAvailable(false)
          } else {
            store.setComplianceSweep(null)
            store.setComplianceSweepNotAvailable(true)
          }
        } catch (err) {
          if (isStale()) return
          Sentry.captureException(err)
        }
      }

      void run()
    }, DEBOUNCE_MS)

    return () => clearTimeout(timer)
  }, [key])
}
