import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { fetchBodyMap, type BodyMapParams } from './api'
import { bodyMapFetchKey, useStudioStore } from './store'

function buildBodyMapParams(s: ReturnType<typeof useStudioStore.getState>): BodyMapParams {
  return {
    condition: s.condition,
    arrayN: s.arrayN,
    beam: s.beam,
    quantity: s.bodyMapQuantity,
    frequencyGhz: s.frequencyGhz,
    realisation: s.seed,
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
        const res = await fetchBodyMap(buildBodyMapParams(useStudioStore.getState()))
        if (isStale()) return
        if (res.ok) {
          useStudioStore.getState().setBodyMap(res.data)
        } else {
          // Not precomputed: clear so the phantom renders without a heatmap.
          useStudioStore.getState().setBodyMap(null)
        }
      } catch (err) {
        if (isStale()) return
        Sentry.captureException(err)
      }
    }

    void run()
  }, [key])
}
