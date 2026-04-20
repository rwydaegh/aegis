import { describe, it, expect, beforeEach } from 'vitest'
// Import simulation first to break the antenna<->simulation module init cycle
// (simulation.ts subscribes to useAntennaStore at module eval time).
import '../../stores/simulation'
import { resetScenarioScopedStores } from '../useScenario'
import { useBaseStationsStore } from '../../stores/basestations'
import { useMIMOStore } from '../../stores/mimo'
import { useOptimizeStore } from '../../stores/optimize'
import { useCoverageStore } from '../../stores/coverage'
import type { BaseStationData } from '@/api/basestations'
import type { SpatialComplianceResult } from '@/api/client'

function bs(partial: Partial<BaseStationData>): BaseStationData {
  return {
    site_code: 'S1',
    antenna_label: 'A1',
    operator: 'op',
    technology: '5G',
    latitude: 51,
    longitude: 3,
    height_m: 25,
    eirp_dbm: 50,
    gain_dbi: 15,
    freq_mhz: 3500,
    azimuth_deg: 0,
    total_tilt_deg: 0,
    has_pattern: false,
    horizontal_beamwidth_deg: 65,
    vertical_beamwidth_deg: 10,
    archetype: 'UPA',
    n_h: 4,
    n_v: 4,
    panel_width_m: 0.3,
    panel_height_m: 0.3,
    ...partial,
  } as BaseStationData
}

describe('resetScenarioScopedStores', () => {
  beforeEach(() => {
    resetScenarioScopedStores()
  })

  it('wipes basestations populated in a previous scenario', () => {
    useBaseStationsStore.getState().setBasestations(
      [bs({ site_code: 'A' }), bs({ site_code: 'B' })],
      { lat: 51, lon: 3 },
    )
    expect(useBaseStationsStore.getState().basestations.length).toBe(2)

    resetScenarioScopedStores()

    expect(useBaseStationsStore.getState().basestations.length).toBe(0)
    expect(useBaseStationsStore.getState().origin).toBeNull()
    expect(useBaseStationsStore.getState().activeCount).toBe(0)
  })

  it('wipes MIMO users and precoder state from a previous scenario', () => {
    useMIMOStore.getState().addUser('duke', [0, 0, 0])
    useMIMOStore.getState().addUser('ella', [1, 0, 0])
    expect(useMIMOStore.getState().users.size).toBe(2)

    resetScenarioScopedStores()

    expect(useMIMOStore.getState().users.size).toBe(0)
    expect(useMIMOStore.getState().focusedUserId).toBeNull()
    expect(useMIMOStore.getState().enabled).toBe(false)
  })

  it('wipes optimizer history and mode from a previous scenario', () => {
    useOptimizeStore.setState({
      mode: 'placement',
      history: [{ iter: 1, objective: 0.5, params: {} }],
      currentIter: 1,
      summary: 'fake summary',
      running: false,
    })
    expect(useOptimizeStore.getState().history.length).toBe(1)

    resetScenarioScopedStores()

    expect(useOptimizeStore.getState().mode).toBeNull()
    expect(useOptimizeStore.getState().history.length).toBe(0)
    expect(useOptimizeStore.getState().summary).toBeNull()
    expect(useOptimizeStore.getState().currentIter).toBe(0)
  })

  it('wipes cached compliance zone and disables the toggle', () => {
    const fakeZone: SpatialComplianceResult = {
      bbox: [0, 0, 1, 1],
      resolution: 80,
      ratios: [[0.5]],
      n_stations: 3,
      freq_hz_dominant: 3.5e9,
    } as unknown as SpatialComplianceResult
    useCoverageStore.setState({
      complianceZone: fakeZone,
      complianceZoneEnabled: true,
    })

    resetScenarioScopedStores()

    expect(useCoverageStore.getState().complianceZone).toBeNull()
    expect(useCoverageStore.getState().complianceZoneEnabled).toBe(false)
  })

  it('is idempotent on an already-empty state', () => {
    resetScenarioScopedStores()
    resetScenarioScopedStores()

    expect(useBaseStationsStore.getState().basestations.length).toBe(0)
    expect(useMIMOStore.getState().users.size).toBe(0)
    expect(useOptimizeStore.getState().history.length).toBe(0)
  })
})
