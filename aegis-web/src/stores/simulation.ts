import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ScenePos } from '@/api/coordinates'
import type { DosimetryStats, QuantityKey, ComplianceInfo, ClusterVizItem, SubpathVizItem } from '@/api/types'
import { useAntennaStore } from '@/stores/antenna'

export type DosimetryMode = 'bound' | 'aggregate' | 'spatial'
export type ExposureMode = 'theoretical' | 'actual_max' | 'typical'

interface SimulationStore {
  // Inputs
  antennaPos: ScenePos | null
  selectedPattern: {
    source: string
    id: string
    manufacturer: string
    model: string
    gain_dbi: number
  } | null

  // Loaded pattern data (for preview)
  patternData: Float32Array | null
  patternMeta: { max_gain_dbi: number; shape: [number, number] } | null
  patternLoading: boolean

  // Applied pattern (used by 3D scene)
  appliedPattern: Float32Array | null
  appliedPatternMeta: {
    source: string
    id: string
    manufacturer: string
    model: string
    gain_dbi: number
    max_gain_dbi: number
    shape: [number, number]
  } | null

  mode: DosimetryMode
  exposureMode: ExposureMode
  fresnel: boolean
  polarisation: boolean
  curvature: boolean
  diffraction: boolean
  powerDbm: number
  skinModel: string
  stochasticPreset: string
  stochasticOverrides: Record<string, number>
  stochasticSeed: number

  // Body physics state
  bodyOffset: ScenePos
  bodyRotationY: number

  // Cluster visualization
  clusterVizVisible: boolean
  clusterVizDetail: 'clusters' | 'subpaths'
  clusterVizData: ClusterVizItem[] | null
  subpathVizData: SubpathVizItem[] | null

  // LSP heatmap
  lspHeatmapVisible: boolean
  lspHeatmapParam: string
  lspHeatmapData: number[][] | null
  lspHeatmapBounds: [number, number, number, number]
  lspHeatmapRange: [number, number]
  lspHeatmapLoading: boolean

  // Results
  sabArray: Float32Array | null
  sabAveragedArray: Float32Array | null
  sincArray: Float32Array | null
  sincAveragedArray: Float32Array | null
  sab1cm2AveragedArray: Float32Array | null
  stats: DosimetryStats | null
  compliance: ComplianceInfo | null

  // Inputs (compliance)
  freqGhz: number
  enabledQuantities: Set<QuantityKey>
  displayQuantity: QuantityKey

  // Actions
  setAntennaPos: (pos: ScenePos | null) => void
  setSelectedPattern: (p: { source: string; id: string; manufacturer: string; model: string; gain_dbi: number } | null) => void
  setPatternData: (data: Float32Array | null, meta: { max_gain_dbi: number; shape: [number, number] } | null) => void
  setPatternLoading: (v: boolean) => void
  applyPattern: () => void
  clearAppliedPattern: () => void
  setMode: (mode: DosimetryMode) => void
  setExposureMode: (mode: ExposureMode) => void
  setFresnel: (on: boolean) => void
  setPolarisation: (on: boolean) => void
  setCurvature: (on: boolean) => void
  setDiffraction: (on: boolean) => void
  setPowerDbm: (power: number) => void
  setSkinModel: (model: string) => void
  setStochasticPreset: (v: string) => void
  setStochasticOverrides: (v: Record<string, number>) => void
  setStochasticSeed: (v: number) => void
  setBodyOffset: (offset: ScenePos) => void
  setBodyRotationY: (angle: number) => void
  setFreqGhz: (v: number) => void
  setEnabledQuantities: (q: Set<QuantityKey>) => void
  toggleQuantity: (key: QuantityKey) => void
  setDisplayQuantity: (key: QuantityKey) => void
  setClusterVizVisible: (v: boolean) => void
  setClusterVizDetail: (v: 'clusters' | 'subpaths') => void
  setClusterVizData: (data: ClusterVizItem[] | null, subpaths?: SubpathVizItem[] | null) => void
  setLSPHeatmapVisible: (v: boolean) => void
  setLSPHeatmapParam: (p: string) => void
  setLSPHeatmapData: (data: number[][] | null, bounds: [number, number, number, number], range: [number, number]) => void
  setLSPHeatmapLoading: (v: boolean) => void
  setCompliance: (report: ComplianceInfo) => void
  setResults: (sab: Float32Array, stats: DosimetryStats, extras?: {
    sabAveraged?: Float32Array; sinc?: Float32Array; sincAveraged?: Float32Array; sab1cm2Averaged?: Float32Array
  }) => void
  clearResults: () => void
}

export const useSimulationStore = create<SimulationStore>()(persist((set) => ({
  antennaPos: null,
  selectedPattern: null,
  patternData: null,
  patternMeta: null,
  patternLoading: false,
  appliedPattern: null,
  appliedPatternMeta: null,
  mode: 'spatial',
  exposureMode: 'theoretical',
  fresnel: true,
  polarisation: false,
  curvature: false,
  diffraction: false,
  powerDbm: 60,
  skinModel: 'itis',
  stochasticPreset: '3GPP_38.901_UMi_LOS',
  stochasticOverrides: {},
  stochasticSeed: 42,
  bodyOffset: [0, 0, 0],
  bodyRotationY: 0,
  clusterVizVisible: true,
  clusterVizDetail: 'clusters',
  clusterVizData: null,
  subpathVizData: null,
  lspHeatmapVisible: true,
  lspHeatmapParam: 'SF_dB',
  lspHeatmapData: null,
  lspHeatmapBounds: [-100, 100, -100, 100],
  lspHeatmapRange: [0, 1],
  lspHeatmapLoading: false,
  sabArray: null,
  sabAveragedArray: null,
  sincArray: null,
  sincAveragedArray: null,
  sab1cm2AveragedArray: null,
  stats: null,
  compliance: null,
  freqGhz: 28,
  enabledQuantities: new Set<QuantityKey>(['sab', 'sab_4cm2']),
  displayQuantity: 'sab' as QuantityKey,
  setAntennaPos: (pos) => {
    set({ antennaPos: pos })
    const antStore = useAntennaStore.getState()
    if (pos && antStore.antennas.size === 0) {
      antStore.addAntenna(pos)
    } else if (pos && antStore.selectedId) {
      antStore.moveAntenna(antStore.selectedId, pos)
    } else if (!pos) {
      antStore.selectAntenna(null)
    }
  },
  setSelectedPattern: (p) => set({ selectedPattern: p }),
  setPatternData: (data, meta) => set({ patternData: data, patternMeta: meta }),
  setPatternLoading: (v) => set({ patternLoading: v }),
  applyPattern: () => set((state) => {
    if (!state.patternData || !state.patternMeta || !state.selectedPattern) return {}
    return {
      appliedPattern: state.patternData,
      appliedPatternMeta: {
        source: state.selectedPattern.source,
        id: state.selectedPattern.id,
        manufacturer: state.selectedPattern.manufacturer,
        model: state.selectedPattern.model,
        gain_dbi: state.selectedPattern.gain_dbi,
        max_gain_dbi: state.patternMeta.max_gain_dbi,
        shape: state.patternMeta.shape,
      },
    }
  }),
  clearAppliedPattern: () => set({ appliedPattern: null, appliedPatternMeta: null }),
  setMode: (mode) => set({ mode }),
  setExposureMode: (exposureMode) => set({ exposureMode }),
  setFresnel: (on) => set(() => {
    // Polarisation requires Fresnel, so auto-disable it
    if (!on) return { fresnel: false, polarisation: false }
    return { fresnel: true }
  }),
  setPolarisation: (on) => set(() => {
    // Polarisation requires Fresnel, so auto-enable it
    if (on) return { polarisation: true, fresnel: true }
    return { polarisation: false }
  }),
  setCurvature: (on) => set(() => {
    // Diffraction requires curvature, so auto-disable it
    if (!on) return { curvature: false, diffraction: false }
    return { curvature: true }
  }),
  setDiffraction: (on) => set(() => {
    // Diffraction requires curvature data, so auto-enable it
    if (on) return { diffraction: true, curvature: true }
    return { diffraction: false }
  }),
  setPowerDbm: (power) => {
    set({ powerDbm: power })
    const antStore = useAntennaStore.getState()
    if (antStore.selectedId) {
      antStore.updateAntenna(antStore.selectedId, { powerDbm: power })
    }
  },
  setSkinModel: (skinModel) => set({ skinModel }),
  setStochasticPreset: (v) => set({ stochasticPreset: v }),
  setStochasticOverrides: (v) => set({ stochasticOverrides: v }),
  setStochasticSeed: (v) => set({ stochasticSeed: v }),
  setBodyOffset: (offset) => set({ bodyOffset: offset }),
  setBodyRotationY: (angle) => set({ bodyRotationY: angle }),
  setFreqGhz: (v) => set((state) => {
    const wasAbove30 = state.freqGhz > 30
    const nowAbove30 = v > 30
    const wasAbove6 = state.freqGhz > 6
    const nowAbove6 = v > 6

    if (wasAbove30 === nowAbove30 && wasAbove6 === nowAbove6) return { freqGhz: v }

    const next = new Set(state.enabledQuantities)
    let displayQuantity = state.displayQuantity

    // Crossing the 6 GHz boundary: swap SAR_wb availability
    if (wasAbove6 !== nowAbove6) {
      if (!nowAbove6) {
        // Going below 6 GHz: enable SAR_wb so compliance panel stays useful
        next.add('sar_wb')
      } else {
        // Going above 6 GHz: remove SAR_wb (not applicable at mmWave)
        next.delete('sar_wb')
        if (displayQuantity === 'sar_wb') displayQuantity = 'sab'
      }
    }

    // Crossing the 30 GHz boundary: swap 4 cm² <-> 1 cm² defaults
    if (wasAbove30 !== nowAbove30) {
      if (nowAbove30) {
        if (next.has('sab_4cm2')) { next.delete('sab_4cm2'); next.add('sab_1cm2') }
        if (displayQuantity === 'sab_4cm2') displayQuantity = 'sab_1cm2'
      } else {
        if (next.has('sab_1cm2')) { next.delete('sab_1cm2'); next.add('sab_4cm2') }
        if (displayQuantity === 'sab_1cm2') displayQuantity = 'sab_4cm2'
      }
    }
    return { freqGhz: v, enabledQuantities: next, displayQuantity }
  }),
  setEnabledQuantities: (q) => set({ enabledQuantities: q }),
  toggleQuantity: (key) => set((state) => {
    // sab is always required (backend always returns it)
    if (key === 'sab') return {}
    const next = new Set(state.enabledQuantities)
    if (next.has(key)) {
      next.delete(key)
      if (state.displayQuantity === key) {
        const fallback = next.size > 0 ? [...next][0] : ('sab' as QuantityKey)
        return { enabledQuantities: next, displayQuantity: fallback }
      }
    } else {
      next.add(key)
    }
    return { enabledQuantities: next }
  }),
  setDisplayQuantity: (key) => set({ displayQuantity: key }),
  setClusterVizVisible: (v) => set({ clusterVizVisible: v }),
  setClusterVizDetail: (v) => set({ clusterVizDetail: v }),
  setClusterVizData: (data, subpaths) => set({ clusterVizData: data, subpathVizData: subpaths ?? null }),
  setLSPHeatmapVisible: (v) => set({ lspHeatmapVisible: v }),
  setLSPHeatmapParam: (p) => set({ lspHeatmapParam: p }),
  setLSPHeatmapData: (data, bounds, range) => set({ lspHeatmapData: data, lspHeatmapBounds: bounds, lspHeatmapRange: range }),
  setLSPHeatmapLoading: (v) => set({ lspHeatmapLoading: v }),
  setCompliance: (report) => set({ compliance: report }),
  setResults: (sab, stats, extras) => set({
    sabArray: sab,
    stats,
    sabAveragedArray: extras?.sabAveraged ?? null,
    sincArray: extras?.sinc ?? null,
    sincAveragedArray: extras?.sincAveraged ?? null,
    sab1cm2AveragedArray: extras?.sab1cm2Averaged ?? null,
    compliance: stats.compliance ?? null,
  }),
  clearResults: () => set({ sabArray: null, sabAveragedArray: null, sincArray: null, sincAveragedArray: null, sab1cm2AveragedArray: null, stats: null, compliance: null }),
}), {
  name: 'aegis-simulation-settings',
  version: 1,
  partialize: (state) => ({
    mode: state.mode,
    fresnel: state.fresnel,
    polarisation: state.polarisation,
    curvature: state.curvature,
    diffraction: state.diffraction,
    powerDbm: state.powerDbm,
    skinModel: state.skinModel,
    freqGhz: state.freqGhz,
    exposureMode: state.exposureMode,
    displayQuantity: state.displayQuantity,
  }),
  merge: (persisted, current) => {
    const merged = { ...current, ...(persisted as Partial<SimulationStore>) }
    // Validate displayQuantity against the default enabledQuantities set.
    // enabledQuantities is NOT persisted, so it resets to default on reload.
    // If the persisted displayQuantity is not in the default set, fall back.
    if (!current.enabledQuantities.has(merged.displayQuantity)) {
      merged.displayQuantity = current.enabledQuantities.values().next().value ?? 'sab'
    }
    return merged
  },
}))

// Bootstrap antenna store from existing antennaPos (config, share link, scenario)
const initialPos = useSimulationStore.getState().antennaPos
if (initialPos && useAntennaStore.getState().antennas.size === 0) {
  useAntennaStore.getState().addAntenna(initialPos)
}

// Sync antenna store -> simulation store (selected antenna's pos/power)
useAntennaStore.subscribe((state) => {
  const selected = state.selectedId ? state.antennas.get(state.selectedId) : null
  const sim = useSimulationStore.getState()
  if (selected) {
    if (sim.antennaPos?.[0] !== selected.position[0] ||
        sim.antennaPos?.[1] !== selected.position[1] ||
        sim.antennaPos?.[2] !== selected.position[2]) {
      useSimulationStore.setState({ antennaPos: selected.position })
    }
    if (sim.powerDbm !== selected.powerDbm) {
      useSimulationStore.setState({ powerDbm: selected.powerDbm })
    }
  } else if (state.antennas.size === 0 && sim.antennaPos !== null) {
    useSimulationStore.setState({ antennaPos: null })
  }
})
