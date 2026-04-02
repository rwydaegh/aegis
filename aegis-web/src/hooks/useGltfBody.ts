// aegis-web/src/hooks/useGltfBody.ts
import { useEffect, useMemo } from 'react'
import { useGLTF, useAnimations } from '@react-three/drei'
import { useSceneStore } from '@/stores/scene'
import { useShallow } from 'zustand/react/shallow'
import type { Group } from 'three'
import type React from 'react'

export function useGltfBody(bodyName: string, groupRef: React.RefObject<Group>) {
  const { scene, animations } = useGLTF(`/api/phantom/${bodyName}.glb`)
  const { actions, mixer } = useAnimations(animations, groupRef)

  const { animationClip, animationPlaying } = useSceneStore(useShallow(s => ({
    animationClip: s.animationClip,
    animationPlaying: s.animationPlaying,
  })))

  // Play/stop/pause animation clips (single effect to avoid races)
  useEffect(() => {
    Object.values(actions).forEach(a => a?.stop())
    const action = actions[animationClip]
    if (!action) return
    action.reset().fadeIn(0.3).play()
    action.paused = !animationPlaying
    return () => { action.fadeOut(0.3) }
  }, [animationClip, animationPlaying, actions])

  const clonedScene = useMemo(() => scene.clone(true), [scene])

  return { scene: clonedScene, actions, mixer }
}
