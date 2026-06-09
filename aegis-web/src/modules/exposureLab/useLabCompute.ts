import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { isClientError } from '@/api/client'
import { useNotificationStore } from '@/stores/notifications'
import { useLabStore } from './store'
import { poseBody, computeDose, type ComputeDoseParams, type LabSource } from './api'

// Debounce window after the last settled change before we hit the server.
const DEBOUNCE_MS = 250

// Build the /api/lab/compute request body from a store snapshot. We always send
// the live 66-vector `pose` (never `preset`) so gizmo/slider edits are honored,
// and phonePos is passed straight through as source.position because the lab
// renders in the raw SMPL-X frame (no grounding offset, see PosableBody).
function buildComputeParams(s: ReturnType<typeof useLabStore.getState>): ComputeDoseParams {
  const source: LabSource =
    s.sourceMode === 'near'
      ? {
          kind: 'near',
          pattern_id: s.patternId,
          position: s.phonePos,
          yaw: s.yaw,
          pitch: s.pitch,
          roll: s.roll,
        }
      : {
          kind: 'far',
          theta_inc: s.thetaInc,
          phi_inc: s.phiInc,
          pol_angle: s.polAngle,
        }

  return {
    gender: s.gender,
    betas: s.betas,
    pose: s.pose,
    freq_mhz: s.freqMhz,
    power_w: s.powerW,
    physics: {
      diffraction_model: s.diffractionModel,
      self_shadow: s.selfShadow,
      curvature: s.curvature,
      fresnel: s.fresnel,
      polarisation: s.polarisation,
    },
    source,
  }
}

// Live-update loop: debounce settled lab-store changes, then run the
// authoritative server pipeline (re-pose -> dose) guarded by a request id so a
// stale response can never overwrite a newer result. Mount once while the lab
// is open.
export function useLabCompute(): void {
  // Trigger on every dose-affecting input. We read fresh values from getState()
  // at fire time, so these selectors exist only to schedule the debounce.
  const gender = useLabStore((s) => s.gender)
  const betas = useLabStore((s) => s.betas)
  const pose = useLabStore((s) => s.pose)
  const sourceMode = useLabStore((s) => s.sourceMode)
  const patternId = useLabStore((s) => s.patternId)
  const phonePos = useLabStore((s) => s.phonePos)
  const yaw = useLabStore((s) => s.yaw)
  const pitch = useLabStore((s) => s.pitch)
  const roll = useLabStore((s) => s.roll)
  const powerW = useLabStore((s) => s.powerW)
  const thetaInc = useLabStore((s) => s.thetaInc)
  const phiInc = useLabStore((s) => s.phiInc)
  const polAngle = useLabStore((s) => s.polAngle)
  const freqMhz = useLabStore((s) => s.freqMhz)
  const diffractionModel = useLabStore((s) => s.diffractionModel)
  const selfShadow = useLabStore((s) => s.selfShadow)
  const curvature = useLabStore((s) => s.curvature)
  const fresnel = useLabStore((s) => s.fresnel)
  const polarisation = useLabStore((s) => s.polarisation)

  // Monotonic request id. Each fire captures myId; after every await we bail if
  // a newer fire has bumped the ref, so only the latest pipeline writes state.
  const latestRef = useRef(0)
  // Track the mesh-defining inputs from the previous run to decide whether to
  // clear the stale heatmap (a pose/shape change invalidates the posed mesh).
  const prevMeshRef = useRef<{ gender: string; betas: number[]; pose: number[] } | null>(null)

  useEffect(() => {
    const store = useLabStore.getState()
    const {
      setPosedMesh,
      setResults,
      clearResults,
      setComputing,
      setAveraging,
    } = store

    // Leading edge: if the pose or shape changed, drop the stale authoritative
    // mesh + heatmap so PosableBody reverts to the live LBS preview immediately.
    // Pure source/physics changes keep the old mesh and just recompute.
    const prev = prevMeshRef.current
    const meshChanged =
      !prev ||
      prev.gender !== gender ||
      prev.pose !== pose ||
      prev.betas !== betas
    if (meshChanged && prev) {
      clearResults()
      setPosedMesh(null, null, null)
    }
    prevMeshRef.current = { gender, betas, pose }

    const timer = setTimeout(() => {
      const myId = ++latestRef.current
      const isStale = () => myId !== latestRef.current

      const run = async () => {
        setComputing(true)
        try {
          // Authoritative re-pose in the raw SMPL-X frame.
          const body = await poseBody({ gender, betas, pose })
          if (isStale()) return
          setPosedMesh(body.positions, body.normals, body.vertexHash)

          const params = buildComputeParams(useLabStore.getState())

          // Phase 1: raw Sab heatmap only. Skipping the 4 cm^2 averaging build
          // (the dominant new-pose cost) gets the heatmap on screen in ~0.5 s.
          // The server bakes the visibility LUT inside this call.
          const fast = await computeDose(params, undefined, ['sab'])
          if (isStale()) return
          setResults(fast.sab, fast.stats, fast.arrays)
          setComputing(false)

          // Phase 2: 4 cm^2 averaging + ICNIRP, off the interactive path. The
          // posed body and kernel are server-cached, so this only pays the
          // averaging build, then fills the metric the heatmap is already showing.
          setAveraging(true)
          const full = await computeDose(params, undefined, ['sab', 'sab_4cm2'])
          if (isStale()) return
          setResults(full.sab, full.stats, full.arrays)
        } catch (err) {
          if (isStale()) return
          if (isClientError(err)) {
            useNotificationStore.getState().addNotification('warning', (err as Error).message)
          } else {
            Sentry.captureException(err)
          }
        } finally {
          // Only the latest pipeline owns the loading flags; a stale run that was
          // superseded must not flip them off under the newer run.
          if (!isStale()) {
            setComputing(false)
            setAveraging(false)
          }
        }
      }

      void run()
    }, DEBOUNCE_MS)

    return () => clearTimeout(timer)
  }, [
    gender,
    betas,
    pose,
    sourceMode,
    patternId,
    phonePos,
    yaw,
    pitch,
    roll,
    powerW,
    thetaInc,
    phiInc,
    polAngle,
    freqMhz,
    diffractionModel,
    selfShadow,
    curvature,
    fresnel,
    polarisation,
  ])
}
