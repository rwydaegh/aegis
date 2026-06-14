import { useEffect, useRef, useState } from 'react'
import * as Sentry from '@sentry/react'
import { fetchRays, type RaysResponse } from './api'
import { useStudioStore } from './store'

// Fetch the top arrival directions for the current (condition, array, seed,
// topK). Kept out of the store (it is a pure scene-decoration result) and
// returned as local state. Race-safe via a monotonic request id.
export function useStudioRays(): RaysResponse | null {
  const condition = useStudioStore((s) => s.condition)
  const arrayN = useStudioStore((s) => s.arrayN)
  const seed = useStudioStore((s) => s.seed)
  const topK = useStudioStore((s) => s.topK)

  const [rays, setRays] = useState<RaysResponse | null>(null)
  const latestRef = useRef(0)

  useEffect(() => {
    if (!condition) return
    const myId = ++latestRef.current
    const isStale = () => myId !== latestRef.current

    fetchRays({ condition, arrayN, seed, topK })
      .then((res) => {
        if (isStale()) return
        setRays(res)
      })
      .catch((err) => {
        if (isStale()) return
        Sentry.captureException(err)
      })
  }, [condition, arrayN, seed, topK])

  return rays
}
