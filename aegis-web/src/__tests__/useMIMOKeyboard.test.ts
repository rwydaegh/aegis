import { describe, it, expect, beforeEach } from 'vitest'
import { useMIMOStore } from '@/stores/mimo'

describe('useMIMOKeyboard store interactions', () => {
  beforeEach(() => {
    useMIMOStore.getState().reset()
  })

  it('Tab cycles through users by insertion order', () => {
    const store = useMIMOStore.getState()
    store.setEnabled(true)
    store.addUser('duke', [0, 0, 0])
    store.addUser('ella', [2, 0, 0])
    const ids = [...useMIMOStore.getState().users.keys()]
    expect(ids).toHaveLength(3)
    expect(useMIMOStore.getState().controlledUserId).toBe(ids[0])

    const current = ids.indexOf(ids[0])
    const nextIdx = (current + 1) % ids.length
    store.setControlledUser(ids[nextIdx])
    expect(useMIMOStore.getState().controlledUserId).toBe(ids[1])
  })

  it('moveUser updates position', () => {
    const store = useMIMOStore.getState()
    store.setEnabled(true)
    store.addUser('duke', [0, 0, 0])
    const id = [...useMIMOStore.getState().users.keys()][0]
    store.moveUser(id, [0.2, 0, 0])
    expect(useMIMOStore.getState().users.get(id)?.position).toEqual([0.2, 0, 0])
  })

  it('number key selects user by index', () => {
    const store = useMIMOStore.getState()
    store.setEnabled(true)
    store.addUser('duke', [0, 0, 0])
    store.addUser('ella', [2, 0, 0])
    const ids = [...useMIMOStore.getState().users.keys()]

    store.setControlledUser(ids[1])
    store.setFocusedUser(ids[1])
    expect(useMIMOStore.getState().controlledUserId).toBe(ids[1])
    expect(useMIMOStore.getState().focusedUserId).toBe(ids[1])
  })
})
