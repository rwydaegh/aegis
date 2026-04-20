import { describe, it, expect, beforeEach } from 'vitest'
import { useMIMOStore } from '../mimo'
import { useNotificationStore } from '../notifications'

describe('MIMO store', () => {
  beforeEach(() => {
    useMIMOStore.getState().reset()
    useNotificationStore.setState({ notifications: [] })
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

  it('setPrecoderType falls back to MRT and notifies when M < K', () => {
    const s = useMIMOStore.getState()
    s.setArrayConfig({
      type: 'upa',
      position: [0, 2, 0],
      broadside: [-1, 0, 0],
      n_h: 1,
      n_v: 2,
      d_h_wavelengths: 0.5,
      d_v_wavelengths: 0.5,
      element_pattern: 'isotropic',
    })
    // Add users first so the later setPrecoderType runs against M=2 < K=3.
    s.addUser('thelonious', [0, 1, -3])
    s.addUser('duke', [0, 1, -5])
    s.addUser('eartha', [0, 1, -7])
    useNotificationStore.setState({ notifications: [] })

    useMIMOStore.getState().setPrecoderType('zf')

    expect(useMIMOStore.getState().precoderType).toBe('mrt')
    const notes = useNotificationStore.getState().notifications
    expect(notes).toHaveLength(1)
    expect(notes[0].level).toBe('warning')
    expect(notes[0].message).toContain('ZF')
  })

  it('setPrecoderType to mrt always succeeds regardless of M vs K', () => {
    const s = useMIMOStore.getState()
    s.setArrayConfig({
      type: 'upa',
      position: [0, 2, 0],
      broadside: [-1, 0, 0],
      n_h: 1,
      n_v: 1,
      d_h_wavelengths: 0.5,
      d_v_wavelengths: 0.5,
      element_pattern: 'isotropic',
    })
    s.addUser('thelonious', [0, 1, -3])
    s.addUser('duke', [0, 1, -5])

    useMIMOStore.getState().setPrecoderType('mrt')

    expect(useMIMOStore.getState().precoderType).toBe('mrt')
  })

  it('setPrecoderType allows ZF when M >= K', () => {
    const s = useMIMOStore.getState()
    s.setArrayConfig({
      type: 'upa',
      position: [0, 2, 0],
      broadside: [-1, 0, 0],
      n_h: 2,
      n_v: 2,
      d_h_wavelengths: 0.5,
      d_v_wavelengths: 0.5,
      element_pattern: 'isotropic',
    })
    s.addUser('thelonious', [0, 1, -3])
    s.addUser('duke', [0, 1, -5])

    useMIMOStore.getState().setPrecoderType('zf')

    expect(useMIMOStore.getState().precoderType).toBe('zf')
  })

  it('setPrecoderType allows ZF when no arrayConfig is set', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 1, -3])
    s.addUser('duke', [0, 1, -5])

    useMIMOStore.getState().setPrecoderType('zf')

    expect(useMIMOStore.getState().precoderType).toBe('zf')
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
})
