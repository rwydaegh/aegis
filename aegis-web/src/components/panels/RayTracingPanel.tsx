import { useSceneStore } from '@/stores/scene'

export default function RayTracingPanel() {
  const caps = useSceneStore(s => s.capabilities)
  const config = useSceneStore(s => s.viewerConfig)
  const rtEnabled = useSceneStore(s => s.rtEnabled)
  const rtSource = useSceneStore(s => s.rtSource)
  const rtMaxOrder = useSceneStore(s => s.rtMaxOrder)
  const scenePaths = useSceneStore(s => s.scenePaths)

  if (!caps?.has_differt) {
    return <p className="text-xs text-muted-foreground">DiffeRT not available</p>
  }

  const selectClass = "w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground"
  const labelClass = "text-xs text-muted-foreground block mt-2 mb-1"

  return (
    <div>
      <label className="flex items-center gap-2 text-xs text-foreground">
        <input type="checkbox" checked={rtEnabled}
          onChange={e => useSceneStore.setState({ rtEnabled: e.target.checked })} />
        Enable ray tracing
      </label>

      {rtEnabled && (
        <>
          <label className={labelClass}>RT scene source</label>
          <select className={selectClass} value={rtSource}
            onChange={e => useSceneStore.setState({ rtSource: e.target.value as 'voxel' | 'sionna' })}>
            {caps.has_voxels && <option value="voxel">Voxel environment</option>}
            {scenePaths.length > 0 && <option value="sionna">Sionna scene</option>}
          </select>

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
