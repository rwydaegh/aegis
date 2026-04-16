import { useAntennaStore } from '@/stores/antenna'

export function AddAntennaButton() {
  const addAntenna = useAntennaStore(s => s.addAntenna)

  return (
    <button
      className="w-full text-[11px] py-1.5 rounded border border-dashed border-border text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
      onClick={() => addAntenna([5, 0, 0])}
    >
      + Add antenna
    </button>
  )
}
