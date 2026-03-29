import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'

type Backend = 'voxel' | 'differt' | 'sionna'

/** Whether a parameter is configurable, fixed to a value, or not available. */
type ParamCap =
  | { kind: 'configurable' }
  | { kind: 'configurable-when'; when: string; reason: string }
  | { kind: 'fixed'; value: string; reason: string }
  | { kind: 'na'; reason: string }

function capFor(backend: Backend, param: string, extra?: { method?: string; diffraction?: boolean }): ParamCap {
  const b = backend
  const method = extra?.method ?? 'exhaustive'
  const diffOn = extra?.diffraction ?? false

  switch (param) {
    case 'method':
      if (b === 'differt') return { kind: 'configurable' }
      if (b === 'sionna') return { kind: 'fixed', value: 'SBR', reason: 'fixed for Sionna RT' }
      return { kind: 'fixed', value: 'exhaustive', reason: 'fixed for Voxel' }

    case 'raysPerSource':
      if (b === 'differt') {
        if (method === 'exhaustive')
          return { kind: 'configurable-when', when: 'sbr', reason: 'exhaustive does not use rays' }
        return { kind: 'configurable' }
      }
      if (b === 'sionna') return { kind: 'configurable' }
      return { kind: 'na', reason: 'not available with Voxel' }

    case 'maxPathsPerSource':
      if (b === 'sionna') return { kind: 'configurable' }
      return { kind: 'na', reason: `not available with ${b === 'differt' ? 'DiffeRT' : 'Voxel'}` }

    case 'los':
      if (b === 'sionna') return { kind: 'configurable' }
      return { kind: 'fixed', value: 'on', reason: 'always on' }

    case 'specularReflection':
      if (b === 'sionna') return { kind: 'configurable' }
      return { kind: 'fixed', value: 'on', reason: 'always on' }

    case 'diffuseReflection':
      if (b === 'sionna') return { kind: 'configurable' }
      return { kind: 'na', reason: `not available with ${b === 'differt' ? 'DiffeRT' : 'Voxel'}` }

    case 'refraction':
      if (b === 'sionna') return { kind: 'configurable' }
      return { kind: 'na', reason: `not available with ${b === 'differt' ? 'DiffeRT' : 'Voxel'}` }

    case 'diffraction':
      if (b === 'sionna') return { kind: 'configurable' }
      return { kind: 'na', reason: `not available with ${b === 'differt' ? 'DiffeRT' : 'Voxel'}` }

    case 'edgeDiffraction':
      if (b === 'sionna') {
        if (!diffOn) return { kind: 'configurable-when', when: 'diffraction', reason: 'requires diffraction' }
        return { kind: 'configurable' }
      }
      return { kind: 'na', reason: `not available with ${b === 'differt' ? 'DiffeRT' : 'Voxel'}` }

    case 'diffractionLitRegion':
      if (b === 'sionna') {
        if (!diffOn) return { kind: 'configurable-when', when: 'diffraction', reason: 'requires diffraction' }
        return { kind: 'configurable' }
      }
      return { kind: 'na', reason: `not available with ${b === 'differt' ? 'DiffeRT' : 'Voxel'}` }

    case 'reflectionLoss':
      if (b === 'differt') return { kind: 'configurable' }
      if (b === 'voxel') return { kind: 'configurable' }
      return { kind: 'na', reason: 'physics-based in Sionna RT' }

    case 'syntheticArray':
      if (b === 'sionna') return { kind: 'configurable' }
      return { kind: 'na', reason: `not available with ${b === 'differt' ? 'DiffeRT' : 'Voxel'}` }

    case 'chunkSize':
      if (b === 'differt') {
        if (method === 'sbr')
          return { kind: 'configurable-when', when: 'exhaustive/hybrid', reason: 'SBR does not use chunks' }
        return { kind: 'configurable' }
      }
      return { kind: 'na', reason: `not available with ${b === 'sionna' ? 'Sionna' : 'Voxel'}` }

    case 'seed':
      if (b === 'sionna') return { kind: 'configurable' }
      return { kind: 'na', reason: `not available with ${b === 'differt' ? 'DiffeRT' : 'Voxel'}` }

    default:
      return { kind: 'configurable' }
  }
}

function isDisabled(cap: ParamCap): boolean {
  return cap.kind !== 'configurable'
}

function disabledText(cap: ParamCap): string | null {
  if (cap.kind === 'fixed') return `(${cap.reason})`
  if (cap.kind === 'na') return `(${cap.reason})`
  if (cap.kind === 'configurable-when') return `(${cap.reason})`
  return null
}

export default function RayTracingPanel() {
  const caps = useSceneStore(s => s.capabilities)
  const pathSource = useSceneStore(s => s.pathSource)
  const rtEnabled = pathSource === 'rt'
  const gpuWarm = useUIStore(s => s.gpuWarm)
  const scenes = useSceneStore(s => s.scenes)
  const loadedScenePath = useSceneStore(s => s.loadedScenePath)

  // RT config state
  const rtSource = useSceneStore(s => s.rtSource)
  const rtMaxOrder = useSceneStore(s => s.rtMaxOrder)
  const rc = useSceneStore(s => s.rtConfig)
  const setRtConfig = useSceneStore(s => s.setRtConfig)

  const hasDiffert = caps?.has_differt ?? false
  const hasSionna = caps?.has_sionna ?? false
  const hasVoxels = caps?.has_voxels ?? false
  const hasScenes = scenes.length > 0

  if (!hasDiffert && !hasSionna) {
    return <p className="text-xs text-muted-foreground">No ray tracing backend available</p>
  }

  const selectClass = "w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground"
  const labelClass = "text-xs text-muted-foreground block mt-2 mb-1"
  const sectionClass = "text-[10px] uppercase tracking-wider text-muted-foreground/50 mt-3 mb-1 border-b border-border/30 pb-1"
  const hintClass = "text-[10px] text-muted-foreground/60 ml-1"

  const needsScene = rtSource === 'differt' || rtSource === 'sionna'
  const sceneReady = needsScene ? !!loadedScenePath : true

  const backend: Backend = rtSource

  // Helper to get capability for a param
  const cap = (param: string) => capFor(backend, param, { method: rc.method, diffraction: rc.diffraction })

  // Wrapper for disabled rows
  function Row({ param, children }: { param: string; children: React.ReactNode }) {
    const c = cap(param)
    const disabled = isDisabled(c)
    return (
      <div className={disabled ? 'opacity-40 pointer-events-none' : ''}>
        {children}
      </div>
    )
  }

  // Inline hint for disabled params
  function Hint({ param }: { param: string }) {
    const c = cap(param)
    const text = disabledText(c)
    if (!text) return null
    return <span className={hintClass}>{text}</span>
  }

  // Checkbox row component
  function CheckboxRow({
    param,
    label,
    checked,
    onChange,
    indent,
  }: {
    param: string
    label: string
    checked: boolean
    onChange: (v: boolean) => void
    indent?: boolean
  }) {
    const c = cap(param)
    const disabled = isDisabled(c)
    // For fixed "on" values, show checked even if store value differs
    const displayChecked = c.kind === 'fixed' && c.value === 'on' ? true : checked

    return (
      <div className={`${disabled ? 'opacity-40 pointer-events-none' : ''} ${indent ? 'ml-5' : ''}`}>
        <label className="flex items-center gap-2 text-xs text-foreground cursor-pointer select-none">
          <input
            type="checkbox"
            className="rounded border-border accent-primary h-3.5 w-3.5"
            checked={displayChecked}
            onChange={e => onChange(e.target.checked)}
            disabled={disabled}
          />
          <span>{label}</span>
          <Hint param={param} />
        </label>
      </div>
    )
  }

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
          {/* GPU status indicator */}
          {gpuWarm !== null && (
            <div className={`flex items-center gap-2 mt-2 px-2 py-1.5 rounded-md text-xs
              ${gpuWarm
                ? 'bg-green-500/10 text-green-400'
                : 'bg-amber-500/10 text-amber-400'
              }`}
            >
              <span className={`inline-block w-1.5 h-1.5 rounded-full
                ${gpuWarm
                  ? 'bg-green-400'
                  : 'bg-amber-400 gpu-dot-pulse'
                }`}
              />
              <span>
                {gpuWarm
                  ? 'GPU ready'
                  : 'GPU asleep'
                }
              </span>
              {!gpuWarm && (
                <span className="text-[10px] text-amber-400/60 ml-auto">~30s first run</span>
              )}
            </div>
          )}

          {/* Backend selector */}
          <label className={labelClass}>RT backend</label>
          <select
            className={selectClass}
            value={rtSource}
            onChange={e => useSceneStore.setState({ rtSource: e.target.value as Backend })}
          >
            {hasVoxels && <option value="voxel">Voxel environment</option>}
            {hasDiffert && hasScenes && <option value="differt">Scene (DiffeRT)</option>}
            {hasSionna && hasScenes && <option value="sionna">Scene (Sionna RT)</option>}
          </select>

          {needsScene && !sceneReady && (
            <p className="text-xs text-amber-400 mt-1">Load a scene first (Scene panel above)</p>
          )}

          {/* ── Path solving ── */}
          <div className={sectionClass}>Path solving</div>

          <label className={labelClass}>Max depth</label>
          <input
            type="number"
            className={selectClass}
            value={rtMaxOrder}
            onChange={e => {
              const v = Number(e.target.value)
              if (v >= 0 && v <= 10) useSceneStore.setState({ rtMaxOrder: v })
            }}
            min={0}
            max={10}
            step={1}
          />

          <Row param="method">
            <label className={labelClass}>
              Method
              <Hint param="method" />
            </label>
            <select
              className={selectClass}
              value={cap('method').kind === 'fixed' ? (cap('method') as { value: string }).value.toLowerCase() : rc.method}
              onChange={e => setRtConfig({ method: e.target.value as 'exhaustive' | 'sbr' | 'hybrid' })}
              disabled={isDisabled(cap('method'))}
            >
              {cap('method').kind === 'fixed' ? (
                <option value={(cap('method') as { value: string }).value.toLowerCase()}>
                  {(cap('method') as { value: string }).value}
                </option>
              ) : (
                <>
                  <option value="exhaustive">Exhaustive</option>
                  <option value="sbr">SBR (Shooting and Bouncing Rays)</option>
                  <option value="hybrid">Hybrid</option>
                </>
              )}
            </select>
          </Row>

          <Row param="raysPerSource">
            <label className={labelClass}>
              Rays per source
              <Hint param="raysPerSource" />
            </label>
            <input
              type="number"
              className={selectClass}
              value={rc.raysPerSource}
              onChange={e => {
                const v = Number(e.target.value)
                if (v > 0) setRtConfig({ raysPerSource: v })
              }}
              min={1}
              step={100000}
              disabled={isDisabled(cap('raysPerSource'))}
            />
          </Row>

          <Row param="maxPathsPerSource">
            <label className={labelClass}>
              Max paths per source
              <Hint param="maxPathsPerSource" />
            </label>
            <input
              type="number"
              className={selectClass}
              value={rc.maxPathsPerSource}
              onChange={e => {
                const v = Number(e.target.value)
                if (v > 0) setRtConfig({ maxPathsPerSource: v })
              }}
              min={1}
              step={100000}
              disabled={isDisabled(cap('maxPathsPerSource'))}
            />
          </Row>

          <Row param="chunkSize">
            <label className={labelClass}>
              Chunk size
              <Hint param="chunkSize" />
            </label>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1 text-xs text-foreground cursor-pointer select-none shrink-0">
                <input
                  type="checkbox"
                  className="rounded border-border accent-primary h-3.5 w-3.5"
                  checked={rc.chunkSize !== null}
                  onChange={e => setRtConfig({ chunkSize: e.target.checked ? 100_000 : null })}
                  disabled={isDisabled(cap('chunkSize'))}
                />
                On
              </label>
              <input
                type="number"
                className={selectClass}
                value={rc.chunkSize ?? ''}
                placeholder="disabled"
                onChange={e => {
                  const v = Number(e.target.value)
                  if (v > 0) setRtConfig({ chunkSize: v })
                }}
                min={1}
                step={10000}
                disabled={isDisabled(cap('chunkSize')) || rc.chunkSize === null}
              />
            </div>
          </Row>

          {/* ── Interactions ── */}
          <div className={sectionClass}>Interactions</div>

          <div className="flex flex-col gap-1.5 mt-1">
            <CheckboxRow
              param="los"
              label="LOS"
              checked={rc.los}
              onChange={v => setRtConfig({ los: v })}
            />
            <CheckboxRow
              param="specularReflection"
              label="Specular reflection"
              checked={rc.specularReflection}
              onChange={v => setRtConfig({ specularReflection: v })}
            />
            <CheckboxRow
              param="diffuseReflection"
              label="Diffuse reflection"
              checked={rc.diffuseReflection}
              onChange={v => setRtConfig({ diffuseReflection: v })}
            />
            <CheckboxRow
              param="refraction"
              label="Refraction"
              checked={rc.refraction}
              onChange={v => setRtConfig({ refraction: v })}
            />
            <CheckboxRow
              param="diffraction"
              label="Diffraction"
              checked={rc.diffraction}
              onChange={v => setRtConfig({ diffraction: v })}
            />
            <CheckboxRow
              param="edgeDiffraction"
              label="Edge diffraction"
              checked={rc.edgeDiffraction}
              onChange={v => setRtConfig({ edgeDiffraction: v })}
              indent
            />
            <CheckboxRow
              param="diffractionLitRegion"
              label="Diffraction lit region"
              checked={rc.diffractionLitRegion}
              onChange={v => setRtConfig({ diffractionLitRegion: v })}
              indent
            />
          </div>

          {/* ── Solver-specific ── */}
          <div className={sectionClass}>Solver-specific</div>

          <Row param="reflectionLoss">
            <label className={labelClass}>
              Reflection loss / bounce
              <Hint param="reflectionLoss" />
            </label>
            <div className="flex items-center gap-2">
              <input
                type="range"
                className="flex-1 accent-primary h-1.5"
                min={0}
                max={1}
                step={0.05}
                value={rc.reflectionLoss}
                onChange={e => setRtConfig({ reflectionLoss: Number(e.target.value) })}
                disabled={isDisabled(cap('reflectionLoss'))}
              />
              <span className="text-xs text-muted-foreground tabular-nums w-8 text-right">
                {rc.reflectionLoss.toFixed(2)}
              </span>
            </div>
          </Row>

          <div className="mt-1.5">
            <CheckboxRow
              param="syntheticArray"
              label="Synthetic array"
              checked={rc.syntheticArray}
              onChange={v => setRtConfig({ syntheticArray: v })}
            />
          </div>

          <Row param="seed">
            <label className={labelClass}>
              Seed
              <Hint param="seed" />
            </label>
            <input
              type="number"
              className={selectClass}
              value={rc.seed}
              onChange={e => {
                const v = Number(e.target.value)
                if (Number.isFinite(v)) setRtConfig({ seed: v })
              }}
              min={0}
              step={1}
              disabled={isDisabled(cap('seed'))}
            />
          </Row>
        </>
      )}
    </div>
  )
}
