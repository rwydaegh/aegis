import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { fetchPowerSweep, type LiveBodyMapParams } from './api'
import { powerSweepFetchKey, useStudioStore } from './store'

// The power sweep re-solves the absolute-ICNIRP QCQP at ~24 transmit powers
// server-side, so it is heavier than a single compliance read. Debounce
// focus/scenario changes like the other live hooks so a drag collapses to one
// sweep on settle.
const DEBOUNCE_MS = 240
const SWEEP_POINTS = 24

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
    sarWbOn: s.ecbfSarWbOn,
    peakSabOn: s.ecbfPeakOn,
  }
}

// Fetch the absolute-mode ECBF-vs-MRT power-sweep curves when the panel is on and
// the absolute ECBF beam is selected. No-ops (and clears) otherwise, so relative
// mode and non-ECBF beams pay nothing. A 409 (no channel pack) clears the curves
// and flags them unavailable; the chart then hides rather than showing stale data.
export function useStudioPowerSweep(): void {
  const key = useStudioStore(powerSweepFetchKey)
  const latestRef = useRef(0)

  useEffect(() => {
    const s = useStudioStore.getState()
    if (!s.showCompliance || s.beam !== 'ecbf' || s.ecbfConstraintMode !== 'absolute') {
      s.setPowerSweep(null)
      s.setPowerSweepNotAvailable(false)
      return
    }
    if (!s.condition) return

    const timer = setTimeout(() => {
      const myId = ++latestRef.current
      const isStale = () => myId !== latestRef.current

      const run = async () => {
        try {
          const store = useStudioStore.getState()
          const res = await fetchPowerSweep(buildParams(store), SWEEP_POINTS)
          if (isStale()) return
          if (res.ok) {
            store.setPowerSweep(res.data)
            store.setPowerSweepNotAvailable(false)
          } else {
            store.setPowerSweep(null)
            store.setPowerSweepNotAvailable(true)
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
