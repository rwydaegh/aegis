import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { fetchPhantom } from './api'
import { useStudioStore } from './store'

// The store does not carry a phantom-mesh selector yet, so the studio renders the
// canonical thelonious phantom (the mesh the e11 geometry is baked around, and the
// only phantom the manifest advertises).
const MESH = 'thelonious'

// Fetch the phantom geometry once and store it. Guarded so it fetches a single
// time even across re-renders.
export function useStudioPhantom(): void {
  const fetchedRef = useRef(false)

  useEffect(() => {
    if (fetchedRef.current) return
    fetchedRef.current = true

    let cancelled = false
    fetchPhantom(MESH)
      .then((geom) => {
        if (cancelled) return
        useStudioStore.getState().setPhantom(geom)
      })
      .catch((err) => {
        if (cancelled) return
        fetchedRef.current = false
        Sentry.captureException(err)
      })
    return () => {
      cancelled = true
    }
  }, [])
}
