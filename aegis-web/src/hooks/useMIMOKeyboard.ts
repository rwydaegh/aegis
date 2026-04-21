import { useEffect } from 'react'
import { useMIMOStore } from '@/stores/mimo'

export function useMIMOKeyboard() {
  const enabled = useMIMOStore(s => s.enabled)

  useEffect(() => {
    if (!enabled) return

    function handleKeyDown(e: KeyboardEvent) {
      if (
        e.target instanceof HTMLInputElement
        || e.target instanceof HTMLSelectElement
        || e.target instanceof HTMLTextAreaElement
      ) return

      const store = useMIMOStore.getState()
      if (!store.enabled) return
      const userId = store.controlledUserId
      if (!userId) return

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
