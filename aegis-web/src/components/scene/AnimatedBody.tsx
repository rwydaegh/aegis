// aegis-web/src/components/scene/AnimatedBody.tsx
import { useRef, useEffect, Suspense } from 'react'
import * as THREE from 'three'
import * as Sentry from '@sentry/react'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { useGltfBody } from '@/hooks/useGltfBody'
import { extractPosedMesh } from '@/hooks/usePoseExtract'
import { computeWithInlineMesh } from '@/api/computeInline'
import BodyMeshInstance from './BodyMeshInstance'

function AnimatedBodyInner() {
  const groupRef = useRef<THREE.Group>(null!)
  const abortRef = useRef<AbortController | null>(null)
  const generationRef = useRef(0)

  const bodyName = useSceneStore(s => s.bodyName)
  const animationPlaying = useSceneStore(s => s.animationPlaying)
  const bodyGeometry = useSceneStore(s => s.bodyGeometry)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const bodyRotationY = useSimulationStore(s => s.bodyRotationY)
  const sabArray = useSimulationStore(s => s.sabArray)
  const sabAveragedArray = useSimulationStore(s => s.sabAveragedArray)
  const sincArray = useSimulationStore(s => s.sincArray)
  const sincAveragedArray = useSimulationStore(s => s.sincAveragedArray)
  const sab1cm2AveragedArray = useSimulationStore(s => s.sab1cm2AveragedArray)
  const stats = useSimulationStore(s => s.stats)
  const compliance = useSimulationStore(s => s.compliance)

  const { scene } = useGltfBody(bodyName, groupRef)

  // Clear stale STL dosimetry results on mount / body change
  useEffect(() => {
    useSimulationStore.getState().clearResults()
    useSceneStore.getState().setBodyGeometry(null)
  }, [bodyName])

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

  // When animation is paused, extract posed mesh and run dosimetry
  useEffect(() => {
    if (animationPlaying) return

    const sm = skinnedMeshRef.current
    if (!sm) return

    // Extract deformed mesh as triangle soup (Z-up, ready for backend)
    const posedData = extractPosedMesh(sm)

    // Create non-indexed geometry clone for heatmap display
    const frozenGeo = new THREE.BufferGeometry()
    frozenGeo.setAttribute('position', new THREE.BufferAttribute(posedData.positions, 3))
    frozenGeo.setAttribute('normal', new THREE.BufferAttribute(posedData.normals, 3))
    // Initialize color attribute for heatmap painting
    const colors = new Float32Array(posedData.positions.length)
    colors.fill(0.5)
    frozenGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3))

    useSceneStore.getState().setBodyGeometry(frozenGeo)

    // Assemble compute params from simulation store (mirrors useDosimetry pattern)
    const simState = useSimulationStore.getState()
    if (!simState.antennaPos) return

    const config = useSceneStore.getState().viewerConfig
    const poleH = config?.antenna?.pole_height ?? 2
    const antennaTip: [number, number, number] = [
      simState.antennaPos[0],
      simState.antennaPos[1] + poleH,
      simState.antennaPos[2],
    ]

    const exposureScenario = useUIStore.getState().exposureScenario

    const params: Record<string, unknown> = {
      antennaPos: antennaTip,
      bodyOffset: simState.bodyOffset,
      bodyRotationY: simState.bodyRotationY,
      mode: simState.mode,
      fresnel: simState.fresnel,
      polarisation: simState.polarisation,
      curvature: simState.curvature,
      diffraction: simState.diffraction,
      powerDbm: simState.powerDbm,
      skinModel: simState.skinModel,
      freqGhz: simState.freqGhz,
      quantities: Array.from(simState.enabledQuantities) as string[],
      exposureScenario,
    }

    // Abort previous in-flight request
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const gen = ++generationRef.current
    const setComputing = useUIStore.getState().setComputing
    setComputing(true)

    computeWithInlineMesh(posedData, params, controller.signal)
      .then(({ sab, stats, arrays }) => {
        if (gen !== generationRef.current) return // stale response
        useNotificationStore.getState().dismissByLevel('error')
        useSimulationStore.getState().setResults(sab, stats, {
          sabAveraged: arrays['sab_4cm2'],
          sinc: arrays['sinc_local'],
          sincAveraged: arrays['sinc_wb'],
          sab1cm2Averaged: arrays['sab_1cm2'],
        })
      })
      .catch(err => {
        if ((err as Error).name === 'AbortError') return
        Sentry.captureException(err)
        useNotificationStore.getState().addNotification(
          'error',
          `Posed mesh compute failed: ${(err as Error).message ?? err}`,
          'This error has been reported and will be fixed automatically using AI. Most issues are fixed in less than 30 minutes.',
        )
      })
      .finally(() => {
        if (gen === generationRef.current) setComputing(false)
      })
  }, [animationPlaying, scene])

  // Cancel in-flight request on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  // When paused and heatmap geometry is ready, show the colored heatmap mesh
  // instead of the GLB model. While animating (or before first pause), show the GLB.
  const showHeatmap = !animationPlaying && bodyGeometry !== null

  return (
    <>
      <group ref={groupRef} position={bodyOffset} rotation={[0, bodyRotationY, 0]} visible={!showHeatmap}>
        <primitive object={scene} />
      </group>
      {showHeatmap && (
        <BodyMeshInstance
          geometry={bodyGeometry}
          sabArray={sabArray}
          sabAveragedArray={sabAveragedArray}
          sincArray={sincArray}
          sincAveragedArray={sincAveragedArray}
          sab1cm2AveragedArray={sab1cm2AveragedArray}
          stats={stats}
          compliance={compliance}
          position={bodyOffset}
          rotationY={bodyRotationY}
        />
      )}
    </>
  )
}

export function AnimatedBody() {
  return (
    <Suspense fallback={null}>
      <AnimatedBodyInner />
    </Suspense>
  )
}
