import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import * as Sentry from '@sentry/react'
import { isClientError } from '@/api/client'
import { useNotificationStore } from '@/stores/notifications'
import BodyMeshInstance from '@/components/scene/BodyMeshInstance'
import { useLabStore } from '../store'
import { getRig } from '../api'
import { forwardKinematics, skin } from '../lbs'

// The lab renders the body in the RAW SMPL-X frame (pelvis at the origin, Y-up).
// No grounding: the displayed frame must equal the frame the server computes in,
// so the phone position the user sets is passed straight through as source_pos
// for the near-field self-shadow query (query_visibility uses centroids -
// source_pos). Grounding here would offset that query by the feet-to-floor shift.

export default function PosableBody() {
  const gender = useLabStore(s => s.gender)
  const betas = useLabStore(s => s.betas)
  const pose = useLabStore(s => s.pose)
  const rig = useLabStore(s => s.rig)
  const posedVertices = useLabStore(s => s.posedVertices)
  const posedNormals = useLabStore(s => s.posedNormals)
  const sab = useLabStore(s => s.sab)
  const stats = useLabStore(s => s.stats)
  const setRig = useLabStore(s => s.setRig)

  // Fetch the rig whenever shape inputs change. A cancelled flag guards against
  // stale responses from races (e.g. rapid gender toggles).
  useEffect(() => {
    let cancelled = false
    getRig(gender, betas)
      .then(r => {
        if (!cancelled) setRig(r)
      })
      .catch(err => {
        if (cancelled) return
        if (isClientError(err)) {
          const msg = (err as Error)?.message ?? 'Lab rig request was rejected.'
          useNotificationStore.getState().addNotification('warning', msg)
        } else {
          Sentry.captureException(err)
        }
      })
    return () => {
      cancelled = true
    }
  }, [gender, betas, setRig])

  // Live client-side LBS preview: indexed geometry rebuilt only on rig/pose
  // change. This is the instant, no-round-trip mesh shown before dose exists.
  const previewGeom = useMemo(() => {
    if (!rig) return null
    const template = new Float32Array(rig.template)
    const weights = new Float32Array(rig.lbs_weights)
    const mats = forwardKinematics(rig.rest_joints, rig.parents, pose)
    const verts = skin(template, weights, mats, rig.n_joints)

    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(verts, 3))
    g.setIndex(new THREE.BufferAttribute(new Uint32Array(rig.faces), 1))
    g.computeVertexNormals()
    return g
  }, [rig, pose])

  // Authoritative server mesh: triangle soup (3 verts per triangle, no index),
  // matching body_to_binary. Cloned so geometry ops never mutate the store array.
  // A neutral color attribute is required by BodyMeshInstance's heatmap writer.
  const authGeom = useMemo(() => {
    if (!posedVertices) return null
    const positions = new Float32Array(posedVertices)
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    if (posedNormals) {
      g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(posedNormals), 3))
    }
    const colors = new Float32Array(positions.length)
    colors.fill(0.5)
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return g
  }, [posedVertices, posedNormals])

  // Dispose replaced geometries to avoid GPU memory leaks.
  useEffect(() => () => previewGeom?.dispose(), [previewGeom])
  useEffect(() => () => authGeom?.dispose(), [authGeom])

  // Prefer the heatmap on the authoritative mesh once dose exists; otherwise
  // fall back to the live preview. Task 20's live loop clears sab/posedVertices
  // on pose change, so this naturally reverts to the preview between computes.
  if (authGeom && sab) {
    return (
      <BodyMeshInstance
        geometry={authGeom}
        sabArray={sab}
        stats={stats}
        position={[0, 0, 0]}
        rotationY={0}
      />
    )
  }

  if (previewGeom) {
    return (
      <mesh geometry={previewGeom} castShadow>
        <meshStandardMaterial color="#8899aa" roughness={0.7} metalness={0.1} />
      </mesh>
    )
  }

  return null
}
