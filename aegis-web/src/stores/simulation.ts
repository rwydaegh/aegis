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
  setCompliance: (report: ComplianceInfo) => void
  setResults: (sab: Float32Array, stats: DosimetryStats, extras?: {
    sabAveraged?: Float32Array; sinc?: Float32Array; sincAveraged?: Float32Array; sab1cm2Averaged?: Float32Array
  }) => void
  clearResults: () => void
}

export const useSimulationStore = create<SimulationStore>((set) => ({
  antennaPos: null,
  selectedPattern: null,
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
  setCurvature: (on) => set({ curvature: on }),
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
    if (wasAbove30 === nowAbove30) return { freqGhz: v }

    // Crossing the 30 GHz boundary: swap 4 cm² <-> 1 cm² defaults
    const next = new Set(state.enabledQuantities)
    let displayQuantity = state.displayQuantity
    if (nowAbove30) {
      if (next.has('sab_4cm2')) { next.delete('sab_4cm2'); next.add('sab_1cm2') }
      if (displayQuantity === 'sab_4cm2') displayQuantity = 'sab_1cm2'
    } else {
      if (next.has('sab_1cm2')) { next.delete('sab_1cm2'); next.add('sab_4cm2') }
      if (displayQuantity === 'sab_1cm2') displayQuantity = 'sab_4cm2'
    }
    return { freqGhz: v, enabledQuantities: next, displayQuantity }
  }),
  setEnabledQuantities: (q) => set({ enabledQuantities: q }),
  toggleQuantity: (key) => set((state) => {
    const next = new Set(state.enabledQuantities)
    if (next.has(key)) {
      next.delete(key)
      if (state.displayQuantity === key) return { enabledQuantities: next, displayQuantity: 'sab' as QuantityKey }
    } else {
      next.add(key)
    }
    return { enabledQuantities: next }
  }),
  setDisplayQuantity: (key) => set({ displayQuantity: key }),
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
