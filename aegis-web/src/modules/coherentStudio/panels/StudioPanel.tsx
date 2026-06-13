import type { StudioPlaneOrientation } from '../api'
import { useStudioStore, type StudioScaleMode } from '../store'
import {
  beamOptions,
  conditionHasRayPack,
  EXTENT_OPTIONS_M,
  extentLabel,
  ORIENTATION_OPTIONS,
  packsOf,
  RESOLUTION_OPTIONS,
} from './controls'
import StudioQuantityPicker from './StudioQuantityPicker'
import { DiscreteSlider, FieldLabel, Group, LabeledSelect, Segmented, type Option } from './widgets'

const COLORMAP_OPTIONS: Option<string>[] = [
  { value: 'viridis', label: 'Viridis' },
  { value: 'jet', label: 'Jet' },
]

const SCALE_OPTIONS: Option<StudioScaleMode>[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'fixed', label: 'Fixed' },
  { value: 'log', label: 'Log' },
]

const CONDITION_LABELS: Record<string, string> = { los: 'LOS', nlos: 'NLOS' }

const FREQ_TOOLTIP =
  'Sweeps the dosimetry frequency over the fixed 28 GHz multipath geometry ' +
  '(specular geometry is frequency independent); not a per-frequency re-trace.'

/**
 * The studio control surface: a grouped panel wiring the Phase-1 subset of the
 * design space to the store. Controls whose precomputed packs are absent (NLOS
 * ray packs, body-map quantities without a pack) grey out; Phase-2 beams are
 * shown disabled with a hint.
 */
export default function StudioPanel() {
  const manifest = useStudioStore((s) => s.manifest)

  const condition = useStudioStore((s) => s.condition)
  const setCondition = useStudioStore((s) => s.setCondition)
  const seed = useStudioStore((s) => s.seed)
  const setSeed = useStudioStore((s) => s.setSeed)
  const arrayN = useStudioStore((s) => s.arrayN)

  const beam = useStudioStore((s) => s.beam)
  const setBeam = useStudioStore((s) => s.setBeam)

  const frequencyGhz = useStudioStore((s) => s.frequencyGhz)
  const setFrequencyGhz = useStudioStore((s) => s.setFrequencyGhz)

  const plane = useStudioStore((s) => s.plane)
  const setPlane = useStudioStore((s) => s.setPlane)

  const colormap = useStudioStore((s) => s.colormap)
  const setColormap = useStudioStore((s) => s.setColormap)
  const scaleMode = useStudioStore((s) => s.scaleMode)
  const setScaleMode = useStudioStore((s) => s.setScaleMode)

  const packs = packsOf(manifest)

  const conditionOptions: Option<string>[] = (manifest?.conditions ?? ['los']).map((c) => ({
    value: c,
    label: CONDITION_LABELS[c] ?? c.toUpperCase(),
    disabled: !conditionHasRayPack(packs, c, arrayN),
    hint: 'no pack',
  }))

  const seedOptions: Option<number>[] = (manifest?.seeds ?? [seed]).map((s) => ({
    value: s,
    label: `Seed ${s}`,
  }))

  const beams = beamOptions(manifest).map((b) => ({
    value: b.value,
    label: b.label,
    disabled: b.phase2,
    hint: 'Phase 2',
  }))

  const frequencies = manifest?.frequencies ?? [frequencyGhz]

  return (
    <div>
      <Group title="Channel">
        <FieldLabel title="Line-of-sight or non-line-of-sight multipath condition.">
          Condition
        </FieldLabel>
        <Segmented<string> value={condition} options={conditionOptions} onChange={setCondition} />

        <FieldLabel title="Realisation / ensemble member of the small-scale fading.">Seed</FieldLabel>
        <LabeledSelect<number>
          value={seed}
          options={seedOptions}
          onChange={setSeed}
          parse={(raw) => Number(raw)}
        />
      </Group>

      <Group title="Beam" hint="Decohered / decoy / ECBF precoders arrive in Phase 2.">
        <LabeledSelect<string> value={beam} options={beams} onChange={setBeam} />
      </Group>

      <Group title="Frequency">
        <FieldLabel title={FREQ_TOOLTIP}>Dosimetry frequency (GHz)</FieldLabel>
        <DiscreteSlider<number>
          value={frequencyGhz}
          options={frequencies}
          labelOf={(f) => `${f} GHz`}
          onChange={setFrequencyGhz}
        />
      </Group>

      <Group title="Slice">
        <FieldLabel>Orientation</FieldLabel>
        <Segmented<StudioPlaneOrientation>
          value={plane.orientation}
          options={ORIENTATION_OPTIONS}
          onChange={(orientation) => setPlane({ orientation })}
        />

        <FieldLabel>Extent</FieldLabel>
        <DiscreteSlider<number>
          value={plane.extentM}
          options={EXTENT_OPTIONS_M}
          labelOf={extentLabel}
          onChange={(extentM) => setPlane({ extentM })}
        />

        <FieldLabel>Resolution</FieldLabel>
        <Segmented<number>
          value={plane.res}
          options={RESOLUTION_OPTIONS}
          onChange={(res) => setPlane({ res })}
        />
      </Group>

      <Group title="Quantities">
        <StudioQuantityPicker />
      </Group>

      <Group title="Colour scale">
        <FieldLabel>Colormap</FieldLabel>
        <LabeledSelect<string> value={colormap} options={COLORMAP_OPTIONS} onChange={setColormap} />

        <FieldLabel>Scale</FieldLabel>
        <Segmented<StudioScaleMode> value={scaleMode} options={SCALE_OPTIONS} onChange={setScaleMode} />
      </Group>
    </div>
  )
}
