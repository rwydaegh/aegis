import { describe, it, expect, beforeEach } from 'vitest'
import { useMIMOStore, precoderRequiresMgeK } from '../mimo'
import { useNotificationStore } from '../notifications'
import type { ArrayConfig } from '@/api/types'

function makeArrayConfig(n_h: number, n_v: number): ArrayConfig {
  return {
    type: 'upa',
    n_h,
    n_v,
    d_h_wavelengths: 0.5,
    d_v_wavelengths: 0.5,
    position: [0, 2, 0],
    broadside: [-1, 0, 0],
    element_pattern: 'patch',
  }
}

describe('MIMO store', () => {
  beforeEach(() => {
    useMIMOStore.getState().reset()
  })

  it('starts disabled with no users', () => {
    const s = useMIMOStore.getState()
    expect(s.enabled).toBe(false)
    expect(s.users.size).toBe(0)
    expect(s.focusedUserId).toBeNull()
    expect(s.controlledUserId).toBeNull()
  })

  it('addUser creates a user and sets focus/control if first', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [2, 0, -3])
    const state = useMIMOStore.getState()
    expect(state.users.size).toBe(1)
    const user = [...state.users.values()][0]
    expect(user.phantomName).toBe('thelonious')
    expect(user.position).toEqual([2, 0, -3])
    expect(state.focusedUserId).toBe(user.userId)
    expect(state.controlledUserId).toBe(user.userId)
  })

  it('addUser auto-names sequentially', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    s.addUser('duke', [2, 0, 0])
    const names = [...useMIMOStore.getState().users.values()].map(u => u.displayName)
    expect(names).toEqual(['User 1', 'User 2'])
  })

  it('removeUser deletes user and transfers focus', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    s.addUser('duke', [2, 0, 0])
    const ids = [...useMIMOStore.getState().users.keys()]
    s.removeUser(ids[0])
    const state = useMIMOStore.getState()
    expect(state.users.size).toBe(1)
    expect(state.focusedUserId).toBe(ids[1])
    expect(state.controlledUserId).toBe(ids[1])
  })

  it('removeUser does not renumber display names', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    s.addUser('duke', [2, 0, 0])
    s.addUser('eartha', [4, 0, 0])
    const ids = [...useMIMOStore.getState().users.keys()]
    s.removeUser(ids[1])
    const names = [...useMIMOStore.getState().users.values()].map(u => u.displayName)
    expect(names).toEqual(['User 1', 'User 3'])
  })

  it('setFocusedUser changes focused user', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    s.addUser('duke', [2, 0, 0])
    const ids = [...useMIMOStore.getState().users.keys()]
    s.setFocusedUser(ids[1])
    expect(useMIMOStore.getState().focusedUserId).toBe(ids[1])
  })

  it('moveUser updates position', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    const id = [...useMIMOStore.getState().users.keys()][0]
    s.moveUser(id, [5, 0, -2])
    expect(useMIMOStore.getState().users.get(id)?.position).toEqual([5, 0, -2])
  })

  it('setUserResult updates sab and stats for a user', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    const id = [...useMIMOStore.getState().users.keys()][0]
    const sab = new Float32Array([1, 2, 3])
    const stats = { peak_sab: 10, p_abs_mw: 5, compliant: true } as any
    s.setUserResult(id, sab, stats)
    const user = useMIMOStore.getState().users.get(id)
    expect(user?.sabArray).toBe(sab)
    expect(user?.stats).toBe(stats)
    expect(user?.compliant).toBe(true)
  })

  it('setPrecoderType updates precoder', () => {
    useMIMOStore.getState().setPrecoderType('mmse')
    expect(useMIMOStore.getState().precoderType).toBe('mmse')
  })

  describe('precoderRequiresMgeK', () => {
    it('is true only for ZF and zf_exposure', () => {
      expect(precoderRequiresMgeK('zf')).toBe(true)
      expect(precoderRequiresMgeK('zf_exposure')).toBe(true)
      expect(precoderRequiresMgeK('mrt')).toBe(false)
      expect(precoderRequiresMgeK('mmse')).toBe(false)
    })
  })

  describe('M<K precoder feasibility', () => {
    beforeEach(() => {
      useNotificationStore.setState({ notifications: [] })
    })

    it('allows MMSE at M<K without fallback to MRT', () => {
      const s = useMIMOStore.getState()
      s.setArrayConfig(makeArrayConfig(2, 1)) // M=2
      s.setPrecoderType('mmse')
      s.addUser('thelonious', [0, 0, 0]) // K=1, M>=K
      s.addUser('duke', [1, 0, 0]) // K=2, M=K
      s.addUser('eartha', [2, 0, 0]) // K=3, M<K
      expect(useMIMOStore.getState().precoderType).toBe('mmse')
      expect(useMIMOStore.getState().users.size).toBe(3)
    })

    it('falls back from ZF to MRT when adding users past M', () => {
      const s = useMIMOStore.getState()
      s.setArrayConfig(makeArrayConfig(2, 1)) // M=2
      s.setPrecoderType('zf')
      s.addUser('thelonious', [0, 0, 0]) // K=1, OK
      s.addUser('duke', [1, 0, 0]) // K=2, OK
      expect(useMIMOStore.getState().precoderType).toBe('zf')
      s.addUser('eartha', [2, 0, 0]) // K=3, M<K → fallback
      expect(useMIMOStore.getState().precoderType).toBe('mrt')
    })

    it('falls back from zf_exposure to MRT when shrinking array past K', () => {
      const s = useMIMOStore.getState()
      s.setArrayConfig(makeArrayConfig(4, 1)) // M=4
      s.addUser('thelonious', [0, 0, 0])
      s.addUser('duke', [1, 0, 0])
      s.addUser('eartha', [2, 0, 0]) // K=3
      s.setPrecoderType('zf_exposure')
      expect(useMIMOStore.getState().precoderType).toBe('zf_exposure')
      s.setArrayConfig(makeArrayConfig(2, 1)) // M=2, K=3 → fallback
      expect(useMIMOStore.getState().precoderType).toBe('mrt')
    })

    it('keeps MMSE across array shrink below K', () => {
      const s = useMIMOStore.getState()
      s.setArrayConfig(makeArrayConfig(4, 1))
      s.addUser('thelonious', [0, 0, 0])
      s.addUser('duke', [1, 0, 0])
      s.addUser('eartha', [2, 0, 0])
      s.setPrecoderType('mmse')
      s.setArrayConfig(makeArrayConfig(2, 1)) // M=2, K=3
      expect(useMIMOStore.getState().precoderType).toBe('mmse')
    })

    it('setPrecoderType rejects ZF when M<K and falls back to MRT', () => {
      const s = useMIMOStore.getState()
      s.setArrayConfig(makeArrayConfig(2, 1)) // M=2
      s.addUser('thelonious', [0, 0, 0])
      s.addUser('duke', [1, 0, 0])
      s.addUser('eartha', [2, 0, 0]) // K=3, M<K
      s.setPrecoderType('zf')
      expect(useMIMOStore.getState().precoderType).toBe('mrt')
    })
  })

  it('focusedUser selector returns the focused user state', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    const focused = useMIMOStore.getState().focusedUser()
    expect(focused).not.toBeNull()
    expect(focused?.phantomName).toBe('thelonious')
  })

  it('focusedUser returns null when no users', () => {
    expect(useMIMOStore.getState().focusedUser()).toBeNull()
  })

  it('setEnabled(false) clears per-user state but preserves config', () => {
    const s = useMIMOStore.getState()
    s.setEnabled(true)
    s.addUser('duke', [3, 0, 0])
    s.setPrecoderType('zf_exposure')
    const initialConfig = useMIMOStore.getState().arrayConfig
    expect(useMIMOStore.getState().users.size).toBeGreaterThan(0)

    s.setEnabled(false)
    const after = useMIMOStore.getState()
    expect(after.enabled).toBe(false)
    expect(after.users.size).toBe(0)
    expect(after.focusedUserId).toBeNull()
    expect(after.controlledUserId).toBeNull()
    expect(after.summaryStats).toBeNull()
    expect(after.precoderWeights).toBeNull()
    expect(after.lastComputeError).toBeNull()
    expect(after.lastSuccessfulUserCount).toBe(0)
    // Config preferences preserved
    expect(after.arrayConfig).toEqual(initialConfig)
    expect(after.precoderType).toBe('zf_exposure')
  })

  it('setEnabled cycle auto-adds User 1 again after disable', () => {
    const s = useMIMOStore.getState()
    s.setEnabled(true)
    s.addUser('duke', [3, 0, 0])
    expect(useMIMOStore.getState().users.size).toBe(2)

    s.setEnabled(false)
    s.setEnabled(true)
    const after = useMIMOStore.getState()
    expect(after.users.size).toBe(1)
    const user = [...after.users.values()][0]
    expect(user.displayName).toBe('User 1')
    expect(after.focusedUserId).toBe(user.userId)
    expect(after.controlledUserId).toBe(user.userId)
  })
})
