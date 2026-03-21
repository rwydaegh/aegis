import { useEffect, useState } from 'react'
import { useGLTF } from '@react-three/drei'
import { useSceneStore } from '@/stores/scene'
import { fetchTileList } from '@/api/client'

export default function Environment() {
  const caps = useSceneStore(s => s.capabilities)
  const envMode = useSceneStore(s => s.envDisplayMode)
  const [tiles, setTiles] = useState<string[]>([])

  useEffect(() => {
    if (!caps?.has_tiles) return
    fetchTileList().then(data => {
      setTiles(data.tiles)
      useSceneStore.setState({ glbTiles: data.tiles })
    }).catch(err => console.error('Failed to load tile list:', err))
  }, [caps?.has_tiles])

  if (envMode !== 'tiles' || tiles.length === 0) return null

  return (
    <group>
      {tiles.map(name => (
        <TileModel key={name} filename={name} />
      ))}
    </group>
  )
}

function TileModel({ filename }: { filename: string }) {
  const { scene } = useGLTF(`/api/tiles/${filename}`)
  return <primitive object={scene.clone()} />
}
