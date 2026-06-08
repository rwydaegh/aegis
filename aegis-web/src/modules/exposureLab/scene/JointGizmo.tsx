import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useThree } from '@react-three/fiber'
import { TransformControls } from '@react-three/drei'
import { useLabStore } from '../store'
import { CURATED_JOINTS, posedJointTransforms } from '../lbs'

// Reused scratch quaternions to keep the objectChange handler allocation-light.
const _qWorld = new THREE.Quaternion()
const _qParent = new THREE.Quaternion()
const _qLocal = new THREE.Quaternion()

// Interactive rotation gizmo. Renders a clickable handle at each curated joint's
// world position; selecting one attaches a rotate TransformControls to a proxy
// object placed at that joint. Dragging converts the proxy's new world rotation
// back into the joint's LOCAL pose axis-angle and writes it into the store.
export default function JointGizmo() {
  const rig = useLabStore(s => s.rig)
  const pose = useLabStore(s => s.pose)
  const selectedJoint = useLabStore(s => s.selectedJoint)
  const setSelectedJoint = useLabStore(s => s.setSelectedJoint)
  const setPose = useLabStore(s => s.setPose)

  const controls = useThree(s => s.controls) as { enabled: boolean } | null

  // Proxy object the TransformControls attaches to. Mounted at the scene root so
  // its local quaternion equals its world quaternion.
  const proxyRef = useRef<THREE.Object3D>(new THREE.Object3D())
  const draggingRef = useRef(false)

  // Joint world transforms, recomputed when rig or pose changes.
  const transforms = useMemo(() => {
    if (!rig) return null
    return posedJointTransforms(rig.rest_joints, rig.parents, pose)
  }, [rig, pose])

  // Sync the proxy to the selected joint's world pose, except while dragging
  // (the controls own the proxy then). New-pose world rotation equals the proxy
  // rotation by construction, so this resync is a no-op visually after a drag.
  useEffect(() => {
    if (draggingRef.current) return
    if (!transforms || selectedJoint == null) return
    const proxy = proxyRef.current
    proxy.position.set(
      transforms.positions[selectedJoint * 3],
      transforms.positions[selectedJoint * 3 + 1],
      transforms.positions[selectedJoint * 3 + 2],
    )
    proxy.quaternion.set(
      transforms.worldQuats[selectedJoint * 4],
      transforms.worldQuats[selectedJoint * 4 + 1],
      transforms.worldQuats[selectedJoint * 4 + 2],
      transforms.worldQuats[selectedJoint * 4 + 3],
    )
    proxy.updateMatrixWorld()
  }, [transforms, selectedJoint])

  if (!rig || !transforms) return null

  const parents = rig.parents

  // R_local_new = R_world_parent^{-1} * R_world_proxy, then log() to axis-angle.
  const onObjectChange = () => {
    if (selectedJoint == null) return
    const proxy = proxyRef.current
    _qWorld.copy(proxy.quaternion)

    const parent = parents[selectedJoint]
    if (parent === -1 || transforms == null) {
      _qParent.identity()
    } else {
      _qParent.set(
        transforms.worldQuats[parent * 4],
        transforms.worldQuats[parent * 4 + 1],
        transforms.worldQuats[parent * 4 + 2],
        transforms.worldQuats[parent * 4 + 3],
      )
    }
    _qLocal.copy(_qParent).invert().multiply(_qWorld).normalize()

    // Shortest-arc representative, then quaternion log -> rotation vector.
    if (_qLocal.w < 0) {
      _qLocal.set(-_qLocal.x, -_qLocal.y, -_qLocal.z, -_qLocal.w)
    }
    const sinHalf = Math.sqrt(_qLocal.x * _qLocal.x + _qLocal.y * _qLocal.y + _qLocal.z * _qLocal.z)
    const angle = 2 * Math.atan2(sinHalf, _qLocal.w)
    let ax = 0
    let ay = 0
    let az = 0
    if (sinHalf > 1e-8) {
      const scale = angle / sinHalf
      ax = _qLocal.x * scale
      ay = _qLocal.y * scale
      az = _qLocal.z * scale
    }

    const next = pose.slice()
    next[selectedJoint * 3] = ax
    next[selectedJoint * 3 + 1] = ay
    next[selectedJoint * 3 + 2] = az
    setPose(next)
  }

  const onDraggingChanged = (e: { value: boolean }) => {
    draggingRef.current = e.value
    if (controls) controls.enabled = !e.value
  }

  return (
    <>
      <primitive object={proxyRef.current} />

      {CURATED_JOINTS.map(({ index }) => (
        <mesh
          key={index}
          position={[
            transforms.positions[index * 3],
            transforms.positions[index * 3 + 1],
            transforms.positions[index * 3 + 2],
          ]}
          onClick={e => {
            e.stopPropagation()
            setSelectedJoint(index)
          }}
        >
          <sphereGeometry args={[0.022, 16, 16]} />
          <meshBasicMaterial
            color={selectedJoint === index ? '#ffcc44' : '#44aaff'}
            transparent
            opacity={selectedJoint === index ? 1 : 0.7}
            depthTest={false}
          />
        </mesh>
      ))}

      {selectedJoint != null && (
        <TransformControls
          object={proxyRef.current}
          mode="rotate"
          size={0.7}
          onObjectChange={onObjectChange}
          onMouseDown={() => onDraggingChanged({ value: true })}
          onMouseUp={() => onDraggingChanged({ value: false })}
        />
      )}
    </>
  )
}
