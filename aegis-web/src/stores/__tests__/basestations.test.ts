import { describe, it, expect, beforeEach } from 'vitest'
import { useBaseStationsStore } from '../basestations'
import type { BaseStationData } from '@/api/basestations'

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

describe('basestations store frequency-band filter', () => {
  beforeEach(() => {
    useBaseStationsStore.getState().clear()
  })

  it('hides banded antennas when user unchecks every band', () => {
    const store = useBaseStationsStore.getState()
    const data = [
      bs({ site_code: 'A', frequency_band: '3.5 GHz', operator: 'o1' }),
      bs({ site_code: 'B', frequency_band: '2.1 GHz', operator: 'o1' }),
    ]
    store.setBasestations(data, { lat: 51, lon: 3 })

    // Both bands enabled: both active
    expect(useBaseStationsStore.getState().activeCount).toBe(2)
    expect(useBaseStationsStore.getState().activeIndices()).toEqual([0, 1])

    // Uncheck one band
    store.toggleFrequencyBand('3.5 GHz')
    expect(useBaseStationsStore.getState().activeCount).toBe(1)
    expect(useBaseStationsStore.getState().activeIndices()).toEqual([1])

    // Uncheck the last band: filter empties, banded antennas must stay hidden
    store.toggleFrequencyBand('2.1 GHz')
    expect(useBaseStationsStore.getState().enabledFrequencyBands.size).toBe(0)
    expect(useBaseStationsStore.getState().activeCount).toBe(0)
    expect(useBaseStationsStore.getState().activeIndices()).toEqual([])
  })

  it('keeps band-less antennas visible even when every band is unchecked', () => {
    const store = useBaseStationsStore.getState()
    const data = [
      bs({ site_code: 'A', frequency_band: '3.5 GHz' }),
      bs({ site_code: 'B', frequency_band: undefined }),
    ]
    store.setBasestations(data, { lat: 51, lon: 3 })

    store.toggleFrequencyBand('3.5 GHz')
    const s = useBaseStationsStore.getState()
    expect(s.enabledFrequencyBands.size).toBe(0)
    // Band-less antenna (index 1) must remain active
    expect(s.activeCount).toBe(1)
    expect(s.activeIndices()).toEqual([1])
  })

  it('unchecking every operator hides everything (no regression)', () => {
    const store = useBaseStationsStore.getState()
    const data = [
      bs({ site_code: 'A', operator: 'o1', frequency_band: '3.5 GHz' }),
      bs({ site_code: 'B', operator: 'o2', frequency_band: undefined }),
    ]
    store.setBasestations(data, { lat: 51, lon: 3 })

    store.toggleOperator('o1')
    store.toggleOperator('o2')
    const s = useBaseStationsStore.getState()
    expect(s.enabledOperators.size).toBe(0)
    expect(s.activeCount).toBe(0)
    expect(s.activeIndices()).toEqual([])
  })
})
