import { useMemo, useEffect, useRef, type ReactNode } from 'react'
import { useThree } from '@react-three/fiber'
import * as THREE from 'three'
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

// WGS84 semi-major axis in meters
const WGS84_A = 6378137.0

/** Convert lat/lon (radians) + altitude (meters) to ECEF position. */
function latLonToECEF(latRad: number, lonRad: number, altitude: number): THREE.Vector3 {
  const r = WGS84_A + altitude
  const cosLat = Math.cos(latRad)
  return new THREE.Vector3(
    r * cosLat * Math.cos(lonRad),
    r * cosLat * Math.sin(lonRad),
    r * Math.sin(latRad),
  )
}

interface Props {
  children: ReactNode
}

/** Position the camera above the given lat/lon on mount. */
function GlobeCameraInit({ latRad, lonRad }: { latRad: number; lonRad: number }) {
  const { camera } = useThree()
  const lastLocation = useRef('')

  useEffect(() => {
    const key = `${latRad},${lonRad}`
    if (key === lastLocation.current) return
    lastLocation.current = key

    const pos = latLonToECEF(latRad, lonRad, 800)
    camera.position.copy(pos)
    // Look toward the center of the Earth
    camera.lookAt(0, 0, 0)
    // Widen clipping planes for globe scale - GlobeControls will refine these
    camera.near = 1
    camera.far = WGS84_A * 4
    camera.updateProjectionMatrix()
  }, [camera, latRad, lonRad])

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
      <EastNorthUpFrame lat={latRad} lon={lonRad}>
        {children}
      </EastNorthUpFrame>
    </TilesRenderer>
  )
}
