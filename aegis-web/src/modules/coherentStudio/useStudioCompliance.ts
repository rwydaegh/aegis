import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { dbmToWatts, fetchCompliance, type LiveBodyMapParams } from './api'
import { complianceFetchKey, useStudioStore } from './store'

// The compliance scalars track the focus and ECBF-budget sliders (they apply the
// live precoder to the field channel), which fire continuously during a drag.
// Debounce like the body-map / slice hooks so a gesture collapses to one
// recompute on settle instead of a request storm.
const DEBOUNCE_MS = 160

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
    ecbfBudgetFrac: s.ecbfBudgetFrac,
    constraintMode: s.ecbfConstraintMode,
    sarWbOn: s.ecbfSarWbOn,
    peakSabOn: s.ecbfPeakOn,
    txPowerW: dbmToWatts(s.txPowerDbm),
    ueAntenna: s.ueAntenna,
    ueIdx: s.ueIdx,
  }
}

// Fetch the ICNIRP compliance scalars when the panel is on and its key changes.
// The panel is opt-in (the first request per phantom builds the 4 cm^2 averaging
// matrix), so this no-ops entirely while showCompliance is off. A 409 (no
// channel / Q pack, or a beam with no per-element precoder) is not an error: we
// clear the scalars and flag them as unavailable so the card can say so.
export function useStudioCompliance(): void {
  const key = useStudioStore(complianceFetchKey)
  const latestRef = useRef(0)

  useEffect(() => {
    const s = useStudioStore.getState()
    if (!s.showCompliance) {
      // Clear stale numbers when the panel is switched off so it never shows a
      // value from a previous beam / focus when reopened.
      s.setCompliance(null)
      s.setComplianceNotAvailable(false)
      return
    }
    if (!s.condition || !s.beam) return

    const timer = setTimeout(() => {
      const myId = ++latestRef.current
      const isStale = () => myId !== latestRef.current

      const run = async () => {
        try {
          const store = useStudioStore.getState()
          const res = await fetchCompliance(buildParams(store))
          if (isStale()) return
          if (res.ok) {
            store.setCompliance(res.data)
            store.setComplianceNotAvailable(false)
          } else {
            store.setCompliance(null)
            store.setComplianceNotAvailable(true)
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
