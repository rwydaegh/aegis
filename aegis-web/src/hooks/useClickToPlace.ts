import { useRef, useCallback } from 'react'
import type { ThreeEvent } from '@react-three/fiber'
import { useSceneStore } from '@/stores/scene'
import { useMIMOStore } from '@/stores/mimo'
import { useAntennaStore } from '@/stores/antenna'

/**
 * Returns onPointerDown/onPointerMove/onPointerUp handlers that place the
 * antenna at the clicked 3D point, only if the pointer was NOT dragged.
 *
 * Unlike measuring just the displacement between down and up positions,
 * we track cumulative movement so that even a small orbit gesture that
 * returns near its start position is correctly identified as a drag.
 */
export function useClickToPlace() {
  const pointerDownPos = useRef<{ x: number; y: number } | null>(null)
  const cumulativeMovement = useRef(0)

  const onPointerDown = useCallback((e: ThreeEvent<PointerEvent>) => {
    pointerDownPos.current = { x: e.clientX, y: e.clientY }
    cumulativeMovement.current = 0
  }, [])

  const onPointerMove = useCallback((e: ThreeEvent<PointerEvent>) => {
    if (!pointerDownPos.current) return
    const dx = e.clientX - pointerDownPos.current.x
    const dy = e.clientY - pointerDownPos.current.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    // Track the max distance the pointer has been from the start
    if (dist > cumulativeMovement.current) {
      cumulativeMovement.current = dist
    }
  }, [])

  const onPointerUp = useCallback((e: ThreeEvent<PointerEvent>) => {
    if (!pointerDownPos.current) return
    const config = useSceneStore.getState().viewerConfig
    if (!config) return

    const threshold = config.interaction.click_max_drag_px ?? 5

    // Use cumulative movement (max distance from start) instead of just
    // the final displacement to catch orbit drags that return near origin
    if (cumulativeMovement.current <= threshold && e.intersections.length > 0) {
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
        // Multi-antenna mode
        const antStore = useAntennaStore.getState()
        if (e.nativeEvent.ctrlKey || e.nativeEvent.metaKey) {
          // Ctrl+click: add new antenna at click point
          antStore.addAntenna([point.x, point.y, point.z])
        } else if (antStore.selectedId) {
          // Click: move selected antenna
          antStore.moveAntenna(antStore.selectedId, [point.x, point.y, point.z])
        } else {
          // No antenna exists yet: create one
          antStore.addAntenna([point.x, point.y, point.z])
        }
      }
    }
    pointerDownPos.current = null
  }, [])

  return { onPointerDown, onPointerMove, onPointerUp }
}
