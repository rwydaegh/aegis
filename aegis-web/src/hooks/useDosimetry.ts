import { useEffect, useRef, useCallback } from 'react'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { computeDosimetry, computeVoxelRT, computeRT, computeSionnaRT } from '@/api/client'

export function useDosimetry() {
  const antennaPos = useSimulationStore(s => s.antennaPos)
  const level = useSimulationStore(s => s.level)
  const powerDbm = useSimulationStore(s => s.powerDbm)
  const tissue = useSimulationStore(s => s.tissue)
  const nPaths = useSimulationStore(s => s.nPaths)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const bodyRotationY = useSimulationStore(s => s.bodyRotationY)

  const config = useSceneStore(s => s.viewerConfig)
  const caps = useSceneStore(s => s.capabilities)
  const rtEnabled = useSceneStore(s => s.rtEnabled)
  const rtSource = useSceneStore(s => s.rtSource)
  const rtMaxOrder = useSceneStore(s => s.rtMaxOrder)
  const loadedScenePath = useSceneStore(s => s.loadedScenePath)

  const abortRef = useRef<AbortController | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const generationRef = useRef(0)

  const triggerCompute = useCallback(() => {
    if (!antennaPos || !config) return

    // Abort any in-flight request
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const gen = ++generationRef.current
    const setComputing = useUIStore.getState().setComputing
    setComputing(true)

    // Send antenna tip position (not pole base) to the backend for physics
    const poleH = (config.antenna as Record<string, unknown>)?.pole_height as number ?? 2
    const antennaTip: typeof antennaPos = [antennaPos[0], antennaPos[1] + poleH, antennaPos[2]]

    const params = {
      antennaPos: antennaTip,
      bodyOffset,
      bodyRotationY,
      level,
      powerDbm,
      tissue,
      nPaths,
    }

    // Timeout: abort after configured limit
    const timeoutMs = (config.interaction as Record<string, unknown> & { compute_timeout_ms?: number }).compute_timeout_ms ?? 60000
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

    // Choose endpoint based on RT state
    let computeCall: Promise<{ sab: Float32Array; stats: import('@/api/types').DosimetryStats }>
    if (rtEnabled && rtSource === 'voxel') {
      computeCall = computeVoxelRT({ ...params, maxOrder: rtMaxOrder }, controller.signal)
    } else if (rtEnabled && rtSource === 'differt' && loadedScenePath) {
      computeCall = computeRT({ ...params, scenePath: loadedScenePath, maxOrder: rtMaxOrder }, controller.signal)
    } else if (rtEnabled && rtSource === 'sionna' && loadedScenePath) {
      computeCall = computeSionnaRT({ ...params, scenePath: loadedScenePath }, controller.signal)
    } else {
      computeCall = computeDosimetry(params, controller.signal)
    }

    computeCall
      .then(({ sab, stats }) => {
        if (gen !== generationRef.current) return // stale response
        useSimulationStore.getState().setResults(sab, stats)
        if (stats.path_viz) {
          useSceneStore.getState().setRtPaths(stats.path_viz)
        }
      })
      .catch(err => {
        if ((err as Error).name === 'AbortError') return // expected cancellation
        console.error('Dosimetry compute failed:', err)
      })
      .finally(() => {
        clearTimeout(timeoutId)
        if (gen === generationRef.current) setComputing(false)
      })
  }, [antennaPos, level, powerDbm, tissue, nPaths, bodyOffset, bodyRotationY, config, caps, rtEnabled, rtSource, rtMaxOrder, loadedScenePath])

  // Debounced trigger on any dependency change
  useEffect(() => {
    if (!antennaPos) return

    if (timerRef.current) clearTimeout(timerRef.current)
    const debounceMs = config?.interaction?.debounce_ms ?? 200
    timerRef.current = setTimeout(triggerCompute, debounceMs)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [antennaPos, level, powerDbm, tissue, nPaths, bodyOffset, bodyRotationY, triggerCompute, config])

  // Cancel any in-flight request on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])
}
