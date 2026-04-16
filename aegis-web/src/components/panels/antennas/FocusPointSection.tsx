import { useAntennaStore, type AntennaConfig } from '@/stores/antenna'
import { sectionClass } from './constants'

export function FocusPointSection({ selected }: { selected: AntennaConfig }) {
  return (
    <div>
      <p className={sectionClass}>Focus point</p>
      <div className="flex gap-1">
        {(['X', 'Y', 'Z'] as const).map((axis, i) => (
          <label key={axis} className="flex items-center gap-0.5 flex-1">
            <span className="text-[9px] text-muted-foreground">{axis}</span>
            <input
              type="number"
              step={0.5}
              value={selected.focusPoint?.[i] ?? 0}
              onChange={e => {
                const v = parseFloat(e.target.value)
                if (isNaN(v)) return
                const fp: [number, number, number] = selected.focusPoint
                  ? [...selected.focusPoint] as [number, number, number]
                  : [0, 0, 0]
                fp[i] = v
                useAntennaStore.getState().setFocusPoint(selected.id, fp)
              }}
              className="w-full bg-muted/50 border border-border rounded px-1 py-0.5 text-[10px] text-foreground font-mono"
            />
          </label>
        ))}
      </div>
      <p className="text-[9px] text-muted-foreground/60 mt-0.5">Target for broadside direction</p>
    </div>
  )
}
