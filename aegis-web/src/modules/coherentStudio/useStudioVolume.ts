import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { fetchVolume, type VolumeParams } from './api'
import { useStudioStore, volumeFetchKey } from './store'

const DEBOUNCE_MS = 160

function buildVolumeParams(s: ReturnType<typeof useStudioStore.getState>): VolumeParams {
  return {
    mesh: s.mesh,
    condition: s.condition,
    arrayN: s.arrayN,
    seed: s.seed,
    beam: s.beam,
    focusMode: s.focusMode,
    focusXyz: s.focusXyz,
    frequencyGhz: s.frequencyGhz,
    extentM: s.volumeExtentM,
    res: s.volumeRes,
    ecbfBudgetFrac: s.ecbfBudgetFrac,
    ueAntenna: s.ueAntenna,
  }
}

// Debounced, race-safe field-volume fetch, mirroring useStudioSlice. Gated on
// showVolume: while the 3D cloud is off, the (more expensive) box is never
// fetched and the last result is cleared so the scene drops it.
export function useStudioVolume(): void {
  const key = useStudioStore(volumeFetchKey)

  const latestRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const s = useStudioStore.getState()
    abortRef.current?.abort()
    if (!s.showVolume || !s.condition || !s.beam) {
      // Bump the request id so any in-flight response is dropped, and clear the
      // stale cloud when the toggle goes off.
      latestRef.current++
      if (s.volumeResult) s.setVolumeResult(null)
      return
    }

    const timer = setTimeout(() => {
      const myId = ++latestRef.current
      const isStale = () => myId !== latestRef.current

      const ac = new AbortController()
      abortRef.current = ac

      const run = async () => {
        const store = useStudioStore.getState()
        try {
          const result = await fetchVolume(buildVolumeParams(store), ac.signal)
          if (isStale()) return
          store.setVolumeResult(result)
        } catch (err) {
          if (isStale()) return
          if ((err as Error)?.name === 'AbortError') return
          Sentry.captureException(err)
        }
      }

      void run()
    }, DEBOUNCE_MS)

    return () => {
      clearTimeout(timer)
      abortRef.current?.abort()
    }
  }, [key])
}
