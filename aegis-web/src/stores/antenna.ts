import { create } from 'zustand'
import type { ScenePos } from '@/api/coordinates'
import type { ElementPattern } from '@/api/types'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'

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
  height: number
  focusPoint: [number, number, number] | null
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
  clearAntennas: () => void
  updateAntenna: (id: string, partial: Partial<AntennaConfig>) => void
  selectAntenna: (id: string | null) => void
  moveAntenna: (id: string, position: ScenePos) => void
  setEnabled: (id: string, on: boolean) => void
  setFocusPoint: (id: string, fp: [number, number, number] | null) => void
  setHeight: (id: string, height: number) => void
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

/** Compute broadside unit vector from antenna tip toward focus point. */
export function deriveBroadside(
  focusPoint: [number, number, number] | null,
  position: ScenePos,
  height: number,
): [number, number, number] {
  if (!focusPoint) return [0, 0, -1]
  const tip: [number, number, number] = [position[0], position[1] + height, position[2]]
  const dx = focusPoint[0] - tip[0]
  const dy = focusPoint[1] - tip[1]
  const dz = focusPoint[2] - tip[2]
  const len = Math.sqrt(dx * dx + dy * dy + dz * dz)
  if (len < 1e-6) return [0, 0, -1]
  return [dx / len, dy / len, dz / len]
}

export const useAntennaStore = create<AntennaStore>((set, get) => ({
  antennas: new Map(),
  selectedId: null,
  _nextNumber: 1,

  addAntenna: (position) => {
    const state = get()
    const num = state._nextNumber
    const id = `ant_${num}`
    const sceneConfig = useSceneStore?.getState?.()?.viewerConfig
    const defaultHeight = sceneConfig?.antenna?.pole_height ?? 2
    const simState = useSimulationStore?.getState?.()
    const bodyOffset = simState?.bodyOffset ?? null
    const focusPoint: [number, number, number] | null = bodyOffset ? [...bodyOffset] as [number, number, number] : null
    const broadside = deriveBroadside(focusPoint, position, defaultHeight)
    const antenna: AntennaConfig = {
      id, name: `Antenna ${num}`, position,
      height: defaultHeight,
      focusPoint,
      powerDbm: 43,
      arrayConfig: { ...defaultArrayConfig(), broadside },
      enabled: true,
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

  clearAntennas: () => set({ antennas: new Map(), selectedId: null, _nextNumber: 1 }),

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
    const broadside = deriveBroadside(existing.focusPoint, position, existing.height)
    const next = new Map(state.antennas)
    next.set(id, { ...existing, position, arrayConfig: { ...existing.arrayConfig, broadside } })
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

  setFocusPoint: (id, fp) => {
    const state = get()
    const ant = state.antennas.get(id)
    if (!ant) return
    const broadside = deriveBroadside(fp, ant.position, ant.height)
    const next = new Map(state.antennas)
    next.set(id, { ...ant, focusPoint: fp, arrayConfig: { ...ant.arrayConfig, broadside } })
    set({ antennas: next })
  },

  setHeight: (id, height) => {
    const state = get()
    const ant = state.antennas.get(id)
    if (!ant) return
    const broadside = deriveBroadside(ant.focusPoint, ant.position, height)
    const next = new Map(state.antennas)
    next.set(id, { ...ant, height, arrayConfig: { ...ant.arrayConfig, broadside } })
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
