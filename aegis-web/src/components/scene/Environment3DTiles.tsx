import { useMemo, useEffect, useRef, type ReactNode } from 'react'
import { useThree } from '@react-three/fiber'
import {
  TilesRenderer,
  TilesPlugin,
  EastNorthUpFrame,
  TilesAttributionOverlay,
  GlobeControls,
} from '3d-tiles-renderer/r3f'
import { GoogleCloudAuthPlugin } from '3d-tiles-renderer/plugins'
import { useEnvironmentStore } from '@/stores/environment'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { WGS84_A, latLonRadToECEF } from '@/lib/geo'

interface Props {
  children: ReactNode
}

/** Position the camera above the given lat/lon. Re-centers every time location changes. */
function GlobeCameraInit({ latRad, lonRad }: { latRad: number; lonRad: number }) {
  const { camera } = useThree()
  const lastKey = useRef('')

  useEffect(() => {
    const key = `${latRad},${lonRad}`
    if (key === lastKey.current) return
    lastKey.current = key

    const surfacePos = latLonRadToECEF(latRad, lonRad, 0)
    const cameraPos = latLonRadToECEF(latRad, lonRad, 800)
    camera.position.copy(cameraPos)
    // Look at the surface point directly below, not Earth's center
    camera.lookAt(surfacePos)
    camera.near = 1
    camera.far = WGS84_A * 4
    camera.updateProjectionMatrix()
  }, [camera, latRad, lonRad])

  return null
}

/**
 * Re-center camera when user clicks search again (even for the same query).
 * The environment store bumps a counter each geocode; we watch it here.
 */
function GlobeCameraRecenter({ latRad, lonRad }: { latRad: number; lonRad: number }) {
  const { camera } = useThree()
  const geocodeCount = useEnvironmentStore((s) => s.geocodeCount)
  const lastCount = useRef(geocodeCount)

  useEffect(() => {
    if (geocodeCount === lastCount.current) return
    lastCount.current = geocodeCount

    const surfacePos = latLonRadToECEF(latRad, lonRad, 0)
    const cameraPos = latLonRadToECEF(latRad, lonRad, 800)
    camera.position.copy(cameraPos)
    camera.lookAt(surfacePos)
    camera.updateProjectionMatrix()
  }, [camera, latRad, lonRad, geocodeCount])

  return null
}

export function Environment3DTiles({ children }: Props) {
  const location = useEnvironmentStore((s) => s.location)
  const apiKey = useSceneStore((s) => s.capabilities?.google_api_key ?? '')
  const cameraMode = useUIStore((s) => s.cameraMode)

  const pluginArgs = useMemo(
    () => ({
      apiToken: apiKey,
      logoUrl: '/google-maps-logo.png',
    }),
    [apiKey],
  )

  const latRad = location ? (location.lat * Math.PI) / 180 : 0
  const lonRad = location ? (location.lon * Math.PI) / 180 : 0

  if (!location || !apiKey) return <>{children}</>

  return (
    <TilesRenderer>
      <TilesPlugin plugin={GoogleCloudAuthPlugin} args={pluginArgs as any} />
      <TilesAttributionOverlay
        style={{ position: 'absolute', right: 10, bottom: 10, left: 'auto' }}
      />
      {cameraMode === 'globe' && <GlobeControls />}
      <GlobeCameraInit latRad={latRad} lonRad={lonRad} />
      <GlobeCameraRecenter latRad={latRad} lonRad={lonRad} />
      <EastNorthUpFrame lat={latRad} lon={lonRad}>
        {/* ENU frame has Z-up but Three.js scene assumes Y-up.
            Rotate +90deg around X so Y-up children stand upright and
            XZ-plane physics operate on the ENU ground plane (XY). */}
        <group rotation={[Math.PI / 2, 0, 0]}>
          {children}
        </group>
      </EastNorthUpFrame>
    </TilesRenderer>
  )
}
