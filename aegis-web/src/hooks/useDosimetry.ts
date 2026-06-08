import { useEffect, useRef, useCallback } from 'react'
import { useShallow } from 'zustand/react/shallow'
import * as Sentry from '@sentry/react'
import { useSimulationStore, type DiffractionModel, type InterBody } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { useMIMOStore } from '@/stores/mimo'
import { useAntennaStore, type AntennaConfig } from '@/stores/antenna'
import { useEnvironmentStore } from '@/stores/environment'
import {
  computeDosimetry,
  computeVoxelRT,
  computeRT,
  computeSionnaRT,
  computeSionnaEnvRT,
  fetchCapabilities,
  fetchLSPHeatmap,
  isClientError,
  isNetworkError,
  type RtConfig,
  type ComputeResult,
  type ComputeParams,
  type AntennaParam,
} from '@/api/client'
import { toServer } from '@/api/coordinates'

// -----------------------------------------------------------------------------
// Module-scope helpers (kept outside the hook so they can be tested in isolation
// and do not get re-created on every render).
// -----------------------------------------------------------------------------

type SimSlice = {
  antennaPos: [number, number, number] | null
  mode: string
  exposureMode: string
  fresnel: boolean
  polarisation: boolean
  curvature: boolean
  diffractionModel: DiffractionModel
  interBody: InterBody
  selfShadow: boolean
  powerDbm: number
  skinModel: string
  freqGhz: number
  bodyOffset: [number, number, number]
  bodyRotationY: number
  stochasticPreset: string
  stochasticOverrides: Record<string, number>
  stochasticSeed: number
  enabledQuantities: Set<string>
}

type SceneSlice = {
  bodyName: string
  config: ReturnType<typeof useSceneStore.getState>['viewerConfig']
  caps: ReturnType<typeof useSceneStore.getState>['capabilities']
  pathSource: ReturnType<typeof useSceneStore.getState>['pathSource']
  rtSource: ReturnType<typeof useSceneStore.getState>['rtSource']
  rtMaxOrder: number
  loadedScenePath: string
  rtConfig: ReturnType<typeof useSceneStore.getState>['rtConfig']
}

function buildAntennasParam(enabledAntennas: AntennaConfig[]): AntennaParam[] | undefined {
  if (enabledAntennas.length === 0) return undefined
  return enabledAntennas.map(a => ({
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
  }))
}

export function buildComputeParams(
  sim: SimSlice,
  scene: SceneSlice,
  exposureScenario: string,
  enabledAntennas: AntennaConfig[],
): ComputeParams {
  // Send antenna tip position (not pole base) to the backend for physics
  const poleH = scene.config?.antenna.pole_height ?? 2
  const pos = sim.antennaPos as [number, number, number]
  const antennaTip: [number, number, number] = [pos[0], pos[1] + poleH, pos[2]]

  return {
    antennaPos: antennaTip,
    bodyOffset: sim.bodyOffset,
    bodyRotationY: sim.bodyRotationY,
    mode: sim.mode,
    fresnel: sim.fresnel,
    polarisation: sim.polarisation,
    curvature: sim.curvature,
    diffractionModel: sim.diffractionModel,
    interBody: sim.interBody,
    // Self-shadowing only affects spatial mode; pass it through regardless and
    // let the backend ignore it for non-spatial modes (it parses spatial-only).
    selfShadow: sim.selfShadow,
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
    antennas: buildAntennasParam(enabledAntennas),
    exposureMode: sim.exposureMode,
  }
}

export function buildRtConfig(scene: SceneSlice): RtConfig {
  const rc = scene.rtConfig
  return {
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
}

const NO_ENV_MESH_WARNING =
  'No environment mesh available. Load an environment (OSM buildings, 3D Tiles, or a scene file) before using ray tracing.'
const NO_ENV_MESH_WARNING_SIONNA =
  'No environment mesh available. Load an environment (OSM buildings, 3D Tiles, or a scene file) before using Sionna RT.'

export function selectComputeCall(
  scene: SceneSlice,
  params: ComputeParams,
  rtCfg: RtConfig,
  signal: AbortSignal,
): { call: Promise<ComputeResult> | null; warning: string | null } {
  if (scene.pathSource !== 'rt') {
    return { call: computeDosimetry(params, signal), warning: null }
  }

  if (scene.rtSource === 'sionna') {
    if (scene.loadedScenePath) {
      return {
        call: computeSionnaRT({ ...params, scenePath: scene.loadedScenePath, rtConfig: rtCfg }, signal),
        warning: null,
      }
    }
    if (scene.caps?.has_voxels) {
      return { call: computeVoxelRT({ ...params, rtConfig: rtCfg }, signal), warning: null }
    }
    if (scene.caps?.has_env_mesh) {
      return { call: computeSionnaEnvRT({ ...params, rtConfig: rtCfg }, signal), warning: null }
    }
    return { call: null, warning: NO_ENV_MESH_WARNING_SIONNA }
  }

  // DiffeRT: check available geometry before calling backend
  if (!scene.loadedScenePath && !scene.caps?.has_voxels && !scene.caps?.has_env_mesh) {
    return { call: null, warning: NO_ENV_MESH_WARNING }
  }
  return {
    call: computeRT({ ...params, scenePath: scene.loadedScenePath || '', rtConfig: rtCfg }, signal),
    warning: null,
  }
}

type ComputeSuccessMeta = {
  generation: number
  tRequest: number
  tResponse: number
  isRtCall: boolean
}

export function onComputeSuccess(
  result: ComputeResult,
  meta: ComputeSuccessMeta,
  generationRef: { current: number },
): void {
  const { sab, stats, arrays } = result
  if (meta.generation !== generationRef.current) return // stale response

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
  const cviz = stats.cluster_viz
  useSimulationStore.getState().setClusterVizData(
    cviz?.clusters ?? null,
    cviz?.subpaths ?? null,
  )

  // Compute timing breakdown for the UI
  const networkMs = (meta.tResponse - meta.tRequest) - (stats.timings?.route_total_ms ?? 0)
  const t = stats.timings
  useUIStore.getState().setLastComputeTiming({
    totalMs: meta.tResponse - meta.tRequest,
    rtMs: t?.rt_ms ?? null,
    kernelMs: t?.kernel_ms ?? 0,
    averagingMs: (t?.avg_build_G_4cm2_ms ?? 0) + (t?.avg_matvec_4cm2_ms ?? 0),
    complianceMs: t?.compliance_stats_ms ?? 0,
    networkMs: Math.max(0, networkMs),
    avgCached: (t?.avg_build_G_4cm2_ms ?? 999) < 1,
    gpuBackend: stats.gpu_backend ?? null,
    coldStart: stats.cold_start ?? false,
  })
  if (meta.isRtCall) {
    useUIStore.getState().setGpuWarm(true)
  }
}

export function onComputeError(
  err: unknown,
  timeoutMs: number,
  controller: AbortController,
): void {
  const notify = useNotificationStore.getState().addNotification

  if ((err as Error).name === 'AbortError') {
    // Distinguish user-initiated abort from timeout
    if (controller.signal.reason === 'timeout') {
      notify(
        'warning',
        `Compute timed out after ${timeoutMs / 1000}s. Try reducing path count or using a lower fidelity level.`,
      )
    }
    return
  }
  if (isNetworkError(err)) {
    notify('warning', 'Network error during compute. Check your connection and try again.')
    return
  }
  // GPU/Modal unavailable is an expected operational state, not a bug
  const errMsg = (err as Error).message ?? ''
  if (/GPU|Modal unavailable/i.test(errMsg)) {
    notify('warning', 'GPU is currently unavailable. Try again later or switch to a non-RT path source.')
    return
  }
  // 4xx responses are user/state issues (e.g. no environment loaded), not bugs.
  // If the server reports missing geometry, refresh capabilities so a stale
  // frontend cache (e.g. after a server restart dropped session state) doesn't
  // keep firing rejected requests.
  if (isClientError(err)) {
    notify('warning', errMsg || 'Compute request was rejected.')
    if (/scene, voxels, or environment/i.test(errMsg)) {
      fetchCapabilities()
        .then(caps => useSceneStore.getState().setCapabilities(caps))
        .catch(() => {})
    }
    return
  }
  Sentry.captureException(err)
  notify(
    'error',
    `Compute failed: ${errMsg || err}`,
    'This error has been reported and will be fixed automatically using AI. Most issues are fixed in less than 30 minutes.',
  )
}

function shouldSkipCompute(sim: SimSlice, scene: SceneSlice): boolean {
  // MIMO mode has its own compute pipeline (useMIMODosimetry)
  if (useMIMOStore.getState().enabled) return true
  // GLB phantoms handle dosimetry via AnimatedBody (inline posed mesh)
  if (useSceneStore.getState().phantomType === 'gltf') return true
  // Skip compute if glTF animation is playing (posed mesh changes every frame)
  if (useSceneStore.getState().animationPlaying) return true
  if (!sim.antennaPos || !scene.config) return true
  return false
}

// -----------------------------------------------------------------------------
// Hook
// -----------------------------------------------------------------------------

export function useDosimetry() {
  const sim = useSimulationStore(useShallow(s => ({
    antennaPos: s.antennaPos,
    mode: s.mode,
    exposureMode: s.exposureMode,
    fresnel: s.fresnel,
    polarisation: s.polarisation,
    curvature: s.curvature,
    diffractionModel: s.diffractionModel,
    interBody: s.interBody,
    selfShadow: s.selfShadow,
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
  const mimoEnabled = useMIMOStore(s => s.enabled)

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
  const lspHeatmapGenRef = useRef(0)

  const triggerCompute = useCallback(() => {
    if (shouldSkipCompute(sim, scene)) return

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

    const antStore = useAntennaStore.getState()
    const enabledAntennas = [...antStore.antennas.values()].filter(a => a.enabled)

    const params = buildComputeParams(sim, scene, exposureScenario, enabledAntennas)
    const rtCfg = buildRtConfig(scene)

    // Timeout: abort after configured limit, with a distinct reason
    const timeoutMs = scene.config?.interaction?.compute_timeout_ms ?? 60000
    const timeoutId = setTimeout(() => controller.abort('timeout'), timeoutMs)

    const { call, warning } = selectComputeCall(scene, params, rtCfg, controller.signal)

    if (!call) {
      clearTimeout(timeoutId)
      setComputing(false)
      if (warning) {
        useNotificationStore.getState().addNotification('warning', warning)
      }
      return
    }

    const tRequest = performance.now()
    call
      .then(result => {
        onComputeSuccess(
          result,
          { generation: gen, tRequest, tResponse: performance.now(), isRtCall },
          generationRef,
        )
      })
      .catch(err => {
        onComputeError(err, timeoutMs, controller)
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
    // mimoEnabled gates compute via shouldSkipCompute; subscribing here rearms
    // the single-user recompute when MIMO toggles off.
  }, [sim, scene, exposureScenario, antennaStoreState, mimoEnabled, triggerCompute])

  // LSP heatmap fetch
  const lspHeatmapVisible = useSimulationStore(s => s.lspHeatmapVisible)
  const lspHeatmapParam = useSimulationStore(s => s.lspHeatmapParam)
  const envSource = useEnvironmentStore(s => s.source)

  useEffect(() => {
    if (scene.pathSource !== 'stochastic' || envSource !== 'none' || !lspHeatmapVisible || !sim.antennaPos) return

    const gen = ++lspHeatmapGenRef.current
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
        if (gen !== lspHeatmapGenRef.current) return
        useSimulationStore.getState().setLSPHeatmapData(result.data, result.bounds, [result.vmin, result.vmax])
      })
      .catch(err => {
        if (gen !== lspHeatmapGenRef.current) return
        if (!isClientError(err)) Sentry.captureException(err)
      })
      .finally(() => {
        if (gen === lspHeatmapGenRef.current) useSimulationStore.getState().setLSPHeatmapLoading(false)
      })
  }, [scene.pathSource, envSource, lspHeatmapVisible, lspHeatmapParam, sim.stochasticPreset, sim.stochasticSeed, sim.freqGhz, sim.antennaPos, scene.config])

  // Cancel any in-flight request on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])
}
