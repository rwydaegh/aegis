import { useAntennaStore } from '@/stores/antenna'

export function AntennaList() {
  const antennas = useAntennaStore(s => s.antennas)
  const selectedId = useAntennaStore(s => s.selectedId)
  const removeAntenna = useAntennaStore(s => s.removeAntenna)
  const selectAntenna = useAntennaStore(s => s.selectAntenna)
  const setEnabled = useAntennaStore(s => s.setEnabled)

  const antennaList = [...antennas.values()]

  return (
    <div className="space-y-1">
      {antennaList.length === 0 && (
        <p className="text-[11px] text-muted-foreground">No antennas. Click below to add one.</p>
      )}
      {antennaList.map(ant => {
        const isSelected = ant.id === selectedId
        const arraySize = ant.arrayConfig.n_h * ant.arrayConfig.n_v
        return (
          <div
            key={ant.id}
            className={`flex items-center gap-1.5 rounded px-1.5 py-1 cursor-pointer transition-colors ${
              isSelected
                ? 'bg-primary/15 border border-primary/40'
                : 'bg-muted/50 border border-transparent hover:bg-muted'
            }`}
            onClick={() => selectAntenna(ant.id)}
          >
            {/* Enable checkbox */}
            <input
              type="checkbox"
              className="rounded border-border accent-primary h-3 w-3 shrink-0"
              checked={ant.enabled}
              onChange={e => {
                e.stopPropagation()
                setEnabled(ant.id, e.target.checked)
              }}
              onClick={e => e.stopPropagation()}
            />

            {/* Name */}
            <span className="text-[11px] text-foreground flex-1 truncate">{ant.name}</span>

            {/* Array size badge */}
            {arraySize > 1 && (
              <span className="text-[9px] text-muted-foreground bg-muted rounded px-1 py-0.5 shrink-0">
                {ant.arrayConfig.n_h}x{ant.arrayConfig.n_v}
              </span>
            )}

            {/* Position */}
            <span className="text-[9px] text-muted-foreground/70 font-mono shrink-0">
              ({ant.position[0].toFixed(1)}, {ant.position[1].toFixed(1)}, {ant.position[2].toFixed(1)})
            </span>

            {/* Delete button */}
            <button
              className="shrink-0 w-4 h-4 flex items-center justify-center rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
              title="Remove antenna"
              onClick={e => {
                e.stopPropagation()
                removeAntenna(ant.id)
              }}
            >
              <svg
                width="10"
                height="10"
                viewBox="0 0 10 10"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <path d="M2 2l6 6M8 2l-6 6" />
              </svg>
            </button>
          </div>
        )
      })}
    </div>
  )
}
