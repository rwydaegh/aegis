import { useRef, useCallback } from 'react'
import type { ThreeEvent } from '@react-three/fiber'
import { useSceneStore } from '@/stores/scene'
import { useMIMOStore } from '@/stores/mimo'
import { useAntennaStore } from '@/stores/antenna'

/**
 * Returns pointer handlers that place the antenna at the clicked 3D point,
 * distinguishing genuine clicks from orbit-control drags.
 *
 * Tracks cumulative pointer travel (not just net displacement) so that
 * circular orbit drags that end near their start point are not mistaken
 * for clicks.
 */
export function useClickToPlace() {
  const pointerDownPos = useRef<{ x: number; y: number } | null>(null)
  const lastMovePos = useRef<{ x: number; y: number } | null>(null)
  const cumulativeTravel = useRef(0)

  const onPointerDown = useCallback((e: ThreeEvent<PointerEvent>) => {
    pointerDownPos.current = { x: e.clientX, y: e.clientY }
    lastMovePos.current = { x: e.clientX, y: e.clientY }
    cumulativeTravel.current = 0
  }, [])

  const onPointerMove = useCallback((e: ThreeEvent<PointerEvent>) => {
    if (!lastMovePos.current) return
    const dx = e.clientX - lastMovePos.current.x
    const dy = e.clientY - lastMovePos.current.y
    cumulativeTravel.current += Math.sqrt(dx * dx + dy * dy)
    lastMovePos.current = { x: e.clientX, y: e.clientY }
  }, [])

  const onPointerUp = useCallback((e: ThreeEvent<PointerEvent>) => {
    if (!pointerDownPos.current) return
    const config = useSceneStore.getState().viewerConfig
    if (!config) return

    const threshold = config.interaction.click_max_drag_px ?? 5
    const isClick = cumulativeTravel.current <= threshold

    if (isClick && e.intersections.length > 0) {
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
    lastMovePos.current = null
  }, [])

  return { onPointerDown, onPointerMove, onPointerUp }
}
