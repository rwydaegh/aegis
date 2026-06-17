import { describe, it, expect, beforeEach } from 'vitest'
import { useStudioStore, sliceFetchKey, bodyMapFetchKey, volumeFetchKey } from '../store'

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

  it('volumeThreshold / volumeOpacity are render-only: change no fetch key', () => {
    const before = keys()
    useStudioStore.getState().setVolumeThreshold(0.6)
    useStudioStore.getState().setVolumeOpacity(0.8)
    const after = keys()
    expect(after.volume).toBe(before.volume)
    expect(after.slice).toBe(before.slice)
    expect(after.bodyMap).toBe(before.bodyMap)
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
