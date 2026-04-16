import { useAntennaStore, type AntennaArrayConfig, type AntennaConfig } from '@/stores/antenna'
import { PATTERN_OPTIONS, sectionClass } from './constants'

export function ElementPatternSection({ selected }: { selected: AntennaConfig }) {
  const updateAntenna = useAntennaStore(s => s.updateAntenna)

  const updateArrayConfig = (partial: Partial<AntennaArrayConfig>) => {
    updateAntenna(selected.id, { arrayConfig: { ...selected.arrayConfig, ...partial } })
  }

  return (
    <div>
      <p className={sectionClass}>Element pattern</p>
      <div className="flex gap-1">
        {PATTERN_OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => updateArrayConfig({ element_pattern: opt.value })}
            className={`flex-1 text-[10px] py-1 px-1.5 rounded border transition-colors ${
              selected.arrayConfig.element_pattern === opt.value
                ? 'bg-primary/15 border border-primary/40'
                : 'bg-muted/50 border border-transparent hover:bg-muted'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  )
}
