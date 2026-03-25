import { useEffect } from 'react'
import { useMIMOStore } from '@/stores/mimo'

const MOVE_STEP = 0.2
const MOVE_STEP_SHIFT = 1.0
const ROTATION_STEP = Math.PI / 12

export function useMIMOKeyboard() {
  const enabled = useMIMOStore(s => s.enabled)

  useEffect(() => {
    if (!enabled) return

    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return

      const store = useMIMOStore.getState()
      if (!store.enabled) return
      const userId = store.controlledUserId
      if (!userId) return

      const user = store.users.get(userId)
      if (!user) return

      const step = e.shiftKey ? MOVE_STEP_SHIFT : MOVE_STEP
      const [x, y, z] = user.position

      if (e.code === 'KeyW') { e.preventDefault(); store.moveUser(userId, [x, y, z - step]); return }
      if (e.code === 'KeyS') { e.preventDefault(); store.moveUser(userId, [x, y, z + step]); return }
      if (e.code === 'KeyA') { e.preventDefault(); store.moveUser(userId, [x - step, y, z]); return }
      if (e.code === 'KeyD') { e.preventDefault(); store.moveUser(userId, [x + step, y, z]); return }

      if (e.code === 'KeyR') {
        e.preventDefault()
        store.setUserOrientation(userId, user.orientation + ROTATION_STEP)
        return
      }

      if (e.code === 'Tab') {
        e.preventDefault()
        const ids = [...store.users.keys()]
        if (ids.length < 2) return
        const idx = ids.indexOf(userId)
        const nextIdx = (idx + 1) % ids.length
        store.setControlledUser(ids[nextIdx])
        store.setFocusedUser(ids[nextIdx])
        return
      }

      if (e.code.startsWith('Digit') && !e.ctrlKey && !e.metaKey) {
        const num = parseInt(e.code.replace('Digit', ''), 10)
        if (num < 1 || num > 9) return
        const ids = [...store.users.keys()]
        if (num <= ids.length) {
          e.preventDefault()
          store.setControlledUser(ids[num - 1])
          store.setFocusedUser(ids[num - 1])
        }
        return
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [enabled])
}
