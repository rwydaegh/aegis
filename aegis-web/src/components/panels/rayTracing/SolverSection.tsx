import { useSceneStore } from '@/stores/scene'
import type { Backend } from './capabilities'
import { capFor, isDisabled } from './capabilities'
import { Row, Hint, CheckboxRow } from './Rows'
import { labelClass, sectionClass, selectClass } from './styles'

export default function SolverSection({ backend }: { backend: Backend }) {
  const rc = useSceneStore(s => s.rtConfig)
  const setRtConfig = useSceneStore(s => s.setRtConfig)

  const cap = (param: string) => capFor(backend, param, { method: rc.method, diffraction: rc.diffraction })

  const reflectionCap = cap('reflectionLoss')
  const seedCap = cap('seed')

  return (
    <>
      <div className={sectionClass}>Solver-specific</div>

      <Row cap={reflectionCap}>
        <label className={labelClass}>
          Reflection loss / bounce
          <Hint cap={reflectionCap} />
        </label>
        <div className="flex items-center gap-2">
          <input
            type="range"
            className="flex-1 accent-primary h-1.5"
            min={0}
            max={1}
            step={0.01}
            value={rc.reflectionLoss}
            onChange={e => setRtConfig({ reflectionLoss: Number(e.target.value) })}
            disabled={isDisabled(reflectionCap)}
          />
          <span className="text-xs text-muted-foreground tabular-nums w-8 text-right">
            {rc.reflectionLoss.toFixed(2)}
          </span>
        </div>
      </Row>

      <div className="mt-1.5">
        <CheckboxRow
          cap={cap('syntheticArray')}
          label="Synthetic array"
          checked={rc.syntheticArray}
          onChange={v => setRtConfig({ syntheticArray: v })}
        />
      </div>

      <Row cap={seedCap}>
        <label className={labelClass}>
          Seed
          <Hint cap={seedCap} />
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
          disabled={isDisabled(seedCap)}
        />
      </Row>
    </>
  )
}
