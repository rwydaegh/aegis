export type Archetype = 'mmimo' | 'sector' | 'small_cell'

export interface ClassificationConfig {
  element_gain_dbi: number
  mmimo_gain_threshold: number
  small_cell_gain_threshold: number
  standard_grids: Record<Archetype, [number, number][]>
  default_freq_mhz: number
}

export const DEFAULT_CLASSIFICATION_CONFIG: ClassificationConfig = {
  element_gain_dbi: 5.0,
  mmimo_gain_threshold: 20.0,
  small_cell_gain_threshold: 10.0,
  standard_grids: {
    mmimo: [[4, 4], [4, 8], [8, 8], [8, 16]],
    sector: [[1, 2], [1, 4], [2, 4], [2, 8]],
    small_cell: [[1, 1], [2, 2]],
  },
  default_freq_mhz: 2100,
}

export function classifyAntenna(
  gainDbi: number,
  technology: string | null | undefined,
  config: ClassificationConfig = DEFAULT_CLASSIFICATION_CONFIG,
): Archetype {
  const tech = (technology ?? '').toUpperCase()
  const is5G = tech.includes('5G')

  if (gainDbi >= config.mmimo_gain_threshold && is5G) return 'mmimo'
  if (gainDbi < config.small_cell_gain_threshold) return 'small_cell'
  return 'sector'
}

export function inferElementGrid(
  archetype: Archetype,
  gainDbi: number,
  config: ClassificationConfig = DEFAULT_CLASSIFICATION_CONFIG,
): [number, number] {
  const candidates = config.standard_grids[archetype] ?? [[1, 1]]
  const arrayGainDb = gainDbi - config.element_gain_dbi
  if (arrayGainDb <= 0) return candidates[0]

  const nRaw = 10 ** (arrayGainDb / 10)

  let best = candidates[0]
  let bestDist = Infinity
  for (const grid of candidates) {
    const nTotal = grid[0] * grid[1]
    const dist = Math.abs(nTotal - nRaw)
    if (dist < bestDist) {
      bestDist = dist
      best = grid
    }
  }
  return best
}

export function computePanelDimensions(
  nH: number,
  nV: number,
  freqMhz: number,
  margin = 0.02,
  defaultFreqMhz = 2100,
): { width: number; height: number } {
  const freq = freqMhz > 0 ? freqMhz : defaultFreqMhz
  const c = 299_792_458
  const wavelength = c / (freq * 1e6)
  const spacing = wavelength / 2

  const width = Math.max((nH - 1) * spacing + margin, margin * 2)
  const height = Math.max((nV - 1) * spacing + margin, margin * 2)
  return { width, height }
}
