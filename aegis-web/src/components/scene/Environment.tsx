import { useEffect } from 'react'
import * as Sentry from '@sentry/react'
import { useGLTF } from '@react-three/drei'
import { useSceneStore } from '@/stores/scene'
import { fetchTileList } from '@/api/client'

export default function Environment() {
  const caps = useSceneStore(s => s.capabilities)
  const envMode = useSceneStore(s => s.envDisplayMode)
  const glbTiles = useSceneStore(s => s.glbTiles)

  useEffect(() => {
    if (!caps?.has_tiles) return
    fetchTileList().then(data => {
      useSceneStore.setState({ glbTiles: data.tiles })
    }).catch(err => Sentry.captureException(err))
  }, [caps?.has_tiles])

  if (envMode !== 'tiles' || glbTiles.length === 0) return null

  return (
    <group>
      {glbTiles.map(name => (
        <TileModel key={name} filename={name} />
      ))}
    </group>
  )
}

function TileModel({ filename }: { filename: string }) {
  const { scene } = useGLTF(`/api/tiles/${filename}`)
  return <primitive object={scene.clone()} />
}
