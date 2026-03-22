import { useSceneStore } from '@/stores/scene'

export default function LayersPanel() {
  const voxelData = useSceneStore(s => s.voxelData)
  const layerVisibility = useSceneStore(s => s.layerVisibility)
  const toggleLayer = useSceneStore(s => s.toggleLayer)
  const envMode = useSceneStore(s => s.envDisplayMode)
  const setEnvMode = useSceneStore(s => s.setEnvDisplayMode)
  const caps = useSceneStore(s => s.capabilities)
  const sceneGeometry = useSceneStore(s => s.sceneGeometry)
  const sceneGeoVisible = useSceneStore(s => s.sceneGeometryVisible)
  const toggleSceneGeo = useSceneStore(s => s.toggleSceneGeometryVisible)

  const hasVoxels = !!voxelData
  const hasSceneGeo = !!sceneGeometry

  if (!hasVoxels && !hasSceneGeo) {
    return <p className="text-xs text-muted-foreground">No environment data loaded. Load a scene or location first.</p>
  }

  // Count voxels per material
  const counts: Record<string, number> = {}
  if (voxelData) {
    const { materialIndices, meta } = voxelData
    for (let i = 0; i < materialIndices.length; i++) {
      const name = meta.materials[materialIndices[i]]
      counts[name] = (counts[name] ?? 0) + 1
    }
  }

  const selectClass = "w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground"
  const toggleClass = (on: boolean) =>
    `block w-full text-left px-2 py-1 my-0.5 rounded text-xs border transition-all ${
      on ? 'bg-accent/10 border-accent/50 text-foreground' : 'bg-background border-border/50 text-muted-foreground opacity-40'
    }`

  return (
    <div>
      {/* Scene geometry toggle */}
      {hasSceneGeo && (
        <button onClick={toggleSceneGeo} className={toggleClass(sceneGeoVisible)}>
          Scene geometry
        </button>
      )}

      {/* Voxel material toggles */}
      {hasVoxels && voxelData!.meta.materials.map(mat => (
        <button key={mat} onClick={() => toggleLayer(mat)} className={toggleClass(layerVisibility[mat])}>
          {mat} ({(counts[mat] ?? 0).toLocaleString()})
        </button>
      ))}

      {/* Environment display mode */}
      {hasVoxels && (
        <>
          <label className="text-xs text-muted-foreground block mt-3 mb-1">Show environment as</label>
          <select className={selectClass} value={envMode} onChange={e => setEnvMode(e.target.value as 'cubes' | 'hull' | 'tiles')}>
            <option value="cubes">Voxel cubes</option>
            {caps?.voxel_rt_available && <option value="hull">Hull mesh</option>}
            {caps?.has_tiles && <option value="tiles">GLB tiles</option>}
          </select>
        </>
      )}
    </div>
  )
}
