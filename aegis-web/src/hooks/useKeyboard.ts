import { useEffect, useRef } from 'react'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useMIMOStore } from '@/stores/mimo'
import { touchKeys } from '@/lib/touchKeys'

export interface KeyState {
  forward: boolean
  back: boolean
  left: boolean
  right: boolean
  rotLeft: boolean
  rotRight: boolean
  jump: boolean
  sprint: boolean
}

export function useKeyboard(): KeyState {
  const keysRef = useRef(new Set<string>())
  const stateRef = useRef<KeyState>({
    forward: false,
    back: false,
    left: false,
    right: false,
    rotLeft: false,
    rotRight: false,
    jump: false,
    sprint: false,
  })

  // Shared updater: merges physical keyboard keys + touch overlay keys
  const updateRef = useRef<() => void>(() => {})
  updateRef.current = () => {
    const keys = keysRef.current
    const t = touchKeys
    const s = stateRef.current
    s.forward = keys.has('KeyW') || t.has('KeyW')
    s.back = keys.has('KeyS') || t.has('KeyS')
    s.left = keys.has('KeyA') || t.has('KeyA')
    s.right = keys.has('KeyD') || t.has('KeyD')
    s.rotLeft = keys.has('KeyQ') || t.has('KeyQ')
    s.rotRight = keys.has('KeyE') || t.has('KeyE')
    s.jump = keys.has('Space') || t.has('Space')
    s.sprint = keys.has('ShiftLeft') || keys.has('ShiftRight')
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return

      keysRef.current.add(e.code)
      updateRef.current()

      // Delete/Backspace removes the antenna
      if ((e.code === 'Delete' || e.code === 'Backspace') && !useMIMOStore.getState().enabled) {
        e.preventDefault()
        const sim = useSimulationStore.getState()
        if (sim.antennaPos) {
          sim.setAntennaPos(null)
          sim.clearResults()
        }
        return
      }

      // Arrow key antenna nudging (single-user mode only)
      if (e.code.startsWith('Arrow') && !useMIMOStore.getState().enabled) {
        e.preventDefault()
        const config = useSceneStore.getState().viewerConfig
        const pos = useSimulationStore.getState().antennaPos
        if (!config || !pos) return

        const step = e.shiftKey
          ? (config.antenna.nudge_step_shift ?? 3)
          : (config.antenna.nudge_step ?? 1)
        const [x, y, z] = pos
        let newPos: [number, number, number] = [x, y, z]
        if (e.code === 'ArrowUp') newPos = [x, y, z - step]
        if (e.code === 'ArrowDown') newPos = [x, y, z + step]
        if (e.code === 'ArrowLeft') newPos = [x - step, y, z]
        if (e.code === 'ArrowRight') newPos = [x + step, y, z]
        useSimulationStore.getState().setAntennaPos(newPos)
      }
    }

    const handleKeyUp = (e: KeyboardEvent) => {
      keysRef.current.delete(e.code)
      updateRef.current()
    }

    // Poll touchKeys every frame so mobile controls work without keyboard events
    let raf = 0
    const pollTouch = () => {
      updateRef.current()
      raf = requestAnimationFrame(pollTouch)
    }
    raf = requestAnimationFrame(pollTouch)

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [])

  return stateRef.current
}
