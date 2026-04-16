import { useAntennaStore, type AntennaConfig } from '@/stores/antenna'
import { sectionClass } from './constants'

export function PositionSection({ selected }: { selected: AntennaConfig }) {
  const updateAntenna = useAntennaStore(s => s.updateAntenna)

  return (
    <div>
      <p className={sectionClass}>Position</p>
      <div className="flex gap-1">
        {(['X', 'Y', 'Z'] as const).map((axis, i) => (
          <label key={axis} className="flex items-center gap-0.5 flex-1">
            <span className="text-[9px] text-muted-foreground">{axis}</span>
            <input
              type="number"
              step={0.5}
              value={selected.position[i]}
              onChange={e => {
                const v = parseFloat(e.target.value)
                if (isNaN(v)) return
                const pos: [number, number, number] = [...selected.position]
                pos[i] = i === 1 ? Math.max(0, v) : v
                updateAntenna(selected.id, { position: pos })
              }}
              className="w-full bg-muted/50 border border-border rounded px-1 py-0.5 text-[10px] text-foreground font-mono"
            />
          </label>
        ))}
      </div>
      <p className="text-[9px] text-muted-foreground/60 mt-0.5">Click scene to place</p>
    </div>
  )
}
