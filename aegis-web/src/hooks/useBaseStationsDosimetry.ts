import { useCallback, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { useBaseStationsStore } from '@/stores/basestations'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { computeBasestations } from '@/api/basestations'
import { isNetworkError } from '@/api/client'
import { toServer } from '@/api/coordinates'

export function useBaseStationsDosimetry() {
  const abortRef = useRef<AbortController | null>(null)
  const generationRef = useRef(0)

  const compute = useCallback(() => {
    const store = useBaseStationsStore.getState()
    const indices = store.activeIndices()
    if (indices.length === 0) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const gen = ++generationRef.current
    store.setComputing(true)
    useUIStore.getState().setComputing(true)

    const timeoutMs = 120_000
    const timeoutId = setTimeout(() => controller.abort('timeout'), timeoutMs)

    const sim = useSimulationStore.getState()
    const enabledQuantities = Array.from(sim.enabledQuantities) as string[]

    computeBasestations(
      {
        indices,
        mode: 'spatial',
        body_offset: toServer(sim.bodyOffset),
        body_rotation_y: sim.bodyRotationY,
        quantities: enabledQuantities,
        skin_model: sim.skinModel,
        exposure_mode: sim.exposureMode,
      },
      controller.signal,
    )
      .then(({ sab, stats, arrays }) => {
        if (gen !== generationRef.current) return
        useNotificationStore.getState().dismissByLevel('error')
        useSimulationStore.getState().setResults(sab, stats, {
          sabAveraged: arrays['sab_4cm2'],
          sinc: arrays['sinc_local'],
          sincAveraged: arrays['sinc_wb'],
          sab1cm2Averaged: arrays['sab_1cm2'],
        })
      })
      .catch(err => {
        if ((err as Error).name === 'AbortError') {
          if (controller.signal.reason === 'timeout') {
            useNotificationStore.getState().addNotification(
              'warning',
              `Base station compute timed out after ${timeoutMs / 1000}s. Try selecting fewer base stations.`,
            )
          }
          return
        }
        if (isNetworkError(err)) {
          useNotificationStore.getState().addNotification(
            'warning',
            'Network error during base station compute. Check your connection and try again.',
          )
          return
        }
        Sentry.captureException(err)
        useNotificationStore.getState().addNotification(
          'error',
          `Base station compute failed: ${(err as Error).message ?? err}`,
          'This error has been reported and will be fixed automatically using AI. Most issues are fixed in less than 30 minutes.',
        )
      })
      .finally(() => {
        clearTimeout(timeoutId)
        if (gen === generationRef.current) {
          store.setComputing(false)
          useUIStore.getState().setComputing(false)
        }
      })
  }, [])

  return compute
}
