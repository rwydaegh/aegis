import { useSceneStore } from '@/stores/scene'

export default function RayTracingPanel() {
  const caps = useSceneStore(s => s.capabilities)
  const config = useSceneStore(s => s.viewerConfig)
  const rtEnabled = useSceneStore(s => s.rtEnabled)
  const rtSource = useSceneStore(s => s.rtSource)
  const rtMaxOrder = useSceneStore(s => s.rtMaxOrder)
  const scenes = useSceneStore(s => s.scenes)
  const loadedScenePath = useSceneStore(s => s.loadedScenePath)

  const hasDiffert = caps?.has_differt ?? false
  const hasSionna = caps?.has_sionna ?? false
  const hasVoxels = caps?.has_voxels ?? false
  const hasScenes = scenes.length > 0

  if (!hasDiffert && !hasSionna) {
    return <p className="text-xs text-muted-foreground">No ray tracing backend available</p>
  }

  const selectClass = "w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground"
  const labelClass = "text-xs text-muted-foreground block mt-2 mb-1"

  const needsScene = rtSource === 'differt' || rtSource === 'sionna'
  const sceneReady = needsScene ? !!loadedScenePath : true

  return (
    <div>
      <label className="flex items-center gap-2 text-xs text-foreground">
        <input type="checkbox" checked={rtEnabled}
          onChange={e => useSceneStore.setState({ rtEnabled: e.target.checked })} />
        Enable ray tracing
      </label>

      {rtEnabled && (
        <>
          <label className={labelClass}>RT backend</label>
          <select className={selectClass} value={rtSource}
            onChange={e => useSceneStore.setState({ rtSource: e.target.value as 'voxel' | 'differt' | 'sionna' })}>
            {hasVoxels && <option value="voxel">Voxel environment</option>}
            {hasDiffert && hasScenes && <option value="differt">Scene (DiffeRT)</option>}
            {hasSionna && hasScenes && <option value="sionna">Scene (Sionna RT)</option>}
          </select>

          {needsScene && !sceneReady && (
            <p className="text-xs text-amber-400 mt-1">Load a scene first (Scene panel above)</p>
          )}

          <label className={labelClass}>Max reflections</label>
          <select className={selectClass} value={rtMaxOrder}
            onChange={e => useSceneStore.setState({ rtMaxOrder: Number(e.target.value) })}>
            {(config?.dosimetry?.max_order_options ?? []).map(o => (
              <option key={o.value} value={o.value}>{o.label ?? `Order ${o.value}`}</option>
            ))}
          </select>
        </>
      )}
    </div>
  )
}
