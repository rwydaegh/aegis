import { describe, it, expect, beforeEach } from 'vitest'
import { useStudioStore, sliceFetchKey, bodyMapFetchKey } from '../store'

function keys() {
  const s = useStudioStore.getState()
  return { slice: sliceFetchKey(s), bodyMap: bodyMapFetchKey(s) }
}

describe('coherentStudio fetch keys', () => {
  beforeEach(() => {
    useStudioStore.setState({
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
})
