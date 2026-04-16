import { useSceneStore } from '@/stores/scene'
import type { Backend } from './capabilities'
import { capFor, isDisabled } from './capabilities'
import { Row, Hint } from './Rows'
import { labelClass, sectionClass, selectClass } from './styles'

export default function PathSolvingSection({ backend }: { backend: Backend }) {
  const rtMaxOrder = useSceneStore(s => s.rtMaxOrder)
  const rc = useSceneStore(s => s.rtConfig)
  const setRtConfig = useSceneStore(s => s.setRtConfig)

  const cap = (param: string) => capFor(backend, param, { method: rc.method, diffraction: rc.diffraction })

  const methodCap = cap('method')
  const raysCap = cap('raysPerSource')
  const maxPathsCap = cap('maxPathsPerSource')
  const chunkCap = cap('chunkSize')

  const methodFixedValue =
    methodCap.kind === 'fixed' ? methodCap.value.toLowerCase() : null

  return (
    <>
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

      <Row cap={methodCap}>
        <label className={labelClass}>
          Method
          <Hint cap={methodCap} />
        </label>
        <select
          className={selectClass}
          value={methodFixedValue ?? rc.method}
          onChange={e => setRtConfig({ method: e.target.value as 'exhaustive' | 'sbr' | 'hybrid' })}
          disabled={isDisabled(methodCap)}
        >
          {methodCap.kind === 'fixed' ? (
            <option value={methodCap.value.toLowerCase()}>{methodCap.value}</option>
          ) : (
            <>
              <option value="exhaustive">Exhaustive</option>
              <option value="sbr">SBR (Shooting and Bouncing Rays)</option>
              <option value="hybrid">Hybrid</option>
            </>
          )}
        </select>
      </Row>

      <Row cap={raysCap}>
        <label className={labelClass}>
          Rays per source
          <Hint cap={raysCap} />
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
          disabled={isDisabled(raysCap)}
        />
      </Row>

      <Row cap={maxPathsCap}>
        <label className={labelClass}>
          Max paths per source
          <Hint cap={maxPathsCap} />
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
          disabled={isDisabled(maxPathsCap)}
        />
      </Row>

      <Row cap={chunkCap}>
        <label className={labelClass}>
          Chunk size
          <Hint cap={chunkCap} />
        </label>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1 text-xs text-foreground cursor-pointer select-none shrink-0">
            <input
              type="checkbox"
              className="rounded border-border accent-primary h-3.5 w-3.5"
              checked={rc.chunkSize !== null}
              onChange={e => setRtConfig({ chunkSize: e.target.checked ? 100_000 : null })}
              disabled={isDisabled(chunkCap)}
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
            disabled={isDisabled(chunkCap) || rc.chunkSize === null}
          />
        </div>
      </Row>
    </>
  )
}
