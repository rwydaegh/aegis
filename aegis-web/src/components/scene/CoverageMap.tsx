import { APIProvider, Map } from '@vis.gl/react-google-maps'
import { useSceneStore } from '@/stores/scene'

export function CoverageMap() {
  const googleApiKey = useSceneStore(s => s.capabilities?.google_api_key) ?? ''

  if (!googleApiKey) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-zinc-950 text-zinc-400 text-sm">
        Google API key not configured. Set GOOGLE_API_KEY on the server.
      </div>
    )
  }

  return (
    <APIProvider apiKey={googleApiKey}>
      <Map
        style={{ width: '100%', height: '100%' }}
        defaultCenter={{ lat: 48.8, lng: 2.3 }}
        defaultZoom={4}
        mapTypeId="hybrid"
        mapId={import.meta.env.VITE_GOOGLE_MAP_ID || undefined}
        disableDefaultUI
        gestureHandling="greedy"
        clickableIcons={false}
      />
    </APIProvider>
  )
}
