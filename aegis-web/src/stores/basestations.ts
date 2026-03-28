import { create } from 'zustand'
import type { BaseStationData } from '@/api/basestations'

interface BaseStationsState {
  basestations: BaseStationData[]
  origin: { lat: number; lon: number } | null
  isLoading: boolean
  isComputing: boolean
  enabledOperators: Set<string>
  enabledTechnologies: Set<string>
  operators: string[]
  technologies: string[]
  activeCount: number

  setBasestations: (bs: BaseStationData[], origin: { lat: number; lon: number }) => void
  toggleOperator: (op: string) => void
  toggleTechnology: (tech: string) => void
  setLoading: (v: boolean) => void
  setComputing: (v: boolean) => void
  clear: () => void
  activeIndices: () => number[]
}

function deriveFilters(bs: BaseStationData[]) {
  const operators = [...new Set(bs.map(b => b.operator))].sort()
  const technologies = [...new Set(bs.map(b => b.technology))].sort()
  return { operators, technologies }
}

function computeActiveCount(
  bs: BaseStationData[],
  enabledOps: Set<string>,
  enabledTechs: Set<string>,
): number {
  return bs.filter(b => enabledOps.has(b.operator) && enabledTechs.has(b.technology)).length
}

export const useBaseStationsStore = create<BaseStationsState>((set, get) => ({
  basestations: [],
  origin: null,
  isLoading: false,
  isComputing: false,
  enabledOperators: new Set<string>(),
  enabledTechnologies: new Set<string>(),
  operators: [],
  technologies: [],
  activeCount: 0,

  setBasestations: (bs, origin) => {
    const { operators, technologies } = deriveFilters(bs)
    const enabledOperators = new Set(operators)
    const enabledTechnologies = new Set(technologies)
    set({
      basestations: bs,
      origin,
      operators,
      technologies,
      enabledOperators,
      enabledTechnologies,
      activeCount: bs.length,
    })
  },

  toggleOperator: (op) => set(state => {
    const next = new Set(state.enabledOperators)
    if (next.has(op)) next.delete(op)
    else next.add(op)
    return {
      enabledOperators: next,
      activeCount: computeActiveCount(state.basestations, next, state.enabledTechnologies),
    }
  }),

  toggleTechnology: (tech) => set(state => {
    const next = new Set(state.enabledTechnologies)
    if (next.has(tech)) next.delete(tech)
    else next.add(tech)
    return {
      enabledTechnologies: next,
      activeCount: computeActiveCount(state.basestations, state.enabledOperators, next),
    }
  }),

  setLoading: (v) => set({ isLoading: v }),
  setComputing: (v) => set({ isComputing: v }),

  clear: () => set({
    basestations: [],
    origin: null,
    enabledOperators: new Set(),
    enabledTechnologies: new Set(),
    operators: [],
    technologies: [],
    activeCount: 0,
  }),

  activeIndices: () => {
    const { basestations, enabledOperators, enabledTechnologies } = get()
    const indices: number[] = []
    for (let i = 0; i < basestations.length; i++) {
      const b = basestations[i]
      if (enabledOperators.has(b.operator) && enabledTechnologies.has(b.technology)) {
        indices.push(i)
      }
    }
    return indices
  },
}))
