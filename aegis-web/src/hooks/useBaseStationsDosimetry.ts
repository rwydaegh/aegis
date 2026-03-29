import { useCallback, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { useBaseStationsStore } from '@/stores/basestations'
import { useSimulationStore } from '@/stores/simulation'
import { useNotificationStore } from '@/stores/notifications'
import { computeBasestations } from '@/api/basestations'
import { toServer } from '@/api/coordinates'

export function useBaseStationsDosimetry() {
  const abortRef = useRef<AbortController | null>(null)

  const compute = useCallback(() => {
    const store = useBaseStationsStore.getState()
    const indices = store.activeIndices()
    if (indices.length === 0) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    store.setComputing(true)

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
      },
      controller.signal,
    )
      .then(({ sab, stats, arrays }) => {
        useSimulationStore.getState().setResults(sab, stats, {
          sabAveraged: arrays['sab_4cm2'],
          sinc: arrays['sinc_local'],
          sincAveraged: arrays['sinc_averaged'],
          sab1cm2Averaged: arrays['sab_1cm2'],
        })
        if (stats.compliance) {
          useSimulationStore.getState().setCompliance(stats.compliance)
        }
      })
      .catch(err => {
        if ((err as Error).name === 'AbortError') return
        Sentry.captureException(err)
        useNotificationStore.getState().addNotification(
          'error',
          `Base station compute failed: ${(err as Error).message ?? err}`,
          'This error has been reported and will be fixed automatically. Please try again in about 30 minutes.',
        )
      })
      .finally(() => {
        store.setComputing(false)
      })
  }, [])

  return compute
}
