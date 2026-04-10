import { create } from 'zustand'
import type { ScenePos } from '@/api/coordinates'
import type { ElementPattern } from '@/api/types'

export interface AntennaArrayConfig {
  n_h: number
  n_v: number
  d_h_wavelengths: number
  d_v_wavelengths: number
  broadside: [number, number, number]
  element_pattern: ElementPattern
}

export interface AntennaConfig {
  id: string
  name: string
  position: ScenePos
  powerDbm: number
  arrayConfig: AntennaArrayConfig
  enabled: boolean
}

interface AntennaStore {
  antennas: Map<string, AntennaConfig>
  selectedId: string | null
  _nextNumber: number

  addAntenna: (position: ScenePos) => string
  removeAntenna: (id: string) => void
  updateAntenna: (id: string, partial: Partial<AntennaConfig>) => void
  selectAntenna: (id: string | null) => void
  moveAntenna: (id: string, position: ScenePos) => void
  setEnabled: (id: string, on: boolean) => void
  selectedAntenna: () => AntennaConfig | null
  enabledAntennas: () => AntennaConfig[]
}

function defaultArrayConfig(): AntennaArrayConfig {
  return {
    n_h: 1, n_v: 1,
    d_h_wavelengths: 0.5, d_v_wavelengths: 0.5,
    broadside: [0, 0, -1],
    element_pattern: 'short_dipole',
  }
}

export const useAntennaStore = create<AntennaStore>((set, get) => ({
  antennas: new Map(),
  selectedId: null,
  _nextNumber: 1,

  addAntenna: (position) => {
    const state = get()
    const num = state._nextNumber
    const id = `ant_${num}`
    const antenna: AntennaConfig = {
      id, name: `Antenna ${num}`, position,
      powerDbm: 60, arrayConfig: defaultArrayConfig(), enabled: true,
    }
    const next = new Map(state.antennas)
    next.set(id, antenna)
    set({ antennas: next, selectedId: id, _nextNumber: num + 1 })
    return id
  },

  removeAntenna: (id) => {
    const state = get()
    const next = new Map(state.antennas)
    next.delete(id)
    let selectedId = state.selectedId
    if (selectedId === id) {
      const remaining = [...next.keys()]
      selectedId = remaining.length > 0 ? remaining[remaining.length - 1] : null
    }
    set({ antennas: next, selectedId })
  },

  updateAntenna: (id, partial) => {
    const state = get()
    const existing = state.antennas.get(id)
    if (!existing) return
    const next = new Map(state.antennas)
    next.set(id, { ...existing, ...partial })
    set({ antennas: next })
  },

  selectAntenna: (id) => set({ selectedId: id }),

  moveAntenna: (id, position) => {
    const state = get()
    const existing = state.antennas.get(id)
    if (!existing) return
    const next = new Map(state.antennas)
    next.set(id, { ...existing, position })
    set({ antennas: next })
  },

  setEnabled: (id, on) => {
    const state = get()
    const existing = state.antennas.get(id)
    if (!existing) return
    const next = new Map(state.antennas)
    next.set(id, { ...existing, enabled: on })
    set({ antennas: next })
  },

  selectedAntenna: () => {
    const state = get()
    if (!state.selectedId) return null
    return state.antennas.get(state.selectedId) ?? null
  },

  enabledAntennas: () => {
    return [...get().antennas.values()].filter(a => a.enabled)
  },
}))
