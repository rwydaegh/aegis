import { describe, it, expect } from 'vitest'
import {
  activeOrientationKey,
  arraySizeHasRayPack,
  beamAvailability,
  beamDescription,
  beamOptions,
  bodyMapHasPack,
  bodyMapStem,
  channelHasPack,
  channelStem,
  conditionHasRayPack,
  ensembleHasPack,
  EXTENT_OPTIONS_M,
  extentLabel,
  FIELD_QUANTITY_OPTIONS,
  frameProvenance,
  ORIENTATION_OPTIONS,
  orientationPatch,
  packsOf,
  phantomHasPack,
  qopStem,
  rayPackStem,
  reconcileBodyMapQuantity,
} from '../panels/controls'
import type { StudioManifest, StudioPacks } from '../api'

const PACKS: StudioPacks = {
  rays: ['bs16_los_seed0', 'bs16_los_seed1', 'bs16_los_seed5', 'bs16_los_seed0_ue0'],
  phantom: ['thelonious', 'duke', 'thelonious_ue0'],
  bodymaps: ['thelonious_los_bs16_mrt_10', 'thelonious_los_bs16_worstcase_10', 'thelonious_los_bs16_mrt_28'],
  ensemble: ['thelonious_los_bs16_mrt_28_mean6', 'thelonious_los_bs16_mrt_28_p95'],
  qop: ['thelonious_los_bs16_10', 'thelonious_los_bs16_28'],
  channel: [
    'thelonious_los_bs16_10_seed0',
    'thelonious_los_bs16_28_seed0',
    'thelonious_nlos_bs16_10_seed0',
    'thelonious_los_bs16_10_seed0_ue0',
  ],
}

function manifest(extra: Partial<StudioManifest> = {}): StudioManifest {
  return {
    phantoms: ['thelonious', 'duke'],
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
    expect(bodyMapStem('thelonious', 'los', 16, 'mrt', 10)).toBe('thelonious_los_bs16_mrt_10')
    expect(bodyMapStem('duke', 'los', 16, 'worstcase', 28)).toBe('duke_los_bs16_worstcase_28')
  })
})

describe('phantomHasPack', () => {
  it('enables a phantom whose geometry pack ships', () => {
    expect(phantomHasPack(PACKS, 'thelonious')).toBe(true)
    expect(phantomHasPack(PACKS, 'duke')).toBe(true)
  })

  it('disables a phantom with no geometry pack yet', () => {
    expect(phantomHasPack(PACKS, 'ella')).toBe(false)
    expect(phantomHasPack(PACKS, 'eartha')).toBe(false)
  })
})

describe('reconcileBodyMapQuantity', () => {
  it('falls back to mrt when the live map is selected but unavailable', () => {
    expect(
      reconcileBodyMapQuantity({ current: 'deposited', preferDeposited: true, liveAvailable: false }),
    ).toBe('mrt')
  })

  it('promotes back to deposited once the channel pack returns and the preference holds', () => {
    expect(
      reconcileBodyMapQuantity({ current: 'mrt', preferDeposited: true, liveAvailable: true }),
    ).toBe('deposited')
  })

  it('leaves a static quantity alone when the user opted out of the live map', () => {
    expect(
      reconcileBodyMapQuantity({ current: 'mrt', preferDeposited: false, liveAvailable: true }),
    ).toBeNull()
  })

  it('leaves the live map alone when it is available', () => {
    expect(
      reconcileBodyMapQuantity({ current: 'deposited', preferDeposited: true, liveAvailable: true }),
    ).toBeNull()
  })

  it('does not promote a static quantity the user picked while the live map is down', () => {
    expect(
      reconcileBodyMapQuantity({ current: 'worstcase', preferDeposited: false, liveAvailable: false }),
    ).toBeNull()
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

describe('arraySizeHasRayPack', () => {
  it('enables an array size that ships a ray pack at the current condition', () => {
    expect(arraySizeHasRayPack(PACKS, 16, 'los')).toBe(true)
  })

  it('disables an array size with no ray pack yet (bs8 not built)', () => {
    expect(arraySizeHasRayPack(PACKS, 8, 'los')).toBe(false)
  })

  it('disables when the condition has no ray pack at that array size', () => {
    expect(arraySizeHasRayPack(PACKS, 16, 'nlos')).toBe(false)
  })
})

describe('bodyMapHasPack', () => {
  it('enables a quantity whose pack exists at the current frequency', () => {
    expect(bodyMapHasPack(PACKS, 'thelonious', 'los', 16, 'mrt', 10)).toBe(true)
    expect(bodyMapHasPack(PACKS, 'thelonious', 'los', 16, 'mrt', 28)).toBe(true)
  })

  it('disables a quantity with no pack at this frequency', () => {
    expect(bodyMapHasPack(PACKS, 'thelonious', 'los', 16, 'worstcase', 28)).toBe(false)
    expect(bodyMapHasPack(PACKS, 'thelonious', 'los', 16, 'floor', 10)).toBe(false)
    expect(bodyMapHasPack(PACKS, 'thelonious', 'los', 16, 'amp', 10)).toBe(false)
  })

  it('disables a quantity for a phantom with no packs (duke ships geometry only)', () => {
    expect(bodyMapHasPack(PACKS, 'duke', 'los', 16, 'mrt', 10)).toBe(false)
  })
})

describe('channelStem / channelHasPack', () => {
  it('builds the seed-bearing channel stem', () => {
    expect(channelStem('thelonious', 'los', 16, 10, 0)).toBe('thelonious_los_bs16_10_seed0')
    expect(channelStem('thelonious', 'nlos', 16, 28, 3)).toBe('thelonious_nlos_bs16_28_seed3')
  })

  it('is true only when the channel pack for the seed exists', () => {
    expect(channelHasPack(PACKS, 'thelonious', 'los', 16, 10, 0)).toBe(true)
    expect(channelHasPack(PACKS, 'thelonious', 'los', 16, 28, 0)).toBe(true)
    expect(channelHasPack(PACKS, 'thelonious', 'nlos', 16, 10, 0)).toBe(true)
  })

  it('is false for a seed / freq / condition / mesh without a channel pack', () => {
    expect(channelHasPack(PACKS, 'thelonious', 'los', 16, 10, 3)).toBe(false)
    expect(channelHasPack(PACKS, 'thelonious', 'los', 16, 12, 0)).toBe(false)
    expect(channelHasPack(PACKS, 'thelonious', 'nlos', 16, 28, 0)).toBe(false)
    expect(channelHasPack(PACKS, 'duke', 'los', 16, 10, 0)).toBe(false)
  })

  it('omits the UE suffix for the default UE (4) and appends it otherwise', () => {
    // Default UE keeps the original unsuffixed stem (the grid stays valid).
    expect(channelStem('thelonious', 'los', 16, 10, 0, 4)).toBe('thelonious_los_bs16_10_seed0')
    expect(channelStem('thelonious', 'los', 16, 10, 0)).toBe('thelonious_los_bs16_10_seed0')
    // Non-default UEs carry a _ue{idx} suffix.
    expect(channelStem('thelonious', 'los', 16, 10, 0, 0)).toBe('thelonious_los_bs16_10_seed0_ue0')
    expect(channelStem('thelonious', 'nlos', 16, 28, 3, 7)).toBe('thelonious_nlos_bs16_28_seed3_ue7')
  })

  it('gates the live map per UE position', () => {
    // The default-UE channel ships; UE 0 ships its suffixed channel; UE 1 does not.
    expect(channelHasPack(PACKS, 'thelonious', 'los', 16, 10, 0, 4)).toBe(true)
    expect(channelHasPack(PACKS, 'thelonious', 'los', 16, 10, 0, 0)).toBe(true)
    expect(channelHasPack(PACKS, 'thelonious', 'los', 16, 10, 0, 1)).toBe(false)
  })
})

describe('phantomHasPack per UE', () => {
  it('finds the unsuffixed pack at the default UE and the suffixed pack otherwise', () => {
    expect(phantomHasPack(PACKS, 'thelonious')).toBe(true)
    expect(phantomHasPack(PACKS, 'thelonious', 4)).toBe(true)
    expect(phantomHasPack(PACKS, 'thelonious', 0)).toBe(true)
    expect(phantomHasPack(PACKS, 'thelonious', 1)).toBe(false)
    expect(phantomHasPack(PACKS, 'duke', 0)).toBe(false)
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
    expect(qopStem('thelonious', 'los', 16, 10)).toBe('thelonious_los_bs16_10')
    expect(qopStem('thelonious', 'los', 16, 28)).toBe('thelonious_los_bs16_28')
  })
})

describe('beamAvailability', () => {
  it('enables a Phase 1 beam wherever its ray pack ships', () => {
    expect(beamAvailability(PACKS, 'mrt', 'thelonious', 'los', 16, 28).available).toBe(true)
    expect(beamAvailability(PACKS, 'worstcase', 'thelonious', 'los', 16, 10).available).toBe(true)
  })

  it('disables any beam when the condition has no ray pack', () => {
    const a = beamAvailability(PACKS, 'mrt', 'thelonious', 'nlos', 16, 28)
    expect(a.available).toBe(false)
    expect(a.hint).toBe('no ray pack')
  })

  it('enables ECBF only where a Q pack ships at this frequency', () => {
    expect(beamAvailability(PACKS, 'ecbf', 'thelonious', 'los', 16, 28).available).toBe(true)
    const a = beamAvailability(PACKS, 'ecbf', 'thelonious', 'los', 16, 20)
    expect(a.available).toBe(false)
    expect(a.hint).toBe('no Q pack at this freq')
  })

  it('disables ECBF for a phantom without its Q pack (duke)', () => {
    const a = beamAvailability(PACKS, 'ecbf', 'duke', 'los', 16, 28)
    expect(a.available).toBe(false)
    expect(a.hint).toBe('no Q pack at this freq')
  })
})

describe('ensembleHasPack', () => {
  it('always allows the single realisation', () => {
    expect(ensembleHasPack(PACKS, 'single', 'thelonious', 'los', 16, 'amp', 12)).toBe(true)
  })

  it('enables mean / p95 only where the ensemble pack ships (LOS, that quantity + freq)', () => {
    expect(ensembleHasPack(PACKS, 'mean', 'thelonious', 'los', 16, 'mrt', 28)).toBe(true)
    expect(ensembleHasPack(PACKS, 'p95', 'thelonious', 'los', 16, 'mrt', 28)).toBe(true)
  })

  it('disables mean / p95 where no ensemble pack ships', () => {
    expect(ensembleHasPack(PACKS, 'mean', 'thelonious', 'los', 16, 'mrt', 10)).toBe(false)
    expect(ensembleHasPack(PACKS, 'p95', 'thelonious', 'los', 16, 'worstcase', 28)).toBe(false)
    expect(ensembleHasPack(PACKS, 'mean', 'thelonious', 'nlos', 16, 'mrt', 28)).toBe(false)
    expect(ensembleHasPack(PACKS, 'mean', 'duke', 'los', 16, 'mrt', 28)).toBe(false)
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

describe('slice orientation presets', () => {
  it('maps anatomical planes to fixed world-axis normals via a free plane', () => {
    expect(orientationPatch('horizontal')).toEqual({ orientation: 'free', normalXyz: [0, 0, 1] })
    expect(orientationPatch('coronal')).toEqual({ orientation: 'free', normalXyz: [1, 0, 0] })
    expect(orientationPatch('sagittal')).toEqual({ orientation: 'free', normalXyz: [0, 1, 0] })
  })

  it('keeps "facing base station" as the backend beam-normal (transverse) orientation', () => {
    expect(orientationPatch('facing-bs')).toEqual({ orientation: 'transverse' })
  })

  it('custom leaves the normal for the sliders to set', () => {
    expect(orientationPatch('free')).toEqual({ orientation: 'free' })
  })

  it('recovers the active preset key from the plane state (either normal sign)', () => {
    expect(activeOrientationKey('free', [0, 1, 0])).toBe('sagittal')
    expect(activeOrientationKey('free', [0, -1, 0])).toBe('sagittal')
    expect(activeOrientationKey('free', [0, 0, 1])).toBe('horizontal')
    expect(activeOrientationKey('free', [1, 0, 0])).toBe('coronal')
    expect(activeOrientationKey('transverse', null)).toBe('facing-bs')
    expect(activeOrientationKey('free', [1, 1, 0])).toBe('free')
    expect(activeOrientationKey('free', null)).toBe('free')
  })

  it('every orientation option carries an explanatory title', () => {
    for (const o of ORIENTATION_OPTIONS) expect(o.title.length).toBeGreaterThan(20)
  })
})

describe('beamDescription', () => {
  it('distinguishes the subtle beams', () => {
    expect(beamDescription('decohered')).toContain('phase-scrambled')
    expect(beamDescription('decoy')).toContain('6 cm')
    expect(beamDescription('ecbf')).toContain('absorbed power')
    expect(beamDescription('mrt')).toContain('Maximum-ratio')
    expect(beamDescription('unknown-beam')).toBe('unknown-beam')
  })
})
