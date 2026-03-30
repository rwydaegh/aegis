import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import * as Sentry from '@sentry/react'
import { fetchBody } from '@/api/client'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useNotificationStore } from '@/stores/notifications'

export function useBodyLoader() {
  const bodyName = useSceneStore(s => s.bodyName)
  const setBodyGeometry = useSceneStore(s => s.setBodyGeometry)
  const prevBodyRef = useRef(bodyName)

  useEffect(() => {
    let cancelled = false

    // Clear stale results only when body actually changes (different triangle count would cause jumbled colors).
    // Skip on re-mount with the same body (e.g. visibility toggle) to preserve dosimetry heatmap.
    if (prevBodyRef.current !== bodyName) {
      useSimulationStore.getState().clearResults()
      prevBodyRef.current = bodyName
    }

    fetchBody(bodyName).then(({ binary }) => {
      if (cancelled) return

      const geometry = new THREE.BufferGeometry()
      geometry.setAttribute('position', new THREE.BufferAttribute(binary.positions, 3))
      geometry.setAttribute('normal', new THREE.BufferAttribute(binary.normals, 3))

      // Body mesh is triangle soup (3 vertices per triangle, no index buffer)
      // Add a color attribute for heatmap (initialized to neutral gray)
      const colors = new Float32Array(binary.positions.length)
      colors.fill(0.5)
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

      geometry.computeBoundingBox()

      // Shift body so feet (min Y) sit on ground plane at y=0
      const bb = geometry.boundingBox!
      if (bb.min.y < 0) {
        geometry.translate(0, -bb.min.y, 0)
        geometry.computeBoundingBox()
      }

      setBodyGeometry(geometry)
    }).catch(err => {
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', `Failed to load body: ${(err as Error).message}`)
    })

    return () => { cancelled = true }
  }, [bodyName, setBodyGeometry])
}
