import { describe, it, expect, beforeEach } from 'vitest'
// Import simulation first to break the antenna<->simulation module init cycle
// (simulation.ts subscribes to useAntennaStore at module eval time).
import '../simulation'
import { useAntennaStore } from '../antenna'
import type { ScenePos } from '@/api/coordinates'

const P: ScenePos = [0, 1.5, -0.8]
const Q: ScenePos = [2, 1.5, -3]

describe('useAntennaStore.clearAntennas', () => {
  beforeEach(() => {
    useAntennaStore.getState().clearAntennas()
  })

  it('empties the map and resets selectedId', () => {
    const s = useAntennaStore.getState()
    s.addAntenna(P)
    s.addAntenna(Q)
    expect(useAntennaStore.getState().antennas.size).toBe(2)
    expect(useAntennaStore.getState().selectedId).not.toBeNull()

    useAntennaStore.getState().clearAntennas()

    expect(useAntennaStore.getState().antennas.size).toBe(0)
    expect(useAntennaStore.getState().selectedId).toBeNull()
  })

  it('resets the numbering so the next add starts at 1', () => {
    const s = useAntennaStore.getState()
    s.addAntenna(P)
    s.addAntenna(Q)
    useAntennaStore.getState().clearAntennas()

    const newId = useAntennaStore.getState().addAntenna(P)
    expect(newId).toBe('ant_1')
    const a = useAntennaStore.getState().antennas.get(newId)
    expect(a?.name).toBe('Antenna 1')
  })

  it('is a no-op on an already-empty store', () => {
    expect(useAntennaStore.getState().antennas.size).toBe(0)
    useAntennaStore.getState().clearAntennas()
    expect(useAntennaStore.getState().antennas.size).toBe(0)
    expect(useAntennaStore.getState().selectedId).toBeNull()
  })
})
