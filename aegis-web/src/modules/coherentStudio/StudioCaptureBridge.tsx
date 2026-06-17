import { useEffect, type MutableRefObject } from 'react'
import * as THREE from 'three'
import { useThree } from '@react-three/fiber'
import { useStudioStore, type StudioCameraPose } from './store'
import { captureComposite, downloadBlob, type ColorbarSpec } from './figureExport'

export interface StudioCaptureOpts {
  longEdgePx: number
  bars: ColorbarSpec[]
  filename: string
}
export type StudioCaptureFn = (opts: StudioCaptureOpts) => Promise<void>

type OrbitLike = { target: THREE.Vector3; update: () => void } | null

/**
 * Lives inside the R3F Canvas so it can reach the renderer, camera, and orbit
 * controls. It (1) registers the high-resolution capture function for the toolbar
 * button, and (2) services camera save / apply requests (bumped as nonces from the
 * store) so a Figure preset can re-frame the scene to an exact, reproducible view.
 */
export default function StudioCaptureBridge({
  captureRef,
}: {
  captureRef: MutableRefObject<StudioCaptureFn | null>
}) {
  const gl = useThree((s) => s.gl)
  const scene = useThree((s) => s.scene)
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera
  const controls = useThree((s) => s.controls) as OrbitLike

  const saveNonce = useStudioStore((s) => s.cameraSaveNonce)
  const applyNonce = useStudioStore((s) => s.cameraApplyNonce)
  const savedCamera = useStudioStore((s) => s.savedCamera)
  const setSavedCamera = useStudioStore((s) => s.setSavedCamera)

  // Save: read the live camera + orbit target into the store (nonce-gated so the
  // first render, nonce 0, does not save).
  useEffect(() => {
    if (saveNonce === 0) return
    const t = controls?.target
    setSavedCamera({
      position: [camera.position.x, camera.position.y, camera.position.z],
      target: t ? [t.x, t.y, t.z] : [0, 0, 0],
      fov: camera.fov,
    })
  }, [saveNonce]) // eslint-disable-line react-hooks/exhaustive-deps

  // Apply: drive the live camera to the saved pose.
  useEffect(() => {
    if (applyNonce === 0 || !savedCamera) return
    applyPose(camera, controls, savedCamera)
  }, [applyNonce]) // eslint-disable-line react-hooks/exhaustive-deps

  // Register the imperative capture fn for the toolbar button.
  useEffect(() => {
    captureRef.current = async ({ longEdgePx, bars, filename }) => {
      const blob = await captureComposite(gl, scene, camera, longEdgePx, bars)
      downloadBlob(blob, filename)
    }
    return () => {
      captureRef.current = null
    }
  }, [gl, scene, camera, captureRef])

  return null
}

function applyPose(camera: THREE.PerspectiveCamera, controls: OrbitLike, pose: StudioCameraPose): void {
  camera.position.set(pose.position[0], pose.position[1], pose.position[2])
  camera.fov = pose.fov
  camera.updateProjectionMatrix()
  if (controls) {
    controls.target.set(pose.target[0], pose.target[1], pose.target[2])
    controls.update()
  } else {
    camera.lookAt(new THREE.Vector3(pose.target[0], pose.target[1], pose.target[2]))
  }
}
