import type { StudioFieldQuantity } from '../api'
import { useStudioStore } from '../store'
import { bodyMapHasPack, FIELD_QUANTITY_OPTIONS, packsOf } from './controls'
import { FieldLabel, LabeledSelect, type Option } from './widgets'

const QTY_LABELS: Record<string, string> = {
  floor: 'Floor (lower bound)',
  mrt: 'MRT (focused)',
  worstcase: 'Worst case',
  amp: 'Amplified',
}

/**
 * The two quantity selectors (field slice quantity + body-map quantity), factored
 * out of StudioPanel so the picker logic stays isolated and testable. Body-map
 * quantities whose precomputed pack is absent for the current scenario are
 * disabled (with the missing-pack note surfaced inline).
 */
export default function StudioQuantityPicker() {
  const fieldQuantity = useStudioStore((s) => s.fieldQuantity)
  const setFieldQuantity = useStudioStore((s) => s.setFieldQuantity)
  const bodyMapQuantity = useStudioStore((s) => s.bodyMapQuantity)
  const setBodyMapQuantity = useStudioStore((s) => s.setBodyMapQuantity)

  const manifest = useStudioStore((s) => s.manifest)
  const condition = useStudioStore((s) => s.condition)
  const arrayN = useStudioStore((s) => s.arrayN)
  const frequencyGhz = useStudioStore((s) => s.frequencyGhz)

  const packs = packsOf(manifest)
  const bodyQuantities = manifest?.body_map_quantities ?? []

  const bodyOptions: Option<string>[] = bodyQuantities.map((q) => {
    const available = bodyMapHasPack(packs, condition, arrayN, q, frequencyGhz)
    return {
      value: q,
      label: QTY_LABELS[q] ?? q,
      disabled: !available,
      hint: 'no pack',
    }
  })

  return (
    <div>
      <FieldLabel title="The scalar painted onto the field slice plane.">Slice quantity</FieldLabel>
      <LabeledSelect<StudioFieldQuantity>
        value={fieldQuantity}
        options={FIELD_QUANTITY_OPTIONS}
        onChange={setFieldQuantity}
      />

      <FieldLabel title="The per-triangle quantity painted onto the phantom body.">
        Body-map quantity
      </FieldLabel>
      <LabeledSelect<string>
        value={bodyMapQuantity}
        options={bodyOptions}
        onChange={setBodyMapQuantity}
      />
    </div>
  )
}
