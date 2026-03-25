import { describe, it, expect } from 'vitest'
import { buildMIMOComputePayload } from '../mimo'
import type { ScenePos } from '../coordinates'
import type { ArrayConfig, MIMOUserConfig } from '../types'

describe('MIMO API', () => {
  const array: ArrayConfig = {
    type: 'upa',
    n_h: 4,
    n_v: 4,
    d_h_wavelengths: 0.5,
    d_v_wavelengths: 0.5,
    position: [5, 3, 0] as ScenePos,
    broadside: [-1, 0, 0],
  }

  const users: MIMOUserConfig[] = [
    { id: 'u1', phantom: 'thelonious', position: [0, 0, 0] as ScenePos, orientation: 0, device_offset: [0.25, 1.4, 0] },
    { id: 'u2', phantom: 'duke', position: [2, 0, -1] as ScenePos, orientation: 0.5, device_offset: [0.25, 1.4, 0] },
  ]

  it('converts scene positions to server positions', () => {
    const payload = buildMIMOComputePayload({
      array,
      users,
      freq_hz: 28e9,
      power_dbm: 60,
      precoder_type: 'zf',
    })
    // toServer swaps: [x, y, z] -> [x, -z, y]
    expect(payload.array.position).toEqual([5, 0, 3])
    expect(payload.users[0].position).toEqual([0, 0, 0])
    expect(payload.users[1].position).toEqual([2, 1, 0])
  })

  it('preserves non-position fields', () => {
    const payload = buildMIMOComputePayload({
      array,
      users,
      freq_hz: 28e9,
      power_dbm: 60,
      precoder_type: 'zf',
    })
    expect(payload.freq_hz).toBe(28e9)
    expect(payload.power_dbm).toBe(60)
    expect(payload.precoder_type).toBe('zf')
    expect(payload.users[0].phantom).toBe('thelonious')
    expect(payload.users[1].orientation).toBe(0.5)
  })

  it('includes changed field when provided', () => {
    const payload = buildMIMOComputePayload({
      array,
      users,
      freq_hz: 28e9,
      power_dbm: 60,
      precoder_type: 'zf',
      changed: { type: 'user_moved', user_id: 'u1' },
    })
    expect(payload.changed).toEqual({ type: 'user_moved', user_id: 'u1' })
  })
})
