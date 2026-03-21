import { useSceneStore } from '@/stores/scene'

export default function LayersPanel() {
  const voxelData = useSceneStore(s => s.voxelData)
  const layerVisibility = useSceneStore(s => s.layerVisibility)
  const toggleLayer = useSceneStore(s => s.toggleLayer)
  const envMode = useSceneStore(s => s.envDisplayMode)
  const setEnvMode = useSceneStore(s => s.setEnvDisplayMode)
  const caps = useSceneStore(s => s.capabilities)

  if (!voxelData) return <p className="text-xs text-muted-foreground">No voxel data loaded</p>

  // Count voxels per material
  const counts: Record<string, number> = {}
  const { materialIndices, meta } = voxelData
  for (let i = 0; i < materialIndices.length; i++) {
    const name = meta.materials[materialIndices[i]]
    counts[name] = (counts[name] ?? 0) + 1
  }

  const selectClass = "w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground"

  return (
    <div>
      {meta.materials.map(mat => (
        <button
          key={mat}
          onClick={() => toggleLayer(mat)}
          className={`block w-full text-left px-2 py-1 my-0.5 rounded text-xs border transition-all ${
            layerVisibility[mat]
              ? 'bg-accent/10 border-accent/50 text-foreground'
              : 'bg-background border-border/50 text-muted-foreground opacity-40'
          }`}
        >
          {mat} ({(counts[mat] ?? 0).toLocaleString()})
        </button>
      ))}

      {/* Environment display mode */}
      <label className="text-xs text-muted-foreground block mt-3 mb-1">Show environment as</label>
      <select className={selectClass} value={envMode} onChange={e => setEnvMode(e.target.value as 'cubes' | 'hull' | 'tiles')}>
        <option value="cubes">Voxel cubes</option>
        {caps?.voxel_rt_available && <option value="hull">Hull mesh</option>}
        {caps?.has_tiles && <option value="tiles">GLB tiles</option>}
      </select>
    </div>
  )
}
