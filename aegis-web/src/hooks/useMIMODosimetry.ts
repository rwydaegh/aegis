import { useEffect, useRef, useCallback } from 'react'
import { useMIMOStore } from '@/stores/mimo'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { computeMIMO, fetchMIMOResult, fetchMIMOSummary } from '@/api/mimo'
import { fetchBody } from '@/api/client'
import * as THREE from 'three'
import type { MIMOComputeRequest, MIMOComputeResponse, MIMOSummary, MIMOUserConfig } from '@/api/types'
import { handleDosimetryError } from './_dosimetryResult'

const LOW_ANTENNA_HINT =
  'The antenna may be too close to the ground. A height of at least 0.5 m above the phantom improves channel conditioning.'
const MIMO_TIMEOUT_MS = 120_000
const FALLBACK_DEVICE_OFFSET: [number, number, number] = [0, 0.30, 1.4]

async function loadMissingBodies(signal?: AbortSignal) {
  const { users, setUserBodyGeometry } = useMIMOStore.getState()
  const promises: Promise<void>[] = []

  for (const [id, user] of users) {
    if (user.bodyGeometry) continue
    promises.push(
      fetchBody(user.phantomName, signal).then(({ binary: { positions, normals } }) => {
        const geo = new THREE.BufferGeometry()
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
        geo.setAttribute('normal', new THREE.BufferAttribute(normals, 3))
        const colors = new Float32Array(positions.length)
        colors.fill(0.5)
        geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
        geo.computeBoundingBox()
        const bb = geo.boundingBox!
        if (bb.min.y < 0) {
          geo.translate(0, -bb.min.y, 0)
          geo.computeBoundingBox()
        }
        geo.computeBoundingSphere()
        setUserBodyGeometry(id, geo)
      })
    )
  }
  await Promise.all(promises)
}

/** Snapshot the MIMO store + simulation inputs into a backend request. */
function buildMIMORequest(
  arrayConfig: MIMOComputeRequest['array'],
  freqGhz: number,
  powerDbm: number,
  precoderType: MIMOComputeRequest['precoder_type'],
): MIMOComputeRequest {
  const deviceOffsets = useSceneStore.getState().capabilities?.body_device_offsets ?? {}
  const override = useMIMOStore.getState().deviceOffsetOverride

  const mimoUsers: MIMOUserConfig[] = [...useMIMOStore.getState().users.values()].map(u => ({
    id: u.userId,
    phantom: u.phantomName,
    position: u.position,
    orientation: u.orientation,
    device_offset: override
      ?? (deviceOffsets[u.phantomName] as [number, number, number])
      ?? FALLBACK_DEVICE_OFFSET,
  }))

  return {
    array: arrayConfig,
    users: mimoUsers,
    freq_hz: freqGhz * 1e9,
    power_dbm: powerDbm,
    precoder_type: precoderType,
  }
}

/**
 * Fan out per-user result fetches and write them into the MIMO store. Aborts
 * cleanly if the caller's generation has been invalidated.
 */
async function fetchAndStoreUserResults(
  userIds: string[],
  signal: AbortSignal,
  isCurrent: () => boolean,
) {
  const { setUserResult } = useMIMOStore.getState()
  await Promise.all(
    userIds.map(async (uid) => {
      const { sab, stats } = await fetchMIMOResult(uid, signal)
      if (!isCurrent()) return
      setUserResult(uid, sab, stats)
    }),
  )
}

/**
 * Combine the MIMO summary with the top-level response warning, commit it to
 * the store, and surface any low-antenna warnings via the notification system.
 */
export function applyMIMOSummary(summary: MIMOSummary, response: MIMOComputeResponse) {
  const { setSummaryStats } = useMIMOStore.getState()

  // Propagate backend warning to summary for UI display
  if (response.warning && !summary.warning) {
    summary.warning = response.warning
  }
  if (response.ecbf_warnings?.length && !summary.ecbf_warnings?.length) {
    summary.ecbf_warnings = response.ecbf_warnings
  }
  setSummaryStats(summary)

  if (summary.ecbf_warnings?.length) {
    useNotificationStore.getState().addNotification(
      'warning',
      'ECBF precoder fell back to a min-absorption baseline; results may differ from your requested precoder.',
      summary.ecbf_warnings.join(' '),
    )
  }

  const warningMsg = summary.warning ?? response.warning
  if (warningMsg) {
    useNotificationStore.getState().addNotification('warning', warningMsg, LOW_ANTENNA_HINT)
    return
  }

  const allZero = summary.users.every((u: { p_abs_mw: number }) => u.p_abs_mw === 0)
  if (allZero && summary.users.length > 0) {
    useNotificationStore.getState().addNotification(
      'warning',
      'All MIMO users show 0 W/m\u00b2. Try elevating the antenna above ground level.',
      LOW_ANTENNA_HINT,
    )
  }
}

export function useMIMODosimetry() {
  const enabled = useMIMOStore(s => s.enabled)
  const precoderType = useMIMOStore(s => s.precoderType)
  const arrayConfig = useMIMOStore(s => s.arrayConfig)
  const configVersion = useMIMOStore(s => s._configVersion)
  const freqGhz = useSimulationStore(s => s.freqGhz)
  const powerDbm = useSimulationStore(s => s.powerDbm)

  const abortRef = useRef<AbortController | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const generationRef = useRef(0)

  const triggerCompute = useCallback(async () => {
    const { users } = useMIMOStore.getState()
    if (!enabled || !arrayConfig || users.size === 0) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const gen = ++generationRef.current
    const isCurrent = () => gen === generationRef.current

    // MIMO computes are heavier than single-user (scales with user count)
    const timeoutId = setTimeout(() => controller.abort('timeout'), MIMO_TIMEOUT_MS)
    const setComputing = useUIStore.getState().setComputing
    setComputing(true)
    useMIMOStore.getState().setLastComputeError(null)

    try {
      await loadMissingBodies(controller.signal)
      if (!isCurrent()) return

      const req = buildMIMORequest(arrayConfig, freqGhz, powerDbm, precoderType)
      const response = await computeMIMO(req, controller.signal)
      if (!isCurrent()) return
      useNotificationStore.getState().dismissByLevel('error')

      // Store precoder weights for antenna pattern visualization
      if (response.weights_real && response.weights_imag) {
        useMIMOStore.getState().setPrecoderWeights({
          real: response.weights_real,
          imag: response.weights_imag,
        })
      }

      await fetchAndStoreUserResults(response.user_ids, controller.signal, isCurrent)
      if (!isCurrent()) return

      const summary = await fetchMIMOSummary(controller.signal)
      if (!isCurrent()) return
      applyMIMOSummary(summary, response)
    } catch (err) {
      const summary = handleDosimetryError(err, {
        controller,
        timeoutMs: MIMO_TIMEOUT_MS,
        label: 'MIMO',
        networkLabel: 'MIMO',
        timeoutHint: 'Try reducing the number of users or using MRT precoder.',
      })
      // Don't clobber state on a normal cancellation (a fresher compute
      // already aborted us and is about to write its own results).
      if (summary !== null && isCurrent()) {
        useMIMOStore.getState().clearAllResults()
        useMIMOStore.getState().setLastComputeError(summary)
      }
    } finally {
      clearTimeout(timeoutId)
      if (isCurrent()) setComputing(false)
    }
  }, [enabled, precoderType, arrayConfig, freqGhz, powerDbm])

  useEffect(() => {
    if (!enabled || !arrayConfig) return
    if (timerRef.current) clearTimeout(timerRef.current)

    const config = useSceneStore.getState().viewerConfig
    const debounceMs = config?.interaction?.debounce_ms ?? 500
    timerRef.current = setTimeout(() => { void triggerCompute() }, debounceMs)

    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
    // configVersion tracks user add/remove/move - NOT result writes
  }, [enabled, precoderType, arrayConfig, freqGhz, powerDbm, configVersion, triggerCompute])

  useEffect(() => {
    return () => { abortRef.current?.abort() }
  }, [])
}
