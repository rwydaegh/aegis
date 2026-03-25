import { useEffect, useRef, useCallback } from 'react'
import { useMIMOStore } from '@/stores/mimo'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { computeMIMO, fetchMIMOResult, fetchMIMOSummary } from '@/api/mimo'
import { fetchBody } from '@/api/client'
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

      const { setUserResult, setSummaryStats } = useMIMOStore.getState()
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
        setSummaryStats(summary)
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      useNotificationStore.getState().addNotification(
        'error',
        `MIMO compute failed: ${(err as Error).message ?? err}`
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
