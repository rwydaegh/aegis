import { describe, it, expect, beforeEach } from 'vitest'
import { FIGURE_PRESETS, findFigurePreset } from '../figurePresets'
import { useStudioStore, type FigurePreset } from '../store'

describe('FIGURE_PRESETS catalogue', () => {
  it('pins a fixed shared colour scale on every panel (honesty guard)', () => {
    // The whole point of the figure is that the body cooling between panels is
    // real, not a per-panel autoscale artifact. Every preset must therefore lock
    // the scale (scaleMode 'fixed' + an explicit fixedRange from 0).
    for (const p of FIGURE_PRESETS) {
      expect(p.settings.scaleMode, p.name).toBe('fixed')
      expect(p.settings.fixedRange, p.name).toBeTruthy()
      expect(p.settings.fixedRange?.vmin, p.name).toBe(0)
      expect(p.settings.fixedRange?.vmax, p.name).toBeGreaterThan(0)
    }
  })

  it('shares one locked vmax across the three knob body tiles', () => {
    const tiles = ['fig1-mrt', 'fig1-ecbf50', 'fig1-ecbf15'].map((n) => findFigurePreset(n))
    const vmaxes = tiles.map((t) => t?.settings.fixedRange?.vmax)
    expect(vmaxes.every((v) => v === vmaxes[0])).toBe(true)
  })

  it('the knob tiles hide the field slice and step the ECBF budget down', () => {
    expect(findFigurePreset('fig1-mrt')?.settings.beam).toBe('mrt')
    expect(findFigurePreset('fig1-ecbf50')?.settings.ecbfBudgetFrac).toBe(0.5)
    expect(findFigurePreset('fig1-ecbf15')?.settings.ecbfBudgetFrac).toBe(0.15)
    for (const n of ['fig1-mrt', 'fig1-ecbf50', 'fig1-ecbf15']) {
      expect(findFigurePreset(n)?.settings.showSlice, n).toBe(false)
    }
  })

  it('every panel carries a camera so the framing is reproducible', () => {
    for (const p of FIGURE_PRESETS) {
      expect(p.camera, p.name).toBeTruthy()
      expect(p.camera?.position.length, p.name).toBe(3)
      expect(p.camera?.fov, p.name).toBeGreaterThan(0)
    }
  })

  it('findFigurePreset returns undefined for an unknown name', () => {
    expect(findFigurePreset('nope')).toBeUndefined()
  })
})

describe('applyFigurePreset', () => {
  beforeEach(() => {
    useStudioStore.getState().resetDefaults()
    useStudioStore.setState({ savedCamera: null, cameraApplyNonce: 0 })
  })

  it('merges the settings patch into the store', () => {
    useStudioStore.getState().applyFigurePreset(findFigurePreset('fig1-ecbf50')!)
    const s = useStudioStore.getState()
    expect(s.beam).toBe('ecbf')
    expect(s.ecbfBudgetFrac).toBe(0.5)
    expect(s.scaleMode).toBe('fixed')
    expect(s.showSlice).toBe(false)
  })

  it('pins the camera and bumps the apply nonce when the preset carries one', () => {
    const withCam: FigurePreset = {
      name: 't',
      label: 't',
      description: 't',
      settings: { beam: 'mrt' },
      camera: { position: [1, 2, 3], target: [0, 0, 0], fov: 45 },
    }
    useStudioStore.getState().applyFigurePreset(withCam)
    const s = useStudioStore.getState()
    expect(s.savedCamera).toEqual(withCam.camera)
    expect(s.cameraApplyNonce).toBe(1)
  })

  it('leaves the camera nonce untouched for a preset without a camera', () => {
    const before = useStudioStore.getState().cameraApplyNonce
    const noCam: FigurePreset = { name: 't', label: 't', description: 't', settings: { beam: 'mrt' } }
    useStudioStore.getState().applyFigurePreset(noCam)
    expect(useStudioStore.getState().cameraApplyNonce).toBe(before)
  })
})
