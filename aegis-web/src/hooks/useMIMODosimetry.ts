import { useEffect, useRef, useCallback } from 'react'
import { useMIMOStore } from '@/stores/mimo'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { computeMIMO, fetchMIMOResult, fetchMIMOSummary } from '@/api/mimo'
import { fetchBody } from '@/api/client'
import * as Sentry from '@sentry/react'
import * as THREE from 'three'
import type { MIMOComputeRequest, MIMOUserConfig } from '@/api/types'

async function loadMissingBodies() {
  const { users, setUserBodyGeometry } = useMIMOStore.getState()
  const promises: Promise<void>[] = []

  for (const [id, user] of users) {
    if (user.bodyGeometry) continue
    promises.push(
      fetchBody(user.phantomName).then(({ binary: { positions, normals } }) => {
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

    const setComputing = useUIStore.getState().setComputing
    setComputing(true)

    try {
      await loadMissingBodies()
      if (gen !== generationRef.current) return

      const mimoUsers: MIMOUserConfig[] = [...useMIMOStore.getState().users.values()].map(u => ({
        id: u.userId,
        phantom: u.phantomName,
        position: u.position,
        orientation: u.orientation,
        device_offset: [0.25, 0, 1.4] as [number, number, number],
      }))

      const req: MIMOComputeRequest = {
        array: arrayConfig,
        users: mimoUsers,
        freq_hz: freqGhz * 1e9,
        power_dbm: powerDbm,
        precoder_type: precoderType,
      }

      const response = await computeMIMO(req, controller.signal)
      if (gen !== generationRef.current) return

      const { setUserResult, setSummaryStats, setPrecoderWeights } = useMIMOStore.getState()

      // Store precoder weights for antenna pattern visualization
      if (response.weights_real && response.weights_imag) {
        setPrecoderWeights({ real: response.weights_real, imag: response.weights_imag })
      }

      await Promise.all(
        response.user_ids.map(async (uid) => {
          const { sab, stats } = await fetchMIMOResult(uid, controller.signal)
          if (gen !== generationRef.current) return
          setUserResult(uid, sab, stats)
        })
      )
      if (gen !== generationRef.current) return

      const summary = await fetchMIMOSummary(controller.signal)
      if (gen === generationRef.current) {
        // Propagate backend warning to summary for UI display
        if (response.warning && !summary.warning) {
          summary.warning = response.warning
        }
        setSummaryStats(summary)
        const warningMsg = summary.warning ?? response.warning
        if (warningMsg) {
          useNotificationStore.getState().addNotification(
            'warning',
            warningMsg,
            'The antenna may be too close to the ground. A height of at least 0.5 m above the phantom improves channel conditioning.'
          )
        } else {
          const allZero = summary.users.every((u: { p_abs_mw: number }) => u.p_abs_mw === 0)
          if (allZero && summary.users.length > 0) {
            useNotificationStore.getState().addNotification(
              'warning',
              'All MIMO users show 0 W/m\u00b2. Try elevating the antenna above ground level.',
              'The antenna may be too close to the ground. A height of at least 0.5 m above the phantom improves channel conditioning.'
            )
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification(
        'error',
        `MIMO compute failed: ${(err as Error).message ?? err}`,
        'This error has been reported and will be fixed automatically using AI. Most issues are fixed in less than 30 minutes.'
      )
    } finally {
      if (gen === generationRef.current) setComputing(false)
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
