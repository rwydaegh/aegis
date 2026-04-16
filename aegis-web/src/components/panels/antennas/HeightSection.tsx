import { useAntennaStore, type AntennaConfig } from '@/stores/antenna'
import { NumInput } from './NumInput'
import { inputClass, sectionClass } from './constants'

export function HeightSection({ selected }: { selected: AntennaConfig }) {
  return (
    <div>
      <p className={sectionClass}>Height</p>
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <NumInput
            className={inputClass}
            value={selected.height}
            min={0.5}
            max={50}
            step={0.5}
            onChange={v => {
              useAntennaStore.getState().setHeight(selected.id, v)
            }}
          />
        </div>
        <span className="text-[10px] text-muted-foreground">m</span>
      </div>
    </div>
  )
}
