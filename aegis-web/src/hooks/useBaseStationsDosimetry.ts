import { useCallback, useRef } from 'react'
import { useBaseStationsStore } from '@/stores/basestations'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { computeBasestations } from '@/api/basestations'
import { toServer } from '@/api/coordinates'
import { applyDosimetryResult, handleDosimetryError } from './_dosimetryResult'

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
      .then(result => {
        if (gen !== generationRef.current) return
        applyDosimetryResult(result)
      })
      .catch(err => {
        handleDosimetryError(err, {
          controller,
          timeoutMs,
          label: 'Base station',
          networkLabel: 'base station',
          timeoutHint: 'Try selecting fewer base stations.',
        })
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
