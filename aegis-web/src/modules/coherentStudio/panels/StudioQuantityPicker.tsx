import { useEffect } from 'react'
import type { StudioBodyMapStatistic, StudioFieldQuantity } from '../api'
import { useStudioStore } from '../store'
import { bodyMapHasPack, ensembleHasPack, FIELD_QUANTITY_OPTIONS, packsOf } from './controls'
import { FieldLabel, LabeledSelect, type Option } from './widgets'

const QTY_LABELS: Record<string, string> = {
  floor: 'Floor (lower bound)',
  mrt: 'MRT (focused)',
  worstcase: 'Worst case',
  amp: 'Amplified',
}

const STAT_LABELS: Record<string, string> = {
  single: 'Single realisation',
  mean: 'Ensemble mean',
  p95: 'Ensemble p95',
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
  const bodyMapStatistic = useStudioStore((s) => s.bodyMapStatistic)
  const setBodyMapStatistic = useStudioStore((s) => s.setBodyMapStatistic)

  const manifest = useStudioStore((s) => s.manifest)
  const condition = useStudioStore((s) => s.condition)
  const arrayN = useStudioStore((s) => s.arrayN)
  const frequencyGhz = useStudioStore((s) => s.frequencyGhz)

  const packs = packsOf(manifest)
  const bodyQuantities = manifest?.body_map_quantities ?? []
  const statistics = manifest?.body_map_statistics ?? ['single']

  const bodyOptions: Option<string>[] = bodyQuantities.map((q) => {
    const available = bodyMapHasPack(packs, condition, arrayN, q, frequencyGhz)
    return {
      value: q,
      label: QTY_LABELS[q] ?? q,
      disabled: !available,
      hint: 'no pack',
    }
  })

  const statOptions: Option<StudioBodyMapStatistic>[] = statistics.map((st) => {
    const available = ensembleHasPack(packs, st, condition, arrayN, bodyMapQuantity, frequencyGhz)
    return {
      value: st as StudioBodyMapStatistic,
      label: STAT_LABELS[st] ?? st,
      disabled: !available,
      hint: 'no ensemble pack',
    }
  })

  // Keep the realisation valid as the scenario changes: an ensemble statistic
  // selected before switching to NLOS (or a frequency with no ensemble pack)
  // would otherwise 409 and grey the body, so fall back to the single
  // realisation, which always ships.
  const statAvailable = ensembleHasPack(packs, bodyMapStatistic, condition, arrayN, bodyMapQuantity, frequencyGhz)
  useEffect(() => {
    if (bodyMapStatistic !== 'single' && !statAvailable) setBodyMapStatistic('single')
  }, [bodyMapStatistic, statAvailable, setBodyMapStatistic])

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

      <FieldLabel title="Single seed, or the mean / 95th percentile of the body map over the LOS seed ensemble.">
        Body-map realisation
      </FieldLabel>
      <LabeledSelect<StudioBodyMapStatistic>
        value={bodyMapStatistic}
        options={statOptions}
        onChange={setBodyMapStatistic}
      />
    </div>
  )
}
