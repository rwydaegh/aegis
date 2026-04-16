import { useAntennaStore, type AntennaArrayConfig, type AntennaConfig } from '@/stores/antenna'
import { NumInput } from './NumInput'
import { inputClass, labelClass, sectionClass } from './constants'

export function ArraySizeSection({ selected }: { selected: AntennaConfig }) {
  const updateAntenna = useAntennaStore(s => s.updateAntenna)

  const updateArrayConfig = (partial: Partial<AntennaArrayConfig>) => {
    updateAntenna(selected.id, { arrayConfig: { ...selected.arrayConfig, ...partial } })
  }

  return (
    <div>
      <p className={sectionClass}>Array size</p>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className={labelClass}>N_h</label>
          <NumInput
            className={inputClass}
            value={selected.arrayConfig.n_h}
            min={1} max={16} step={1} integer
            onChange={v => updateArrayConfig({ n_h: v })}
          />
        </div>
        <div>
          <label className={labelClass}>N_v</label>
          <NumInput
            className={inputClass}
            value={selected.arrayConfig.n_v}
            min={1} max={16} step={1} integer
            onChange={v => updateArrayConfig({ n_v: v })}
          />
        </div>
      </div>
    </div>
  )
}
