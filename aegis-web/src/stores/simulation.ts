import { create } from 'zustand'
import type { ScenePos } from '@/api/coordinates'
import type { DosimetryStats } from '@/api/types'

interface SimulationStore {
  // Inputs
  antennaPos: ScenePos | null
  level: number
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
  setLevel: (level: number) => void
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
  level: 2,
  powerDbm: 30,
  tissue: 'skin_28ghz',
  nPaths: 1,
  bodyOffset: [0, 0, 0],
  bodyRotationY: 0,
  sabArray: null,
  stats: null,
  setAntennaPos: (pos) => set({ antennaPos: pos }),
  setLevel: (level) => set({ level }),
  setPowerDbm: (power) => set({ powerDbm: power }),
  setTissue: (tissue) => set({ tissue }),
  setNPaths: (n) => set({ nPaths: n }),
  setBodyOffset: (offset) => set({ bodyOffset: offset }),
  setBodyRotationY: (angle) => set({ bodyRotationY: angle }),
  setResults: (sab, stats) => set({ sabArray: sab, stats }),
  clearResults: () => set({ sabArray: null, stats: null }),
}))
