import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { fetchScene } from './api'
import { useStudioStore } from './store'

// Fetch the real scene geometry (blockers, room, BS) for the current
// (condition, seed) and stash it in the store. The geometry is array-size
// independent, so it keys only on condition + seed. A not-precomputed miss
// clears the scene (the blockers just do not draw). Race-safe via a monotonic
// request id.
export function useStudioScene(): void {
  const condition = useStudioStore((s) => s.condition)
  const seed = useStudioStore((s) => s.seed)
  const setScene = useStudioStore((s) => s.setScene)

  const latestRef = useRef(0)

  useEffect(() => {
    if (!condition) return
    const myId = ++latestRef.current
    const isStale = () => myId !== latestRef.current

    fetchScene(condition, seed)
      .then((res) => {
        if (isStale()) return
        setScene(res.ok ? res.data : null)
      })
      .catch((err) => {
        if (isStale()) return
        setScene(null)
        Sentry.captureException(err)
      })
  }, [condition, seed, setScene])
}
