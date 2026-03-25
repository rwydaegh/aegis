import { useRef, useCallback } from 'react'
import type { ThreeEvent } from '@react-three/fiber'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useMIMOStore } from '@/stores/mimo'

/**
 * Returns onPointerDown/onPointerUp handlers that place the antenna
 * at the clicked 3D point (if the click wasn't a drag).
 */
export function useClickToPlace() {
  const pointerDownPos = useRef<{ x: number; y: number } | null>(null)

  const onPointerDown = useCallback((e: ThreeEvent<PointerEvent>) => {
    pointerDownPos.current = { x: e.clientX, y: e.clientY }
  }, [])

  const onPointerUp = useCallback((e: ThreeEvent<PointerEvent>) => {
    if (!pointerDownPos.current) return
    const config = useSceneStore.getState().viewerConfig
    if (!config) return

    const dx = e.clientX - pointerDownPos.current.x
    const dy = e.clientY - pointerDownPos.current.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    const threshold = config.interaction.click_max_drag_px ?? 5

    if (dist <= threshold && e.intersections.length > 0) {
      const point = e.intersections[0].point
      const mimoStore = useMIMOStore.getState()
      if (mimoStore.enabled && mimoStore.arrayConfig) {
        if (e.nativeEvent.shiftKey) {
          // Shift+click: place focus point (preserve current Y height)
          mimoStore.setFocusPoint([point.x, mimoStore.focusPoint[1], point.z])
        } else {
          // Click: place array (preserve current Y height)
          mimoStore.setArrayConfig({
            ...mimoStore.arrayConfig,
            position: [point.x, mimoStore.arrayConfig.position[1], point.z],
          })
        }
      } else {
        useSimulationStore.getState().setAntennaPos([point.x, point.y, point.z])
      }
    }
    pointerDownPos.current = null
  }, [])

  return { onPointerDown, onPointerUp }
}
