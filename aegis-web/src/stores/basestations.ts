import { create } from 'zustand'
import type { BaseStationData } from '@/api/basestations'

export type AntennaColorMode = 'operator' | 'fidelity' | 'technology' | 'frequency_band'

interface BaseStationsState {
  basestations: BaseStationData[]
  origin: { lat: number; lon: number } | null
  isLoading: boolean
  isComputing: boolean
  enabledOperators: Set<string>
  enabledTechnologies: Set<string>
  enabledFrequencyBands: Set<string>
  operators: string[]
  technologies: string[]
  frequencyBands: string[]
  activeCount: number
  colorMode: AntennaColorMode

  selectedIndex: number | null
  selectAntenna: (index: number | null) => void

  setBasestations: (bs: BaseStationData[], origin: { lat: number; lon: number }) => void
  toggleOperator: (op: string) => void
  toggleTechnology: (tech: string) => void
  toggleFrequencyBand: (band: string) => void
  setColorMode: (mode: AntennaColorMode) => void
  setLoading: (v: boolean) => void
  setComputing: (v: boolean) => void
  clear: () => void
  activeIndices: () => number[]
}

function deriveFilters(bs: BaseStationData[]) {
  const operators = [...new Set(bs.map(b => b.operator))].sort()
  const technologies = [...new Set(bs.map(b => b.technology))].sort()
  const frequencyBands = [...new Set(bs.map(b => b.frequency_band).filter((v): v is string => !!v))].sort()
  return { operators, technologies, frequencyBands }
}

function computeActiveCount(
  bs: BaseStationData[],
  enabledOps: Set<string>,
  enabledTechs: Set<string>,
  enabledBands: Set<string>,
): number {
  return bs.filter(b => {
    if (!enabledOps.has(b.operator)) return false
    if (!enabledTechs.has(b.technology)) return false
    // Antennas without a frequency_band aren't filterable by band, so keep them;
    // antennas with a band must be in the enabled set (unchecking all hides them).
    if (b.frequency_band && !enabledBands.has(b.frequency_band)) return false
    return true
  }).length
}

export const useBaseStationsStore = create<BaseStationsState>((set, get) => ({
  basestations: [],
  origin: null,
  isLoading: false,
  isComputing: false,
  enabledOperators: new Set<string>(),
  enabledTechnologies: new Set<string>(),
  enabledFrequencyBands: new Set<string>(),
  operators: [],
  technologies: [],
  frequencyBands: [],
  activeCount: 0,
  colorMode: 'operator' as AntennaColorMode,
  selectedIndex: null,
  selectAntenna: (index) => set({ selectedIndex: index }),

  setBasestations: (bs, origin) => {
    const { operators, technologies, frequencyBands } = deriveFilters(bs)
    const enabledOperators = new Set(operators)
    const enabledTechnologies = new Set(technologies)
    const enabledFrequencyBands = new Set(frequencyBands)
    set({
      basestations: bs,
      origin,
      operators,
      technologies,
      frequencyBands,
      enabledOperators,
      enabledTechnologies,
      enabledFrequencyBands,
      activeCount: bs.length,
    })
  },

  toggleOperator: (op) => set(state => {
    const next = new Set(state.enabledOperators)
    if (next.has(op)) next.delete(op)
    else next.add(op)
    return {
      enabledOperators: next,
      activeCount: computeActiveCount(state.basestations, next, state.enabledTechnologies, state.enabledFrequencyBands),
    }
  }),

  toggleTechnology: (tech) => set(state => {
    const next = new Set(state.enabledTechnologies)
    if (next.has(tech)) next.delete(tech)
    else next.add(tech)
    return {
      enabledTechnologies: next,
      activeCount: computeActiveCount(state.basestations, state.enabledOperators, next, state.enabledFrequencyBands),
    }
  }),

  toggleFrequencyBand: (band) => set(state => {
    const next = new Set(state.enabledFrequencyBands)
    if (next.has(band)) next.delete(band)
    else next.add(band)
    return {
      enabledFrequencyBands: next,
      activeCount: computeActiveCount(state.basestations, state.enabledOperators, state.enabledTechnologies, next),
    }
  }),

  setColorMode: (mode) => set({ colorMode: mode }),

  setLoading: (v) => set({ isLoading: v }),
  setComputing: (v) => set({ isComputing: v }),

  clear: () => set({
    basestations: [],
    origin: null,
    isLoading: false,
    isComputing: false,
    enabledOperators: new Set(),
    enabledTechnologies: new Set(),
    enabledFrequencyBands: new Set(),
    operators: [],
    technologies: [],
    frequencyBands: [],
    activeCount: 0,
    colorMode: 'operator' as AntennaColorMode,
    selectedIndex: null,
  }),

  activeIndices: () => {
    const { basestations, enabledOperators, enabledTechnologies, enabledFrequencyBands } = get()
    const indices: number[] = []
    for (let i = 0; i < basestations.length; i++) {
      const b = basestations[i]
      if (!enabledOperators.has(b.operator)) continue
      if (!enabledTechnologies.has(b.technology)) continue
      if (b.frequency_band && !enabledFrequencyBands.has(b.frequency_band)) continue
      indices.push(i)
    }
    return indices
  },
}))
