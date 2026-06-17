import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { fetchBodyMap, fetchLiveBodyMap, type BodyMapParams, type LiveBodyMapParams } from './api'
import { bodyMapFetchKey, useStudioStore } from './store'

// The default "deposited" map is live (a full-body precoder + field-channel
// recompute on the server), and its key tracks the focus and ECBF-budget
// sliders, which fire continuously during a drag. Debounce like the slice and
// volume hooks so a gesture collapses to one recompute on settle instead of a
// request storm.
const DEBOUNCE_MS = 120

function buildBodyMapParams(s: ReturnType<typeof useStudioStore.getState>): BodyMapParams {
  return {
    mesh: s.mesh,
    condition: s.condition,
    arrayN: s.arrayN,
    beam: s.beam,
    quantity: s.bodyMapQuantity,
    frequencyGhz: s.frequencyGhz,
    realisation: s.seed,
    statistic: s.bodyMapStatistic,
  }
}

function buildLiveBodyMapParams(s: ReturnType<typeof useStudioStore.getState>): LiveBodyMapParams {
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
    ueAntenna: s.ueAntenna,
    ueIdx: s.ueIdx,
  }
}

// Fetch the precomputed body-map pack when its key changes. A 409 (not
// precomputed for this combination) is not an error: we clear the body map and
// move on, leaving the phantom uncoloured rather than throwing.
export function useStudioBodyMap(): void {
  const key = useStudioStore(bodyMapFetchKey)

  const latestRef = useRef(0)

  useEffect(() => {
    const s = useStudioStore.getState()
    if (!s.condition || !s.beam) return

    const timer = setTimeout(() => {
      const myId = ++latestRef.current
      const isStale = () => myId !== latestRef.current

      const run = async () => {
        try {
          const store = useStudioStore.getState()
          // The "deposited" quantity is the live, focus-tracking map (applies the
          // current precoder to the field channel); everything else is a static
          // precomputed pack.
          const res =
            store.bodyMapQuantity === 'deposited'
              ? await fetchLiveBodyMap(buildLiveBodyMapParams(store))
              : await fetchBodyMap(buildBodyMapParams(store))
          if (isStale()) return
          if (res.ok) {
            store.setBodyMap(res.data)
            store.setBodyMapNotPrecomputed(false)
          } else {
            // Not precomputed: clear so the phantom renders without a heatmap, but
            // record the flag so the HUD can show a "not precomputed" provenance.
            store.setBodyMap(null)
            store.setBodyMapNotPrecomputed(true)
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
