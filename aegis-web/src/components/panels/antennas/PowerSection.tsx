import { useAntennaStore, type AntennaConfig } from '@/stores/antenna'
import Tex from '@/components/ui/Tex'
import { inputClass, labelClass, sectionClass } from './constants'

export function PowerSection({ selected }: { selected: AntennaConfig }) {
  const updateAntenna = useAntennaStore(s => s.updateAntenna)

  const updateSelected = (partial: Partial<AntennaConfig>) => {
    updateAntenna(selected.id, partial)
  }

  return (
    <div>
      <p className={sectionClass}>Power</p>
      <label className={labelClass}>
        <Tex math={'P_\\text{TX}'} />
      </label>
      <div className="flex gap-2 items-center">
        <div className="flex-1">
          <input
            type="number"
            className={inputClass}
            value={selected.powerDbm}
            onChange={e => {
              const v = Number(e.target.value)
              if (Number.isFinite(v)) updateSelected({ powerDbm: v })
            }}
            step={1}
          />
          <span className="text-[10px] text-muted-foreground mt-0.5 block">dBm</span>
        </div>
        <span className="text-muted-foreground text-xs pb-3">=</span>
        <div className="flex-1">
          <input
            type="number"
            className={inputClass}
            value={Number((10 ** ((selected.powerDbm - 30) / 10)).toPrecision(4))}
            onChange={e => {
              const w = Number(e.target.value)
              if (w > 0)
                updateSelected({
                  powerDbm: Math.round((10 * Math.log10(w) + 30) * 100) / 100,
                })
            }}
            step={0.1}
            min={0}
          />
          <span className="text-[10px] text-muted-foreground mt-0.5 block">W</span>
        </div>
      </div>
    </div>
  )
}
