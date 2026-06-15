import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { fetchSlice, type SliceParams } from './api'
import { sliceFetchKey, useStudioStore } from './store'

const DEBOUNCE_MS = 120

function buildSliceParams(s: ReturnType<typeof useStudioStore.getState>): SliceParams {
  return {
    mesh: s.mesh,
    condition: s.condition,
    arrayN: s.arrayN,
    seed: s.seed,
    beam: s.beam,
    focusMode: s.focusMode,
    focusXyz: s.focusXyz,
    frequencyGhz: s.frequencyGhz,
    plane: s.plane,
    quantity: s.fieldQuantity,
    ecbfBudgetFrac: s.ecbfBudgetFrac,
  }
}

// Debounced, race-safe slice fetch. Subscribes to the derived slice key; on every
// change it debounces, cancels any in-flight request, and drops stale responses
// via a monotonic request id (mirrors the discipline in exposureLab/useLabCompute).
export function useStudioSlice(): void {
  const key = useStudioStore(sliceFetchKey)

  const latestRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const s = useStudioStore.getState()
    // Params are not ready until the manifest seeds condition/beam.
    if (!s.condition || !s.beam) return

    const timer = setTimeout(() => {
      const myId = ++latestRef.current
      const isStale = () => myId !== latestRef.current

      abortRef.current?.abort()
      const ac = new AbortController()
      abortRef.current = ac

      const run = async () => {
        const store = useStudioStore.getState()
        store.setComputing(true)
        try {
          const result = await fetchSlice(buildSliceParams(store), ac.signal)
          if (isStale()) return
          store.setSliceResult(result)
        } catch (err) {
          if (isStale()) return
          if ((err as Error)?.name === 'AbortError') return
          Sentry.captureException(err)
        } finally {
          if (!isStale()) store.setComputing(false)
        }
      }

      void run()
    }, DEBOUNCE_MS)

    return () => {
      clearTimeout(timer)
      // Drop any in-flight slice request when the key changes or the studio unmounts.
      abortRef.current?.abort()
    }
  }, [key])
}
