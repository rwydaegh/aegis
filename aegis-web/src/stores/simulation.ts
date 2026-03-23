import { create } from 'zustand'
import type { ScenePos } from '@/api/coordinates'
import type { DosimetryStats } from '@/api/types'

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

  // Body physics state
  bodyOffset: ScenePos
  bodyRotationY: number

  // Results
  sabArray: Float32Array | null
  stats: DosimetryStats | null

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
  setBodyOffset: (offset: ScenePos) => void
  setBodyRotationY: (angle: number) => void
  setResults: (sab: Float32Array, stats: DosimetryStats) => void
  clearResults: () => void
}

export const useSimulationStore = create<SimulationStore>((set) => ({
  antennaPos: null,
  mode: 'spatial',
  fresnel: true,
  polarisation: false,
  curvature: false,
  diffraction: false,
  powerDbm: 30,
  tissue: 'skin_28ghz',
  nPaths: 1,
  bodyOffset: [0, 0, 0],
  bodyRotationY: 0,
  sabArray: null,
  stats: null,
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
  setBodyOffset: (offset) => set({ bodyOffset: offset }),
  setBodyRotationY: (angle) => set({ bodyRotationY: angle }),
  setResults: (sab, stats) => set({ sabArray: sab, stats }),
  clearResults: () => set({ sabArray: null, stats: null }),
}))
