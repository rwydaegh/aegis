import { describe, it, expect, beforeEach } from 'vitest'
import { useMIMOStore } from '@/stores/mimo'

describe('MIMOPanel store interactions', () => {
  beforeEach(() => {
    useMIMOStore.getState().reset()
  })

  it('addUser creates user with auto-incremented name', () => {
    const store = useMIMOStore.getState()
    store.addUser('duke', [0, 0, 0])
    store.addUser('ella', [1, 0, 0])
    const users = [...useMIMOStore.getState().users.values()]
    expect(users).toHaveLength(2)
    expect(users[0].displayName).toBe('User 1')
    expect(users[1].displayName).toBe('User 2')
  })

  it('removeUser does not renumber remaining users', () => {
    const store = useMIMOStore.getState()
    store.addUser('duke', [0, 0, 0])
    store.addUser('ella', [1, 0, 0])
    const firstId = [...useMIMOStore.getState().users.keys()][0]
    store.removeUser(firstId)
    const remaining = [...useMIMOStore.getState().users.values()]
    expect(remaining).toHaveLength(1)
    expect(remaining[0].displayName).toBe('User 2')
  })

  it('first user becomes focused and controlled', () => {
    useMIMOStore.getState().addUser('duke', [0, 0, 0])
    const id = [...useMIMOStore.getState().users.keys()][0]
    expect(useMIMOStore.getState().focusedUserId).toBe(id)
    expect(useMIMOStore.getState().controlledUserId).toBe(id)
  })

  it('setPrecoderType updates store', () => {
    useMIMOStore.getState().setPrecoderType('mmse')
    expect(useMIMOStore.getState().precoderType).toBe('mmse')
  })
})
