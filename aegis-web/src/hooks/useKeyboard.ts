import { useEffect, useRef } from 'react'
import { useSimulationStore } from '@/stores/simulation'
import { useAntennaStore } from '@/stores/antenna'
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

function isTypingTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLInputElement
    || target instanceof HTMLSelectElement
    || target instanceof HTMLTextAreaElement
  )
}

function deleteAntenna(e: KeyboardEvent): void {
  e.preventDefault()
  // Remove the selected antenna from the antenna store. setAntennaPos(null) only
  // deselects and leaves the pole on screen when more than one antenna exists
  // (or when the sole antenna was added by the multi-antenna flow).
  const antStore = useAntennaStore.getState()
  const selectedId = antStore.selectedId
  if (!selectedId) return
  antStore.removeAntenna(selectedId)
  useSimulationStore.getState().clearResults()
}

const ARROW_DELTAS: Record<string, [number, number, number]> = {
  ArrowUp: [0, 0, -1],
  ArrowDown: [0, 0, 1],
  ArrowLeft: [-1, 0, 0],
  ArrowRight: [1, 0, 0],
}

function nudgeAntennaWithArrow(e: KeyboardEvent): void {
  e.preventDefault()
  const config = useSceneStore.getState().viewerConfig
  const pos = useSimulationStore.getState().antennaPos
  if (!config || !pos) return
  const delta = ARROW_DELTAS[e.code]
  if (!delta) return
  const step = e.shiftKey
    ? (config.antenna.nudge_step_shift ?? 3)
    : (config.antenna.nudge_step ?? 1)
  const [x, y, z] = pos
  useSimulationStore.getState().setAntennaPos([
    x + delta[0] * step,
    y + delta[1] * step,
    z + delta[2] * step,
  ])
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
      if (isTypingTarget(e.target)) return

      keysRef.current.add(e.code)
      updateRef.current()

      if ((e.code === 'Delete' || e.code === 'Backspace') && !useMIMOStore.getState().enabled) {
        deleteAntenna(e)
        return
      }

      if (e.code.startsWith('Arrow') && !useMIMOStore.getState().enabled) {
        nudgeAntennaWithArrow(e)
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
