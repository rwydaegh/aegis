import { useMemo, type ReactNode } from 'react'
import {
  TilesRenderer,
  TilesPlugin,
  EastNorthUpFrame,
  TilesAttributionOverlay,
  GlobeControls,
} from '3d-tiles-renderer/r3f'
import { GoogleCloudAuthPlugin } from '3d-tiles-renderer/plugins'
import { useEnvironmentStore } from '@/stores/environment'
import { useUIStore } from '@/stores/ui'

interface Props {
  children: ReactNode
}

export function Environment3DTiles({ children }: Props) {
  const location = useEnvironmentStore((s) => s.location)
  const apiKey = useEnvironmentStore((s) => s.googleApiKey)
  const cameraMode = useUIStore((s) => s.cameraMode)

  const pluginArgs = useMemo(
    () => ({
      apiToken: apiKey,
      logoUrl: '/google-maps-logo.png',
    }),
    [apiKey],
  )

  if (!location || !apiKey) return <>{children}</>

  return (
    <TilesRenderer>
      <TilesPlugin plugin={GoogleCloudAuthPlugin} args={pluginArgs} />
      <TilesAttributionOverlay
        style={{ position: 'absolute', right: 10, bottom: 10, left: 'auto' }}
      />
      {cameraMode === 'globe' && <GlobeControls />}
      <EastNorthUpFrame
        lat={(location.lat * Math.PI) / 180}
        lon={(location.lon * Math.PI) / 180}
      >
        {children}
      </EastNorthUpFrame>
    </TilesRenderer>
  )
}
