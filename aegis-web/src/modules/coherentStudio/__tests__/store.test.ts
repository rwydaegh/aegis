import { describe, it, expect, beforeEach } from 'vitest'
import {
  useStudioStore,
  sliceFetchKey,
  bodyMapFetchKey,
  volumeFetchKey,
  complianceFetchKey,
  complianceSweepFetchKey,
  STUDIO_DEFAULTS,
} from '../store'
import { dbmToWatts, icnirpLimits, spectralEfficiency } from '../api'
import { powerDisplayFactor, quantityIsField } from '../scene/studioHelpers'

function keys() {
  const s = useStudioStore.getState()
  return { slice: sliceFetchKey(s), bodyMap: bodyMapFetchKey(s), volume: volumeFetchKey(s) }
}

describe('coherentStudio fetch keys', () => {
  beforeEach(() => {
    useStudioStore.setState({
      mesh: 'thelonious',
      condition: 'urban',
      arrayN: 16,
      seed: 0,
      beam: 'mrt',
      focusMode: 'at-skin',
      focusXyz: [0.923, -0.005, 0.734],
      frequencyGhz: 10,
      plane: { orientation: 'transverse', normalXyz: null, extentM: 0.08, res: 160 },
      fieldQuantity: 'S',
      bodyMapQuantity: 'mrt',
      colormap: 'viridis',
      scaleMode: 'auto',
      ecbfConstraintMode: 'relative',
      ecbfSarWbOn: true,
      ecbfPeakOn: true,
      txPowerDbm: 25,
    })
  })

  it('colormap is render-only: changes neither key', () => {
    const before = keys()
    useStudioStore.getState().setColormap('inferno')
    const after = keys()
    expect(after.slice).toBe(before.slice)
    expect(after.bodyMap).toBe(before.bodyMap)
  })

  it('scaleMode is render-only: changes neither key', () => {
    const before = keys()
    useStudioStore.getState().setScaleMode('log')
    const after = keys()
    expect(after.slice).toBe(before.slice)
    expect(after.bodyMap).toBe(before.bodyMap)
  })

  it('plane.res changes the slice key but not the body-map key', () => {
    const before = keys()
    useStudioStore.getState().setPlane({ res: 320 })
    const after = keys()
    expect(after.slice).not.toBe(before.slice)
    expect(after.bodyMap).toBe(before.bodyMap)
  })

  it('beam changes both keys', () => {
    const before = keys()
    useStudioStore.getState().setBeam('ecbf')
    const after = keys()
    expect(after.slice).not.toBe(before.slice)
    expect(after.bodyMap).not.toBe(before.bodyMap)
  })

  it('mesh (phantom) changes slice, body-map and volume keys', () => {
    // Switching the phantom swaps every per-body pack (channel, Q, body map) and
    // the at-skin snap target, so all three fetch keys must change.
    const before = keys()
    useStudioStore.getState().setMesh('duke')
    const after = keys()
    expect(after.slice).not.toBe(before.slice)
    expect(after.bodyMap).not.toBe(before.bodyMap)
    expect(after.volume).not.toBe(before.volume)
  })

  it('opens on the live deposited map so the body responds to focus by default', () => {
    // Regression guard: the studio's headline interaction is "move the focus,
    // watch the body recolour". That only works when the default body-map
    // quantity is the live, precoder-applied 'deposited' map, not a static
    // focus-frozen pack. Defaulting to a static pack reads as "the body map is
    // not responding to the focus".
    expect(useStudioStore.getInitialState().bodyMapQuantity).toBe('deposited')
  })

  it('static body map ignores focus, but the live deposited map tracks it', () => {
    // Default quantity (mrt) is a static pack: focus must not change its key.
    const beforeStatic = keys()
    useStudioStore.getState().setFocusXyz([0.5, 0.1, 0.8])
    expect(keys().bodyMap).toBe(beforeStatic.bodyMap)

    // The live deposited map is a function of the precoder, so focus moves drive
    // a refetch (this is the fix for "body map does not respond to the focus").
    useStudioStore.getState().setBodyMapQuantity('deposited')
    const beforeLive = keys()
    useStudioStore.getState().setFocusXyz([0.9, -0.2, 0.7])
    expect(keys().bodyMap).not.toBe(beforeLive.bodyMap)
  })

  it('toggling showVolume changes the volume key but not slice / body-map', () => {
    const before = keys()
    useStudioStore.getState().setShowVolume(true)
    const after = keys()
    expect(after.volume).not.toBe(before.volume)
    expect(after.slice).toBe(before.slice)
    expect(after.bodyMap).toBe(before.bodyMap)
  })

  it('volumeRes / volumeExtentM change the volume key only', () => {
    const before = keys()
    useStudioStore.getState().setVolumeRes(40)
    const afterRes = keys()
    expect(afterRes.volume).not.toBe(before.volume)
    expect(afterRes.slice).toBe(before.slice)

    useStudioStore.getState().setVolumeExtentM(0.4)
    const afterExtent = keys()
    expect(afterExtent.volume).not.toBe(afterRes.volume)
    expect(afterExtent.slice).toBe(before.slice)
  })

  it('toggling showCompliance changes the compliance key but not slice / body-map', () => {
    const before = { ...keys(), compliance: complianceFetchKey(useStudioStore.getState()) }
    useStudioStore.getState().setShowCompliance(true)
    const after = { ...keys(), compliance: complianceFetchKey(useStudioStore.getState()) }
    expect(after.compliance).not.toBe(before.compliance)
    expect(after.slice).toBe(before.slice)
    expect(after.bodyMap).toBe(before.bodyMap)
    expect(after.volume).toBe(before.volume)
  })

  it('compliance key tracks the beam / focus, not render-only colormap', () => {
    useStudioStore.getState().setShowCompliance(true)
    const before = complianceFetchKey(useStudioStore.getState())
    useStudioStore.getState().setColormap('magma')
    expect(complianceFetchKey(useStudioStore.getState())).toBe(before)
    useStudioStore.getState().setFocusXyz([0.4, 0.1, 0.9])
    expect(complianceFetchKey(useStudioStore.getState())).not.toBe(before)
  })

  it('budget-sweep key ignores the live budget and SNR (cursor + client-side rate)', () => {
    const s = useStudioStore.getState()
    s.setShowCompliance(true)
    s.setBeam('ecbf')
    const before = complianceSweepFetchKey(useStudioStore.getState())
    // The sweep spans every budget, so moving the slider only moves the cursor.
    s.setEcbfBudgetFrac(0.3)
    expect(complianceSweepFetchKey(useStudioStore.getState())).toBe(before)
    // Spectral efficiency is recomputed client-side, so SNR is not a fetch axis.
    s.setSnrMrtDb(5)
    expect(complianceSweepFetchKey(useStudioStore.getState())).toBe(before)
    // Focus / beam selection does change it.
    s.setFocusXyz([0.4, 0.1, 0.9])
    expect(complianceSweepFetchKey(useStudioStore.getState())).not.toBe(before)
  })

  it('budget-sweep key is gated on showCompliance AND the ecbf beam', () => {
    const s = useStudioStore.getState()
    s.setShowCompliance(true)
    s.setBeam('mrt')
    const mrtKey = complianceSweepFetchKey(useStudioStore.getState())
    s.setBeam('ecbf')
    expect(complianceSweepFetchKey(useStudioStore.getState())).not.toBe(mrtKey)
  })

  it('txPowerDbm is render-only: rescales display, triggers no re-fetch', () => {
    const s = useStudioStore.getState()
    s.setShowCompliance(true)
    s.setBeam('ecbf')
    const before = {
      ...keys(),
      compliance: complianceFetchKey(useStudioStore.getState()),
      sweep: complianceSweepFetchKey(useStudioStore.getState()),
    }
    s.setTxPowerDbm(43)
    const after = {
      ...keys(),
      compliance: complianceFetchKey(useStudioStore.getState()),
      sweep: complianceSweepFetchKey(useStudioStore.getState()),
    }
    expect(after).toEqual(before)
  })

  it('absolute mode setters update state', () => {
    const s = useStudioStore.getState()
    s.setEcbfConstraintMode('absolute')
    expect(useStudioStore.getState().ecbfConstraintMode).toBe('absolute')
    s.setEcbfSarWbOn(false)
    expect(useStudioStore.getState().ecbfSarWbOn).toBe(false)
    s.setEcbfPeakOn(false)
    expect(useStudioStore.getState().ecbfPeakOn).toBe(false)
  })

  it('switching to absolute mode changes the ECBF fetch keys', () => {
    const s = useStudioStore.getState()
    s.setBeam('ecbf')
    s.setShowCompliance(true)
    s.setBodyMapQuantity('deposited') // the live map reflects the precoder (static packs do not)
    const before = { ...keys(), compliance: complianceFetchKey(useStudioStore.getState()) }
    s.setEcbfConstraintMode('absolute')
    const after = { ...keys(), compliance: complianceFetchKey(useStudioStore.getState()) }
    expect(after.compliance).not.toBe(before.compliance)
    expect(after.slice).not.toBe(before.slice)
    expect(after.bodyMap).not.toBe(before.bodyMap)
    expect(after.volume).not.toBe(before.volume)
  })

  it('txPowerDbm enters the ECBF fetch keys ONLY in absolute mode', () => {
    const s = useStudioStore.getState()
    s.setBeam('ecbf')
    s.setShowCompliance(true)
    s.setBodyMapQuantity('deposited') // the live map reflects the precoder (static packs do not)
    // Relative mode: the dBm slider is render-only (no key change).
    const relBefore = { ...keys(), compliance: complianceFetchKey(useStudioStore.getState()) }
    s.setTxPowerDbm(43)
    const relAfter = { ...keys(), compliance: complianceFetchKey(useStudioStore.getState()) }
    expect(relAfter).toEqual(relBefore)

    // Absolute mode: the dBm slider feeds the solve, so it joins the keys.
    s.setEcbfConstraintMode('absolute')
    const absBefore = { ...keys(), compliance: complianceFetchKey(useStudioStore.getState()) }
    s.setTxPowerDbm(70)
    const absAfter = { ...keys(), compliance: complianceFetchKey(useStudioStore.getState()) }
    expect(absAfter.compliance).not.toBe(absBefore.compliance)
    expect(absAfter.slice).not.toBe(absBefore.slice)
    expect(absAfter.bodyMap).not.toBe(absBefore.bodyMap)
    expect(absAfter.volume).not.toBe(absBefore.volume)
  })

  it('restriction toggles enter the keys only in absolute mode', () => {
    const s = useStudioStore.getState()
    s.setBeam('ecbf')
    s.setShowCompliance(true)
    // Relative: toggling a restriction is inert (the budget ECBF ignores them).
    const relBefore = complianceFetchKey(useStudioStore.getState())
    s.setEcbfPeakOn(false)
    expect(complianceFetchKey(useStudioStore.getState())).toBe(relBefore)

    // Absolute: the enforced restriction set changes the solved beam.
    s.setEcbfConstraintMode('absolute')
    const absBefore = complianceFetchKey(useStudioStore.getState())
    s.setEcbfSarWbOn(false)
    expect(complianceFetchKey(useStudioStore.getState())).not.toBe(absBefore)
  })

  it('absolute-mode keys stay render-only for a non-ECBF beam', () => {
    const s = useStudioStore.getState()
    s.setBeam('mrt')
    s.setEcbfConstraintMode('absolute')
    s.setShowCompliance(true)
    const before = { ...keys(), compliance: complianceFetchKey(useStudioStore.getState()) }
    // The absolute params only steer ECBF, so for MRT the dBm slider stays render-only.
    s.setTxPowerDbm(80)
    const after = { ...keys(), compliance: complianceFetchKey(useStudioStore.getState()) }
    expect(after).toEqual(before)
  })

  it('volumeThreshold / volumeOpacity are render-only: change no fetch key', () => {
    const before = keys()
    useStudioStore.getState().setVolumeThreshold(0.6)
    useStudioStore.getState().setVolumeOpacity(0.8)
    const after = keys()
    expect(after.volume).toBe(before.volume)
    expect(after.slice).toBe(before.slice)
    expect(after.bodyMap).toBe(before.bodyMap)
  })

  it('resetDefaults restores every knob to STUDIO_DEFAULTS', () => {
    // Mutate a spread of params (channel / render-only / nested / volume) away
    // from their defaults, then reset and confirm each comes back.
    const st = useStudioStore.getState()
    st.setMesh('duke')
    st.setBeam('mrt')
    st.setBackground('dark')
    st.setRayThickness(3)
    st.setShowGizmo(false)
    st.setPlane({ extentM: 0.4 })
    st.setVolumeOpacity(0.9)
    st.setReferenceMap({ values: [1, 2], label: 'ref' })

    useStudioStore.getState().resetDefaults()
    const s = useStudioStore.getState()
    expect(s.mesh).toBe(STUDIO_DEFAULTS.mesh)
    expect(s.beam).toBe(STUDIO_DEFAULTS.beam)
    expect(s.background).toBe(STUDIO_DEFAULTS.background)
    expect(s.rayThickness).toBe(STUDIO_DEFAULTS.rayThickness)
    expect(s.showGizmo).toBe(STUDIO_DEFAULTS.showGizmo)
    expect(s.plane.extentM).toBe(STUDIO_DEFAULTS.plane.extentM)
    expect(s.volumeOpacity).toBe(STUDIO_DEFAULTS.volumeOpacity)
    expect(s.referenceMap).toBeNull()
    expect(s.snrMrtDb).toBe(STUDIO_DEFAULTS.snrMrtDb)
    expect(s.txPowerDbm).toBe(STUDIO_DEFAULTS.txPowerDbm)
    expect(s.txPowerDbm).toBe(25) // calibration power -> powerScale 1, baseline unchanged
    expect(s.ecbfConstraintMode).toBe(STUDIO_DEFAULTS.ecbfConstraintMode)
    expect(s.ecbfConstraintMode).toBe('relative') // absolute mode is opt-in
    expect(s.ecbfSarWbOn).toBe(true)
    expect(s.ecbfPeakOn).toBe(true)
  })

  it('dbmToWatts converts dBm to watts (P[W] = 10^((dBm-30)/10))', () => {
    expect(dbmToWatts(30)).toBeCloseTo(1, 9)
    expect(dbmToWatts(25)).toBeCloseTo(0.31623, 4) // calibration power
    expect(dbmToWatts(60)).toBeCloseTo(1000, 6) // near the binding knee
    expect(dbmToWatts(0)).toBeCloseTo(1e-3, 12)
  })

  it('icnirpLimits exposes the 4 cm^2 S_ab limit only above 6 GHz', () => {
    expect(icnirpLimits(10).sarWb).toBe(0.08)
    expect(icnirpLimits(10).sab4cm2).toBe(20)
    expect(icnirpLimits(3.5).sab4cm2).toBeNull() // below 6 GHz: SAR_wb only
  })

  it('spectralEfficiency = log2(1 + SNR_mrt * signal_rel)', () => {
    // At the MRT operating point (signal_rel = 1) the rate is log2(1 + SNR_mrt).
    expect(spectralEfficiency(1, 20)).toBeCloseTo(Math.log2(101), 9)
    // SINR is linear in received signal power, so a weaker beam scales inside.
    expect(spectralEfficiency(0.25, 20)).toBeCloseTo(Math.log2(1 + 100 * 0.25), 9)
    // No signal -> no rate.
    expect(spectralEfficiency(0, 20)).toBe(0)
  })

  it('powerDisplayFactor: power-class scales linearly, field-class as sqrt', () => {
    // S / S_ab / P_abs / SAR are power-class (quadratic in x) -> x powerScale.
    expect(quantityIsField('S')).toBe(false)
    expect(quantityIsField('sab')).toBe(false)
    expect(powerDisplayFactor('S', 4)).toBeCloseTo(4, 12)
    expect(powerDisplayFactor('sab', 4)).toBeCloseTo(4, 12)
    // Field amplitudes (|E|, |H|, Re E) are linear in x -> x sqrt(powerScale).
    expect(quantityIsField('absE')).toBe(true)
    expect(quantityIsField('ReEz')).toBe(true)
    expect(powerDisplayFactor('absE', 4)).toBeCloseTo(2, 12)
    expect(powerDisplayFactor('ReEz', 9)).toBeCloseTo(3, 12)
    // Identity at the calibration power (powerScale = 1).
    expect(powerDisplayFactor('S', 1)).toBe(1)
    expect(powerDisplayFactor('absE', 1)).toBe(1)
  })

  it('resetDefaults does not wipe fetched results / scene', () => {
    // Reset is a knob reset, not a teardown: results refetch from the restored
    // params, so clearing them here would just flash the scene empty.
    useStudioStore.setState({ scene: { provenance: 'keep' } as never })
    useStudioStore.getState().resetDefaults()
    expect(useStudioStore.getState().scene).not.toBeNull()
  })

  it('ueIdx changes slice, body-map and volume keys', () => {
    // Regression guard for "scrolling the UE slider only moved the phantom".
    // The standing position selects per-UE ray / channel packs, so every live
    // fetch (slice, deposited body map, volume) must refetch when it changes.
    const before = keys()
    useStudioStore.getState().setUeIdx(2)
    const after = keys()
    expect(after.slice).not.toBe(before.slice)
    expect(after.bodyMap).not.toBe(before.bodyMap)
    expect(after.volume).not.toBe(before.volume)
  })
})

describe('coherentStudio UE focus tracking', () => {
  // The corridor relocates the body by ue_positions[new] - ue_positions[old]
  // (a pure x translation), so the steering focus must shift by the same vector
  // to keep tracking the same spot on the body. This is what makes the rays,
  // slice, volume, Rx marker and gizmo follow the body down the corridor instead
  // of staying pinned at the previous standing position.
  beforeEach(() => {
    useStudioStore.setState({
      ueIdx: 4,
      focusXyz: [0.923, -0.005, 0.734],
      // Minimal scene carrying the corridor positions (2 m x-spacing, UE4 at x=1).
      scene: {
        room_dims: [0, 0, 0],
        bs_position: [-13, 0, 3],
        bs_n: 16,
        bs_tilt_deg: 0,
        scatterers: [],
        blocker: null,
        ue_positions: Array.from({ length: 9 }, (_, i) => [-7 + 2 * i, 0, 1.75]),
        provenance: 'test',
      },
    })
  })

  it('shifts the focus by the corridor delta when the UE moves', () => {
    useStudioStore.getState().setUeIdx(0) // x: 1 -> -7, delta -8 in x
    const s = useStudioStore.getState()
    expect(s.ueIdx).toBe(0)
    expect(s.focusXyz[0]).toBeCloseTo(0.923 - 8, 6)
    expect(s.focusXyz[1]).toBeCloseTo(-0.005, 6)
    expect(s.focusXyz[2]).toBeCloseTo(0.734, 6)
  })

  it('stepping UE4 -> UE8 -> UE4 returns the focus to its origin', () => {
    useStudioStore.getState().setUeIdx(8) // +8 in x
    useStudioStore.getState().setUeIdx(4) // -8 in x
    const s = useStudioStore.getState()
    expect(s.focusXyz[0]).toBeCloseTo(0.923, 6)
  })

  it('leaves the focus untouched when the scene (hence ue_positions) is absent', () => {
    useStudioStore.setState({ scene: null })
    useStudioStore.getState().setUeIdx(0)
    const s = useStudioStore.getState()
    expect(s.ueIdx).toBe(0)
    expect(s.focusXyz[0]).toBeCloseTo(0.923, 6)
  })
})
