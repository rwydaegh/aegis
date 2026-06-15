import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { fetchBodyMap, fetchLiveBodyMap, type BodyMapParams, type LiveBodyMapParams } from './api'
import { bodyMapFetchKey, useStudioStore } from './store'

function buildBodyMapParams(s: ReturnType<typeof useStudioStore.getState>): BodyMapParams {
  return {
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
    condition: s.condition,
    arrayN: s.arrayN,
    seed: s.seed,
    beam: s.beam,
    focusMode: s.focusMode,
    focusXyz: s.focusXyz,
    frequencyGhz: s.frequencyGhz,
    ecbfBudgetFrac: s.ecbfBudgetFrac,
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
  }, [key])
}
