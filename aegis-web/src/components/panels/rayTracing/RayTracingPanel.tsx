import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import type { Backend } from './capabilities'
import PathSolvingSection from './PathSolvingSection'
import InteractionsSection from './InteractionsSection'
import SolverSection from './SolverSection'
import { labelClass, selectClass } from './styles'

function GpuStatus({ gpuWarm }: { gpuWarm: boolean }) {
  return (
    <div
      className={`flex items-center gap-2 mt-2 px-2 py-1.5 rounded-md text-xs
        ${gpuWarm ? 'bg-green-500/10 text-green-400' : 'bg-amber-500/10 text-amber-400'}`}
    >
      <span
        className={`inline-block w-1.5 h-1.5 rounded-full
          ${gpuWarm ? 'bg-green-400' : 'bg-amber-400 gpu-dot-pulse'}`}
      />
      <span>{gpuWarm ? 'GPU ready' : 'GPU asleep'}</span>
      {!gpuWarm && (
        <span className="text-[10px] text-amber-400/60 ml-auto">~30s first run</span>
      )}
    </div>
  )
}

export default function RayTracingPanel() {
  const caps = useSceneStore(s => s.capabilities)
  const pathSource = useSceneStore(s => s.pathSource)
  const rtEnabled = pathSource === 'rt'
  const gpuWarm = useUIStore(s => s.gpuWarm)

  const rtSource = useSceneStore(s => s.rtSource)

  const hasDiffert = caps?.has_differt ?? false
  const hasSionna = caps?.has_sionna ?? false

  if (!hasDiffert && !hasSionna) {
    return <p className="text-xs text-muted-foreground">No ray tracing backend available</p>
  }

  const backend: Backend = rtSource

  return (
    <div>
      {/* Enable toggle */}
      <label className="flex items-center gap-2 text-xs text-foreground cursor-pointer select-none">
        <input
          type="checkbox"
          className="rounded border-border accent-primary h-3.5 w-3.5"
          checked={rtEnabled}
          onChange={e => useSceneStore.getState().setPathSource(e.target.checked ? 'rt' : 'synthetic')}
        />
        Enable ray tracing
      </label>

      {rtEnabled && (
        <>
          {gpuWarm !== null && <GpuStatus gpuWarm={gpuWarm} />}

          <label className={labelClass}>RT backend</label>
          <select
            className={selectClass}
            value={rtSource}
            onChange={e => useSceneStore.setState({ rtSource: e.target.value as Backend })}
          >
            {hasSionna && <option value="sionna">Sionna RT</option>}
            {hasDiffert && <option value="differt">DiffeRT</option>}
          </select>

          <PathSolvingSection backend={backend} />
          <InteractionsSection backend={backend} />
          <SolverSection backend={backend} />
        </>
      )}
    </div>
  )
}
