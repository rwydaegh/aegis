import { useEffect } from 'react'
import * as THREE from 'three'
import { fetchBody } from '@/api/client'
import { useSceneStore } from '@/stores/scene'

export function useBodyLoader() {
  const bodyName = useSceneStore(s => s.bodyName)
  const setBodyGeometry = useSceneStore(s => s.setBodyGeometry)

  useEffect(() => {
    let cancelled = false

    fetchBody().then(({ binary }) => {
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
      console.error('Failed to load body:', err)
    })

    return () => { cancelled = true }
  }, [bodyName, setBodyGeometry])
}
