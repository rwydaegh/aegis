import { describe, it, expect } from 'vitest'
import {
  beamAvailability,
  beamOptions,
  bodyMapHasPack,
  bodyMapStem,
  conditionHasRayPack,
  EXTENT_OPTIONS_M,
  extentLabel,
  FIELD_QUANTITY_OPTIONS,
  frameProvenance,
  packsOf,
  qopStem,
  rayPackStem,
} from '../panels/controls'
import type { StudioManifest, StudioPacks } from '../api'

const PACKS: StudioPacks = {
  rays: ['bs16_los_seed0', 'bs16_los_seed1', 'bs16_los_seed5'],
  phantom: ['thelonious'],
  bodymaps: ['los_bs16_mrt_10', 'los_bs16_worstcase_10', 'los_bs16_mrt_28'],
  ensemble: [],
  qop: ['los_bs16_10', 'los_bs16_28'],
}

function manifest(extra: Partial<StudioManifest> = {}): StudioManifest {
  return {
    phantoms: ['thelonious'],
    conditions: ['los', 'nlos'],
    frequencies: [8, 10, 12, 15, 20, 28],
    seeds: [0, 1, 2, 3, 4, 5],
    array_sizes: [16],
    beams: ['mrt', 'unfocused', 'decohered', 'decoy', 'worstcase', 'ecbf'],
    body_map_quantities: ['floor', 'mrt', 'worstcase', 'amp'],
    packs: PACKS,
    default_scene: {},
    ...extra,
  }
}

describe('extentLabel', () => {
  it('labels sub-metre extents in centimetres', () => {
    expect(extentLabel(0.04)).toBe('4 cm')
    expect(extentLabel(0.08)).toBe('8 cm')
    expect(extentLabel(0.16)).toBe('16 cm')
    expect(extentLabel(0.4)).toBe('40 cm')
    expect(extentLabel(0.8)).toBe('80 cm')
  })

  it('labels metre-and-up extents in metres, trimming trailing zeros', () => {
    expect(extentLabel(1.6)).toBe('1.6 m')
    expect(extentLabel(2.56)).toBe('2.56 m')
  })

  it('every catalogue extent gets a finite label', () => {
    for (const m of EXTENT_OPTIONS_M) {
      expect(extentLabel(m)).toMatch(/\d/)
    }
  })
})

describe('pack stems', () => {
  it('builds the backend ray-pack stem', () => {
    expect(rayPackStem('los', 16, 0)).toBe('bs16_los_seed0')
  })

  it('builds the backend body-map stem', () => {
    expect(bodyMapStem('los', 16, 'mrt', 10)).toBe('los_bs16_mrt_10')
    expect(bodyMapStem('los', 16, 'worstcase', 28)).toBe('los_bs16_worstcase_28')
  })
})

describe('packsOf', () => {
  it('reads typed pack lists off the manifest', () => {
    expect(packsOf(manifest()).rays).toEqual(PACKS.rays)
  })

  it('returns empty lists for a null manifest', () => {
    const p = packsOf(null)
    expect(p.rays).toEqual([])
    expect(p.bodymaps).toEqual([])
  })
})

describe('conditionHasRayPack', () => {
  it('enables a condition that ships a ray pack at the array size', () => {
    expect(conditionHasRayPack(PACKS, 'los', 16)).toBe(true)
  })

  it('disables a condition with no ray pack (NLOS today)', () => {
    expect(conditionHasRayPack(PACKS, 'nlos', 16)).toBe(false)
  })

  it('disables when the array size has no packs', () => {
    expect(conditionHasRayPack(PACKS, 'los', 64)).toBe(false)
  })
})

describe('bodyMapHasPack', () => {
  it('enables a quantity whose pack exists at the current frequency', () => {
    expect(bodyMapHasPack(PACKS, 'los', 16, 'mrt', 10)).toBe(true)
    expect(bodyMapHasPack(PACKS, 'los', 16, 'mrt', 28)).toBe(true)
  })

  it('disables a quantity with no pack at this frequency', () => {
    expect(bodyMapHasPack(PACKS, 'los', 16, 'worstcase', 28)).toBe(false)
    expect(bodyMapHasPack(PACKS, 'los', 16, 'floor', 10)).toBe(false)
    expect(bodyMapHasPack(PACKS, 'los', 16, 'amp', 10)).toBe(false)
  })
})

describe('beamOptions', () => {
  it('restricts to the beams the manifest advertises', () => {
    const opts = beamOptions(manifest({ beams: ['mrt', 'unfocused'] }))
    expect(opts.map((o) => o.value)).toEqual(['mrt', 'unfocused'])
  })

  it('falls back to the full catalogue when the manifest has no beams', () => {
    expect(beamOptions(null).length).toBeGreaterThan(0)
  })
})

describe('qopStem', () => {
  it('builds the backend exposure-operator pack stem', () => {
    expect(qopStem('los', 16, 10)).toBe('los_bs16_10')
    expect(qopStem('los', 16, 28)).toBe('los_bs16_28')
  })
})

describe('beamAvailability', () => {
  it('enables a Phase 1 beam wherever its ray pack ships', () => {
    expect(beamAvailability(PACKS, 'mrt', 'los', 16, 28).available).toBe(true)
    expect(beamAvailability(PACKS, 'worstcase', 'los', 16, 10).available).toBe(true)
  })

  it('disables any beam when the condition has no ray pack', () => {
    const a = beamAvailability(PACKS, 'mrt', 'nlos', 16, 28)
    expect(a.available).toBe(false)
    expect(a.hint).toBe('no ray pack')
  })

  it('enables ECBF only where a Q pack ships at this frequency', () => {
    expect(beamAvailability(PACKS, 'ecbf', 'los', 16, 28).available).toBe(true)
    const a = beamAvailability(PACKS, 'ecbf', 'los', 16, 20)
    expect(a.available).toBe(false)
    expect(a.hint).toBe('no Q pack at this freq')
  })
})

describe('frameProvenance', () => {
  it('reports a served body-map pack as high confidence', () => {
    const p = frameProvenance({ sliceProvenance: 'served', hasBodyMap: true, bodyMapNotPrecomputed: false })
    expect(p.confidence).toBeGreaterThan(0.7)
    expect(p.label).toBe('precomputed')
  })

  it('reports a missing body-map pack as low confidence', () => {
    const p = frameProvenance({ sliceProvenance: 'live', hasBodyMap: false, bodyMapNotPrecomputed: true })
    expect(p.confidence).toBeLessThan(0.4)
    expect(p.label).toBe('not precomputed')
  })

  it('reports a live slice with no body map at mid confidence', () => {
    const p = frameProvenance({ sliceProvenance: { kind: 'computed' }, hasBodyMap: false, bodyMapNotPrecomputed: false })
    expect(p.confidence).toBeGreaterThan(0.4)
    expect(p.confidence).toBeLessThan(0.8)
    expect(p.title).toContain('computed')
  })
})

describe('FIELD_QUANTITY_OPTIONS', () => {
  it('exposes the full Phase 2 slice quantity set the backend supports', () => {
    const values = FIELD_QUANTITY_OPTIONS.map((o) => o.value)
    expect(values).toEqual(['S', 'absE', 'absH', 'poynting', 'ReEx', 'ReEy', 'ReEz'])
  })

  it('does not offer Sab (a surface quantity served by the body-map endpoint)', () => {
    const values = FIELD_QUANTITY_OPTIONS.map((o) => o.value as string)
    expect(values).not.toContain('Sab')
  })
})
