import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { dbmToWatts, fetchPrecoder, type LiveBodyMapParams } from './api'
import { precoderFetchKey, useStudioStore } from './store'

// The precoder drives the Tx radiation lobe, and its key tracks the focus and
// ECBF-budget sliders, which fire continuously during a drag. Debounce like the
// body-map and slice hooks so a gesture collapses to one synth on settle.
const DEBOUNCE_MS = 120

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

// Fetch the synthesised precoder (weights + array geometry) when its key
// changes. A 409 (e.g. ECBF with no Q pack) or a beam with no per-element
// precoder clears the lobe rather than throwing; the array viz then falls back
// to the uniform-excitation pattern.
export function useStudioTxPrecoder(): void {
  const key = useStudioStore(precoderFetchKey)
  const latestRef = useRef(0)

  useEffect(() => {
    const s = useStudioStore.getState()
    if (!s.condition || !s.beam) return

    const timer = setTimeout(() => {
      const myId = ++latestRef.current
      const isStale = () => myId !== latestRef.current

      const run = async () => {
        try {
          const res = await fetchPrecoder(buildParams(useStudioStore.getState()))
          if (isStale()) return
          if (res.ok && res.data.available) {
            useStudioStore.getState().setPrecoder(res.data)
          } else {
            useStudioStore.getState().setPrecoder(null)
          }
        } catch (err) {
          if (isStale()) return
          useStudioStore.getState().setPrecoder(null)
          Sentry.captureException(err)
        }
      }

      void run()
    }, DEBOUNCE_MS)

    return () => clearTimeout(timer)
  }, [key])
}
