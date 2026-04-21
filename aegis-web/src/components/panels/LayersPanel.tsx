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
  const hullStatus = useSceneStore(s => s.hullMeshStatus)
  const setHullStatus = useSceneStore(s => s.setHullMeshStatus)

  const bodyMeshVisible = useSceneStore(s => s.bodyMeshVisible)
  const toggleBodyMesh = useSceneStore(s => s.toggleBodyMeshVisible)
  const groundPlaneVisible = useSceneStore(s => s.groundPlaneVisible)
  const toggleGroundPlane = useSceneStore(s => s.toggleGroundPlaneVisible)
  const gridVisible = useSceneStore(s => s.gridVisible)
  const toggleGrid = useSceneStore(s => s.toggleGridVisible)
  const complianceRingVisible = useSceneStore(s => s.complianceRingVisible)
  const toggleComplianceRing = useSceneStore(s => s.toggleComplianceRingVisible)
  const complianceVolumeVisible = useSceneStore(s => s.complianceVolumeVisible)
  const toggleComplianceVolume = useSceneStore(s => s.toggleComplianceVolumeVisible)

  const hasVoxels = !!voxelData
  const hasSceneGeo = !!sceneGeometry

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
      {/* Scene element toggles (always visible) */}
      <label className="text-xs text-muted-foreground block mb-1">Scene elements</label>
      <button onClick={toggleBodyMesh} className={toggleClass(bodyMeshVisible)}>
        Body mesh
      </button>
      <button onClick={toggleGroundPlane} className={toggleClass(groundPlaneVisible)}>
        Ground plane
      </button>
      <button onClick={toggleGrid} className={toggleClass(gridVisible)}>
        Grid
      </button>
      <button onClick={toggleComplianceRing} className={toggleClass(complianceRingVisible)}>
        Compliance ring
      </button>
      <button onClick={toggleComplianceVolume} className={toggleClass(complianceVolumeVisible)}>
        Compliance volume (3-D)
      </button>

      {/* Scene geometry toggle */}
      {hasSceneGeo && (
        <button onClick={toggleSceneGeo} className={toggleClass(sceneGeoVisible)}>
          Scene geometry
        </button>
      )}

      {/* Voxel material toggles */}
      {hasVoxels && (
        <>
          <label className="text-xs text-muted-foreground block mt-3 mb-1">Materials</label>
          {voxelData!.meta.materials.map(mat => (
            <button key={mat} onClick={() => toggleLayer(mat)} className={toggleClass(layerVisibility[mat])}>
              {mat} ({(counts[mat] ?? 0).toLocaleString()})
            </button>
          ))}
        </>
      )}

      {/* Environment display mode */}
      {hasVoxels && (
        <>
          <label className="text-xs text-muted-foreground block mt-3 mb-1">Show environment as</label>
          <select className={selectClass} value={envMode} onChange={e => setEnvMode(e.target.value as 'cubes' | 'hull' | 'tiles')}>
            <option value="cubes">Voxel cubes</option>
            {caps?.voxel_rt_available && <option value="hull">Hull mesh</option>}
            {caps?.has_tiles && <option value="tiles">GLB tiles</option>}
          </select>

          {envMode === 'hull' && hullStatus === 'idle' && (
            <div className="mt-2 p-2 rounded border border-amber-500/30 bg-amber-500/5 text-xs text-muted-foreground">
              <p className="mb-1.5">Computing the hull mesh may take a few seconds.</p>
              <button
                onClick={() => setHullStatus('computing')}
                className="w-full px-2 py-1 rounded bg-accent text-accent-foreground text-xs font-medium hover:bg-accent/80 transition-colors"
              >
                Compute hull mesh
              </button>
            </div>
          )}

          {envMode === 'hull' && hullStatus === 'computing' && (
            <div className="mt-2 p-2 rounded border border-border bg-muted/30 text-xs text-muted-foreground flex items-center gap-2">
              <svg className="animate-spin size-3.5 shrink-0" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Computing hull mesh...
            </div>
          )}

          {envMode === 'hull' && hullStatus === 'ready' && (
            <p className="mt-1.5 text-[10px] text-muted-foreground/70">
              Wireframe enabled. Toggle off with the wireframe button in the toolbar.
            </p>
          )}

          {envMode === 'hull' && hullStatus === 'error' && (
            <div className="mt-2 p-2 rounded border border-destructive/30 bg-destructive/5 text-xs text-destructive">
              <p className="mb-1.5">Failed to compute hull mesh.</p>
              <button
                onClick={() => setHullStatus('computing')}
                className="w-full px-2 py-1 rounded bg-destructive text-destructive-foreground text-xs font-medium hover:bg-destructive/80 transition-colors"
              >
                Retry
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
