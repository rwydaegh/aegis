import { useEffect, useRef } from 'react'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useMIMOStore } from '@/stores/mimo'

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

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return

      // MIMO mode has its own keyboard controls (useMIMOKeyboard)
      if (useMIMOStore.getState().enabled) return

      keysRef.current.add(e.code)
      updateState()

      // Arrow key antenna nudging
      if (e.code.startsWith('Arrow')) {
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
      updateState()
    }

    function updateState() {
      const keys = keysRef.current
      const s = stateRef.current
      s.forward = keys.has('KeyW')
      s.back = keys.has('KeyS')
      s.left = keys.has('KeyA')
      s.right = keys.has('KeyD')
      s.rotLeft = keys.has('KeyQ')
      s.rotRight = keys.has('KeyE')
      s.jump = keys.has('Space')
      s.sprint = keys.has('ShiftLeft') || keys.has('ShiftRight')
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [])

  return stateRef.current
}
