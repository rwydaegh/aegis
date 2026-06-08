import { describe, it, expect, beforeEach } from 'vitest'
import { useSimulationStore } from '../simulation'

describe('simulation store diffraction model', () => {
  beforeEach(() => {
    useSimulationStore.setState({
      diffractionModel: 'fock',
      diffraction: true,
      curvature: true,
      interBody: 'off',
    })
  })

  it('defaults to fock with curvature and derived diffraction on', () => {
    const s = useSimulationStore.getState()
    expect(s.diffractionModel).toBe('fock')
    expect(s.diffraction).toBe(true)
    expect(s.curvature).toBe(true)
    expect(s.interBody).toBe('off')
  })

  it('setDiffractionModel(none) clears the derived diffraction bool', () => {
    useSimulationStore.getState().setDiffractionModel('none')
    const s = useSimulationStore.getState()
    expect(s.diffractionModel).toBe('none')
    expect(s.diffraction).toBe(false)
  })

  it('setDiffractionModel(gelu) forces curvature on and derives diffraction', () => {
    useSimulationStore.setState({ curvature: false, diffractionModel: 'none', diffraction: false })
    useSimulationStore.getState().setDiffractionModel('gelu')
    const s = useSimulationStore.getState()
    expect(s.diffractionModel).toBe('gelu')
    expect(s.diffraction).toBe(true)
    expect(s.curvature).toBe(true)
  })

  it('keeps the derived diffraction getter consistent with the model', () => {
    for (const model of ['none', 'gelu', 'fock'] as const) {
      useSimulationStore.getState().setDiffractionModel(model)
      const s = useSimulationStore.getState()
      expect(s.diffraction).toBe(model !== 'none')
    }
  })

  it('disabling curvature also clears an active diffraction gate', () => {
    useSimulationStore.getState().setDiffractionModel('fock')
    useSimulationStore.getState().setCurvature(false)
    const s = useSimulationStore.getState()
    expect(s.curvature).toBe(false)
    expect(s.diffractionModel).toBe('none')
    expect(s.diffraction).toBe(false)
  })

  it('setInterBody updates the inter-body backend selector', () => {
    useSimulationStore.getState().setInterBody('specular1')
    expect(useSimulationStore.getState().interBody).toBe('specular1')
    useSimulationStore.getState().setInterBody('off')
    expect(useSimulationStore.getState().interBody).toBe('off')
  })
})
