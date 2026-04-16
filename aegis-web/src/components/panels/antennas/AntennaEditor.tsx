import { useAntennaStore } from '@/stores/antenna'
import { PowerSection } from './PowerSection'
import { ArraySizeSection } from './ArraySizeSection'
import { ElementSpacingSection } from './ElementSpacingSection'
import { ElementPatternSection } from './ElementPatternSection'
import { PositionSection } from './PositionSection'
import { HeightSection } from './HeightSection'
import { DirectionSection } from './DirectionSection'
import { FocusPointSection } from './FocusPointSection'

export function AntennaEditor() {
  const antennas = useAntennaStore(s => s.antennas)
  const selectedId = useAntennaStore(s => s.selectedId)
  const selected = selectedId ? antennas.get(selectedId) ?? null : null

  if (!selected) return null

  return (
    <div className="space-y-3 pt-2 border-t border-border">
      <PowerSection selected={selected} />
      <ArraySizeSection selected={selected} />
      <ElementSpacingSection selected={selected} />
      <ElementPatternSection selected={selected} />
      <PositionSection selected={selected} />
      <HeightSection selected={selected} />
      <DirectionSection selected={selected} />
      {selected.arrayConfig.element_pattern === 'patch' && (
        <FocusPointSection selected={selected} />
      )}
    </div>
  )
}
