// aegis-web/src/components/scene/AnimatedBody.tsx
import { useRef, useEffect, Suspense } from 'react'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useGltfBody } from '@/hooks/useGltfBody'
import { extractPosedMesh } from '@/hooks/usePoseExtract'

function AnimatedBodyInner() {
  const groupRef = useRef<THREE.Group>(null!)

  const bodyName = useSceneStore(s => s.bodyName)
  const animationPlaying = useSceneStore(s => s.animationPlaying)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const bodyRotationY = useSimulationStore(s => s.bodyRotationY)

  const { scene } = useGltfBody(bodyName, groupRef)

  // Find the SkinnedMesh in the loaded scene
  const skinnedMeshRef = useRef<THREE.SkinnedMesh | null>(null)
  useEffect(() => {
    skinnedMeshRef.current = null
    scene.traverse((child) => {
      if (child instanceof THREE.SkinnedMesh && !skinnedMeshRef.current) {
        skinnedMeshRef.current = child
      }
    })
  }, [scene])

  // When animation is paused, extract posed mesh for dosimetry
  useEffect(() => {
    if (animationPlaying) return

    const sm = skinnedMeshRef.current
    if (!sm) return

    // Extract deformed mesh as triangle soup (Z-up, ready for backend)
    const posedData = extractPosedMesh(sm)

    // Create non-indexed geometry clone for heatmap display
    // This will be wired to the dosimetry pipeline in Task 6
    const frozenGeo = new THREE.BufferGeometry()
    frozenGeo.setAttribute('position', new THREE.BufferAttribute(posedData.positions, 3))
    frozenGeo.setAttribute('normal', new THREE.BufferAttribute(posedData.normals, 3))
    // Initialize color attribute for heatmap painting
    const colors = new Float32Array(posedData.positions.length)
    colors.fill(0.5)
    frozenGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3))

    useSceneStore.getState().setBodyGeometry(frozenGeo)
  }, [animationPlaying, scene])

  return (
    <group ref={groupRef} position={bodyOffset} rotation={[0, bodyRotationY, 0]}>
      <primitive object={scene} />
    </group>
  )
}

export function AnimatedBody() {
  return (
    <Suspense fallback={null}>
      <AnimatedBodyInner />
    </Suspense>
  )
}
