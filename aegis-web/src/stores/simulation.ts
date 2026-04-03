import { create } from 'zustand'
import type { ScenePos } from '@/api/coordinates'
import type { DosimetryStats, QuantityKey, ComplianceInfo } from '@/api/types'

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

  // LSP heatmap
  lspHeatmapVisible: boolean
  lspHeatmapParam: string
  lspHeatmapData: number[][] | null
  lspHeatmapBounds: [number, number, number, number]
  lspHeatmapRange: [number, number]

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
  setLSPHeatmapVisible: (v: boolean) => void
  setLSPHeatmapParam: (p: string) => void
  setLSPHeatmapData: (data: number[][] | null, bounds: [number, number, number, number], range: [number, number]) => void
  setCompliance: (report: ComplianceInfo) => void
  setResults: (sab: Float32Array, stats: DosimetryStats, extras?: {
    sabAveraged?: Float32Array; sinc?: Float32Array; sincAveraged?: Float32Array; sab1cm2Averaged?: Float32Array
  }) => void
  clearResults: () => void
}

export const useSimulationStore = create<SimulationStore>((set) => ({
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
  lspHeatmapVisible: false,
  lspHeatmapParam: 'SF_dB',
  lspHeatmapData: null,
  lspHeatmapBounds: [-100, 100, -100, 100],
  lspHeatmapRange: [0, 1],
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
  setAntennaPos: (pos) => set({ antennaPos: pos }),
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
  setPowerDbm: (power) => set({ powerDbm: power }),
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

    // Crossing the 6 GHz boundary: S_ab does not apply below 6 GHz, auto-enable SAR_wb
    if (wasAbove6 !== nowAbove6) {
      if (!nowAbove6) {
        // Going below 6 GHz: enable SAR_wb so compliance panel stays useful
        next.add('sar_wb')
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
  setLSPHeatmapVisible: (v) => set({ lspHeatmapVisible: v }),
  setLSPHeatmapParam: (p) => set({ lspHeatmapParam: p }),
  setLSPHeatmapData: (data, bounds, range) => set({ lspHeatmapData: data, lspHeatmapBounds: bounds, lspHeatmapRange: range }),
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
}))
