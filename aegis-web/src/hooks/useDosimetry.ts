import { useEffect, useRef, useCallback } from 'react'
import { useShallow } from 'zustand/react/shallow'
import * as Sentry from '@sentry/react'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { useMIMOStore } from '@/stores/mimo'
import { useAntennaStore } from '@/stores/antenna'
import { computeDosimetry, computeVoxelRT, computeRT, computeSionnaRT, computeSionnaEnvRT, fetchLSPHeatmap, isNetworkError, type RtConfig } from '@/api/client'
import { toServer } from '@/api/coordinates'

export function useDosimetry() {
  const sim = useSimulationStore(useShallow(s => ({
    antennaPos: s.antennaPos,
    mode: s.mode,
    exposureMode: s.exposureMode,
    fresnel: s.fresnel,
    polarisation: s.polarisation,
    curvature: s.curvature,
    diffraction: s.diffraction,
    powerDbm: s.powerDbm,
    skinModel: s.skinModel,
    freqGhz: s.freqGhz,
    bodyOffset: s.bodyOffset,
    bodyRotationY: s.bodyRotationY,
    stochasticPreset: s.stochasticPreset,
    stochasticOverrides: s.stochasticOverrides,
    stochasticSeed: s.stochasticSeed,
    enabledQuantities: s.enabledQuantities,
  })))

  const antennaStoreState = useAntennaStore(useShallow(s => ({
    antennas: s.antennas,
    selectedId: s.selectedId,
  })))

  const exposureScenario = useUIStore(s => s.exposureScenario)

  const scene = useSceneStore(useShallow(s => ({
    bodyName: s.bodyName,
    config: s.viewerConfig,
    caps: s.capabilities,
    pathSource: s.pathSource,
    rtSource: s.rtSource,
    rtMaxOrder: s.rtMaxOrder,
    loadedScenePath: s.loadedScenePath,
    rtConfig: s.rtConfig,
  })))

  const abortRef = useRef<AbortController | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const generationRef = useRef(0)

  const triggerCompute = useCallback(() => {
    // MIMO mode has its own compute pipeline (useMIMODosimetry)
    if (useMIMOStore.getState().enabled) return
    // GLB phantoms handle dosimetry via AnimatedBody (inline posed mesh)
    if (useSceneStore.getState().phantomType === 'gltf') return
    // Skip compute if glTF animation is playing (posed mesh changes every frame)
    if (useSceneStore.getState().animationPlaying) return
    if (!sim.antennaPos || !scene.config) return

    // Abort any in-flight request
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const gen = ++generationRef.current
    const setComputing = useUIStore.getState().setComputing
    setComputing(true)

    // Flag cold-start for the StatusBar
    const isRtCall = scene.pathSource === 'rt'
    const gpuWarm = useUIStore.getState().gpuWarm
    useUIStore.getState().setComputeColdStart(isRtCall && gpuWarm === false)

    // Send antenna tip position (not pole base) to the backend for physics
    const poleH = scene.config.antenna.pole_height ?? 2
    const antennaTip: typeof sim.antennaPos = [sim.antennaPos[0], sim.antennaPos[1] + poleH, sim.antennaPos[2]]

    // Build multi-antenna array from antenna store
    const antStore = useAntennaStore.getState()
    const enabledAntennas = [...antStore.antennas.values()].filter(a => a.enabled)
    const antennasParam = enabledAntennas.length > 0 ? enabledAntennas.map(a => ({
      position: [a.position[0], a.position[1] + a.height, a.position[2]] as [number, number, number],
      power_dbm: a.powerDbm,
      array_config: {
        n_h: a.arrayConfig.n_h,
        n_v: a.arrayConfig.n_v,
        d_h_wavelengths: a.arrayConfig.d_h_wavelengths,
        d_v_wavelengths: a.arrayConfig.d_v_wavelengths,
        broadside: a.arrayConfig.broadside,
        element_pattern: a.arrayConfig.element_pattern,
      },
    })) : undefined

    const params = {
      antennaPos: antennaTip,
      bodyOffset: sim.bodyOffset,
      bodyRotationY: sim.bodyRotationY,
      mode: sim.mode,
      fresnel: sim.fresnel,
      polarisation: sim.polarisation,
      curvature: sim.curvature,
      diffraction: sim.diffraction,
      powerDbm: sim.powerDbm,
      skinModel: sim.skinModel,
      freqGhz: sim.freqGhz,
      stochastic: scene.pathSource === 'stochastic',
      stochasticPreset: sim.stochasticPreset,
      stochasticOverrides: sim.stochasticOverrides,
      stochasticSeed: sim.stochasticSeed,
      quantities: Array.from(sim.enabledQuantities) as string[],
      exposureScenario,
      bodyName: scene.bodyName || undefined,
      antennas: antennasParam,
      exposureMode: sim.exposureMode,
    }

    // Timeout: abort after configured limit, with a distinct reason
    const timeoutMs = scene.config?.interaction?.compute_timeout_ms ?? 60000
    const timeoutId = setTimeout(() => controller.abort('timeout'), timeoutMs)

    // Build RT config from store state
    const rc = scene.rtConfig
    const rtCfg: RtConfig = {
      max_depth: scene.rtMaxOrder,
      method: rc.method,
      rays_per_source: rc.raysPerSource,
      max_paths_per_source: rc.maxPathsPerSource,
      chunk_size: rc.chunkSize,
      los: rc.los,
      specular_reflection: rc.specularReflection,
      diffuse_reflection: rc.diffuseReflection,
      refraction: rc.refraction,
      diffraction: rc.diffraction,
      edge_diffraction: rc.edgeDiffraction,
      diffraction_lit_region: rc.diffractionLitRegion,
      reflection_loss_per_order: rc.reflectionLoss,
      synthetic_array: rc.syntheticArray,
      seed: rc.seed,
    }

    // Choose endpoint based on path source
    let computeCall: Promise<import('@/api/client').ComputeResult>
    if (scene.pathSource === 'rt') {
      if (scene.rtSource === 'sionna') {
        // Sionna RT: route based on available geometry
        if (scene.loadedScenePath) {
          computeCall = computeSionnaRT({ ...params, scenePath: scene.loadedScenePath, rtConfig: rtCfg }, controller.signal)
        } else if (scene.caps?.has_voxels) {
          computeCall = computeVoxelRT({ ...params, rtConfig: rtCfg }, controller.signal)
        } else if (scene.caps?.has_env_mesh) {
          computeCall = computeSionnaEnvRT({ ...params, rtConfig: rtCfg }, controller.signal)
        } else {
          setComputing(false)
          useNotificationStore.getState().addNotification(
            'warning',
            'No environment mesh available. Load an environment (OSM buildings, 3D Tiles, or a scene file) before using Sionna RT.',
          )
          return
        }
      } else {
        // DiffeRT: check available geometry before calling backend
        if (!scene.loadedScenePath && !scene.caps?.has_voxels && !scene.caps?.has_env_mesh) {
          setComputing(false)
          useNotificationStore.getState().addNotification(
            'warning',
            'No environment mesh available. Load an environment (OSM buildings, 3D Tiles, or a scene file) before using ray tracing.',
          )
          return
        }
        computeCall = computeRT({ ...params, scenePath: scene.loadedScenePath || '', rtConfig: rtCfg }, controller.signal)
      }
    } else {
      computeCall = computeDosimetry(params, controller.signal)
    }

    const t_request = performance.now()
    computeCall
      .then(({ sab, stats, arrays }) => {
        const t_response = performance.now()
        if (gen !== generationRef.current) return // stale response
        useNotificationStore.getState().dismissByLevel('error')
        useSimulationStore.getState().setResults(sab, stats, {
          sabAveraged: arrays['sab_4cm2'],
          sinc: arrays['sinc_local'],
          sincAveraged: arrays['sinc_wb'],
          sab1cm2Averaged: arrays['sab_1cm2'],
        })
        if (stats.path_viz) {
          useSceneStore.getState().setRtPaths(stats.path_viz)
        }
        // Store cluster visualization data from stochastic channel
        const cviz = stats.cluster_viz
        useSimulationStore.getState().setClusterVizData(
          cviz?.clusters ?? null,
          cviz?.subpaths ?? null,
        )

        // Compute timing breakdown for the UI
        const networkMs = (t_response - t_request) - (stats.timings?.route_total_ms ?? 0)
        const t = stats.timings
        useUIStore.getState().setLastComputeTiming({
          totalMs: t_response - t_request,
          rtMs: t?.rt_ms ?? null,
          kernelMs: t?.kernel_ms ?? 0,
          averagingMs: (t?.avg_build_G_4cm2_ms ?? 0) + (t?.avg_matvec_4cm2_ms ?? 0),
          complianceMs: t?.compliance_stats_ms ?? 0,
          networkMs: Math.max(0, networkMs),
          avgCached: (t?.avg_build_G_4cm2_ms ?? 999) < 1,
          gpuBackend: stats.gpu_backend ?? null,
          coldStart: stats.cold_start ?? false,
        })
        // GPU is now warm after successful RT
        if (isRtCall) {
          useUIStore.getState().setGpuWarm(true)
        }
      })
      .catch(err => {
        if ((err as Error).name === 'AbortError') {
          // Distinguish user-initiated abort from timeout
          if (controller.signal.reason === 'timeout') {
            useNotificationStore.getState().addNotification(
              'warning',
              `Compute timed out after ${timeoutMs / 1000}s. Try reducing path count or using a lower fidelity level.`,
            )
          }
          return
        }
        if (isNetworkError(err)) {
          useNotificationStore.getState().addNotification(
            'warning',
            'Network error during compute. Check your connection and try again.',
          )
          return
        }
        Sentry.captureException(err)
        useNotificationStore.getState().addNotification('error', `Compute failed: ${(err as Error).message ?? err}`, 'This error has been reported and will be fixed automatically using AI. Most issues are fixed in less than 30 minutes.')
      })
      .finally(() => {
        clearTimeout(timeoutId)
        if (gen === generationRef.current) setComputing(false)
      })
  }, [sim, scene, exposureScenario, antennaStoreState])

  // Debounced trigger on any dependency change
  useEffect(() => {
    if (!sim.antennaPos) return

    if (timerRef.current) clearTimeout(timerRef.current)
    const debounceMs = scene.config?.interaction?.debounce_ms ?? 200
    timerRef.current = setTimeout(triggerCompute, debounceMs)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [sim, scene, exposureScenario, antennaStoreState, triggerCompute])

  // LSP heatmap fetch
  const lspHeatmapVisible = useSimulationStore(s => s.lspHeatmapVisible)
  const lspHeatmapParam = useSimulationStore(s => s.lspHeatmapParam)

  useEffect(() => {
    if (scene.pathSource !== 'stochastic' || !lspHeatmapVisible || !sim.antennaPos) return

    const controller = new AbortController()
    const poleH = scene.config?.antenna?.pole_height ?? 2
    const antennaTip: [number, number, number] = [sim.antennaPos[0], sim.antennaPos[1] + poleH, sim.antennaPos[2]]

    useSimulationStore.getState().setLSPHeatmapLoading(true)
    fetchLSPHeatmap({
      preset: sim.stochasticPreset,
      freq_ghz: sim.freqGhz,
      antenna_pos: toServer(antennaTip),
      lsp_name: lspHeatmapParam,
      bounds: [-100, 100, -100, 100],
      resolution: 128,
      seed: sim.stochasticSeed,
    })
      .then(result => {
        if (controller.signal.aborted) return
        useSimulationStore.getState().setLSPHeatmapData(result.data, result.bounds, [result.vmin, result.vmax])
      })
      .catch(err => {
        if ((err as Error).name === 'AbortError') return
        Sentry.captureException(err)
      })
      .finally(() => {
        useSimulationStore.getState().setLSPHeatmapLoading(false)
      })

    return () => { controller.abort() }
  }, [scene.pathSource, lspHeatmapVisible, lspHeatmapParam, sim.stochasticPreset, sim.stochasticSeed, sim.freqGhz, sim.antennaPos, scene.config])

  // Cancel any in-flight request on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])
}
