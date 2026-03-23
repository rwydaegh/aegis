import { create } from 'zustand'
import type { ScenePos } from '@/api/coordinates'
import type { DosimetryStats, QuantityKey } from '@/api/types'

export type DosimetryMode = 'bound' | 'aggregate' | 'spatial'

interface SimulationStore {
  // Inputs
  antennaPos: ScenePos | null
  mode: DosimetryMode
  fresnel: boolean
  polarisation: boolean
  curvature: boolean
  diffraction: boolean
  powerDbm: number
  tissue: string
  nPaths: number
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

  // Inputs (compliance)
  freqGhz: number
  enabledQuantities: Set<QuantityKey>
  displayQuantity: QuantityKey

  // Actions
  setAntennaPos: (pos: ScenePos | null) => void
  setMode: (mode: DosimetryMode) => void
  setFresnel: (on: boolean) => void
  setPolarisation: (on: boolean) => void
  setCurvature: (on: boolean) => void
  setDiffraction: (on: boolean) => void
  setPowerDbm: (power: number) => void
  setTissue: (tissue: string) => void
  setNPaths: (n: number) => void
  setStochasticPreset: (v: string) => void
  setStochasticOverrides: (v: Record<string, number>) => void
  setStochasticSeed: (v: number) => void
  setBodyOffset: (offset: ScenePos) => void
  setBodyRotationY: (angle: number) => void
  setFreqGhz: (v: number) => void
  setEnabledQuantities: (q: Set<QuantityKey>) => void
  toggleQuantity: (key: QuantityKey) => void
  setDisplayQuantity: (key: QuantityKey) => void
  setResults: (sab: Float32Array, stats: DosimetryStats, extras?: {
    sabAveraged?: Float32Array; sinc?: Float32Array; sincAveraged?: Float32Array; sab1cm2Averaged?: Float32Array
  }) => void
  clearResults: () => void
}

export const useSimulationStore = create<SimulationStore>((set) => ({
  antennaPos: null,
  mode: 'spatial',
  fresnel: true,
  polarisation: false,
  curvature: false,
  diffraction: false,
  powerDbm: 60,
  tissue: 'skin_28ghz',
  nPaths: 1,
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
  freqGhz: 28,
  enabledQuantities: new Set<QuantityKey>(['sab', 'sab_4cm2']),
  displayQuantity: 'sab' as QuantityKey,
  setAntennaPos: (pos) => set({ antennaPos: pos }),
  setMode: (mode) => set({ mode }),
  setFresnel: (on) => set({ fresnel: on }),
  setPolarisation: (on) => set({ polarisation: on }),
  setCurvature: (on) => set({ curvature: on }),
  setDiffraction: (on) => set(() => {
    // Diffraction requires curvature data, so auto-enable it
    if (on) return { diffraction: true, curvature: true }
    return { diffraction: false }
  }),
  setPowerDbm: (power) => set({ powerDbm: power }),
  setTissue: (tissue) => set({ tissue }),
  setNPaths: (n) => set({ nPaths: n }),
  setStochasticPreset: (v) => set({ stochasticPreset: v }),
  setStochasticOverrides: (v) => set({ stochasticOverrides: v }),
  setStochasticSeed: (v) => set({ stochasticSeed: v }),
  setBodyOffset: (offset) => set({ bodyOffset: offset }),
  setBodyRotationY: (angle) => set({ bodyRotationY: angle }),
  setFreqGhz: (v) => set({ freqGhz: v }),
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
  setResults: (sab, stats, extras) => set({
    sabArray: sab,
    stats,
    sabAveragedArray: extras?.sabAveraged ?? null,
    sincArray: extras?.sinc ?? null,
    sincAveragedArray: extras?.sincAveraged ?? null,
    sab1cm2AveragedArray: extras?.sab1cm2Averaged ?? null,
  }),
  clearResults: () => set({ sabArray: null, sabAveragedArray: null, sincArray: null, sincAveragedArray: null, sab1cm2AveragedArray: null, stats: null }),
}))
