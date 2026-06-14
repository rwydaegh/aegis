import type { StudioFocusMode, StudioPlaneOrientation, Vec3 } from '../api'
import { useStudioStore, type StudioScaleMode } from '../store'
import {
  beamAvailability,
  beamOptions,
  conditionHasRayPack,
  EXTENT_OPTIONS_M,
  extentLabel,
  ORIENTATION_OPTIONS,
  packsOf,
  RESOLUTION_OPTIONS,
} from './controls'
import StudioQuantityPicker from './StudioQuantityPicker'
import {
  Checkbox,
  DiscreteSlider,
  FieldLabel,
  Group,
  LabeledSelect,
  Segmented,
  Slider,
  type Option,
} from './widgets'

const COLORMAP_OPTIONS: Option<string>[] = [
  { value: 'viridis', label: 'Viridis' },
  { value: 'jet', label: 'Jet' },
]

const SCALE_OPTIONS: Option<StudioScaleMode>[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'fixed', label: 'Fixed' },
  { value: 'log', label: 'Log' },
]

const FOCUS_MODE_OPTIONS: Option<StudioFocusMode>[] = [
  { value: 'at-skin', label: 'At skin' },
  { value: 'free-space', label: 'Free space' },
]

const CONDITION_LABELS: Record<string, string> = { los: 'LOS', nlos: 'NLOS' }

const FREQ_TOOLTIP =
  'Sweeps the dosimetry frequency over the fixed 28 GHz multipath geometry ' +
  '(specular geometry is frequency independent); not a per-frequency re-trace.'

// Focus slider ranges (server Z-up metres), sized to the placed phantom's
// bounding box with a little slack so the focus can sit just off the skin.
const FOCUS_RANGE: Record<'x' | 'y' | 'z', [number, number]> = {
  x: [0.3, 1.5],
  y: [-0.6, 0.6],
  z: [0.0, 1.9],
}

/**
 * The studio control surface: every design-space axis the backend supports,
 * grouped and wired to the store. Controls whose precomputed packs are absent
 * (NLOS without a ray pack, ECBF without a Q pack, body-map quantities without
 * a pack) grey out with an inline hint.
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
  const ecbfBudgetFrac = useStudioStore((s) => s.ecbfBudgetFrac)
  const setEcbfBudgetFrac = useStudioStore((s) => s.setEcbfBudgetFrac)

  const frequencyGhz = useStudioStore((s) => s.frequencyGhz)
  const setFrequencyGhz = useStudioStore((s) => s.setFrequencyGhz)

  const focusMode = useStudioStore((s) => s.focusMode)
  const setFocusMode = useStudioStore((s) => s.setFocusMode)
  const focusXyz = useStudioStore((s) => s.focusXyz)
  const setFocusXyz = useStudioStore((s) => s.setFocusXyz)
  const pickFocusOnBody = useStudioStore((s) => s.pickFocusOnBody)
  const setPickFocusOnBody = useStudioStore((s) => s.setPickFocusOnBody)

  const plane = useStudioStore((s) => s.plane)
  const setPlane = useStudioStore((s) => s.setPlane)

  const colormap = useStudioStore((s) => s.colormap)
  const setColormap = useStudioStore((s) => s.setColormap)
  const scaleMode = useStudioStore((s) => s.scaleMode)
  const setScaleMode = useStudioStore((s) => s.setScaleMode)

  const topK = useStudioStore((s) => s.topK)
  const setTopK = useStudioStore((s) => s.setTopK)
  const showRays = useStudioStore((s) => s.showRays)
  const setShowRays = useStudioStore((s) => s.setShowRays)
  const showArrayPattern = useStudioStore((s) => s.showArrayPattern)
  const setShowArrayPattern = useStudioStore((s) => s.setShowArrayPattern)
  const wireframe = useStudioStore((s) => s.wireframe)
  const setWireframe = useStudioStore((s) => s.setWireframe)

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

  const beams: Option<string>[] = beamOptions(manifest).map((b) => {
    const { available, hint } = beamAvailability(packs, b.value, condition, arrayN, frequencyGhz)
    return { value: b.value, label: b.label, disabled: !available, hint }
  })

  const frequencies = manifest?.frequencies ?? [frequencyGhz]

  const setFocusAxis = (i: 0 | 1 | 2, v: number) => {
    const f = [...focusXyz] as Vec3
    f[i] = v
    setFocusXyz(f)
  }

  const normal: Vec3 = plane.normalXyz ?? [1, 0, 0]
  const setNormalAxis = (i: 0 | 1 | 2, v: number) => {
    const n = [...normal] as Vec3
    n[i] = v
    setPlane({ normalXyz: n })
  }

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

      <Group title="Beam">
        <LabeledSelect<string> value={beam} options={beams} onChange={setBeam} />
        {beam === 'ecbf' && (
          <>
            <FieldLabel title="ECBF absorbed-power budget as a fraction of the MRT operating point. 1 reproduces MRT; lower trades received signal for lower whole-body dose.">
              Exposure budget (fraction of MRT)
            </FieldLabel>
            <Slider
              value={ecbfBudgetFrac}
              min={0.05}
              max={1}
              step={0.05}
              onChange={setEcbfBudgetFrac}
              labelOf={(v) => `${Math.round(v * 100)}%`}
            />
          </>
        )}
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

      <Group title="Focus">
        <FieldLabel title="At-skin snaps the focus onto the nearest body surface; free-space leaves it where set.">
          Focus mode
        </FieldLabel>
        <Segmented<StudioFocusMode> value={focusMode} options={FOCUS_MODE_OPTIONS} onChange={setFocusMode} />

        <Checkbox
          checked={pickFocusOnBody}
          onChange={setPickFocusOnBody}
          title="When on, click anywhere on the body to move the beam focus to that surface point."
        >
          Pick focus by clicking the body
        </Checkbox>

        <FieldLabel>Focus position (m, Z-up)</FieldLabel>
        <Slider value={focusXyz[0]} min={FOCUS_RANGE.x[0]} max={FOCUS_RANGE.x[1]} step={0.01} onChange={(v) => setFocusAxis(0, v)} labelOf={(v) => `x ${v.toFixed(2)}`} />
        <Slider value={focusXyz[1]} min={FOCUS_RANGE.y[0]} max={FOCUS_RANGE.y[1]} step={0.01} onChange={(v) => setFocusAxis(1, v)} labelOf={(v) => `y ${v.toFixed(2)}`} />
        <Slider value={focusXyz[2]} min={FOCUS_RANGE.z[0]} max={FOCUS_RANGE.z[1]} step={0.01} onChange={(v) => setFocusAxis(2, v)} labelOf={(v) => `z ${v.toFixed(2)}`} />
      </Group>

      <Group title="Slice">
        <FieldLabel>Orientation</FieldLabel>
        <Segmented<StudioPlaneOrientation>
          value={plane.orientation}
          options={ORIENTATION_OPTIONS}
          onChange={(orientation) =>
            // The free plane needs a normal or the backend rejects the slice; seed
            // a sensible default (toward the BS) the first time free is selected.
            setPlane(
              orientation === 'free' && !plane.normalXyz
                ? { orientation, normalXyz: [1, 0, 0] }
                : { orientation },
            )
          }
        />

        {plane.orientation === 'free' && (
          <>
            <FieldLabel title="Plane normal for the free orientation (unnormalised; the backend normalises).">
              Plane normal
            </FieldLabel>
            <Slider value={normal[0]} min={-1} max={1} step={0.05} onChange={(v) => setNormalAxis(0, v)} labelOf={(v) => `nx ${v.toFixed(2)}`} />
            <Slider value={normal[1]} min={-1} max={1} step={0.05} onChange={(v) => setNormalAxis(1, v)} labelOf={(v) => `ny ${v.toFixed(2)}`} />
            <Slider value={normal[2]} min={-1} max={1} step={0.05} onChange={(v) => setNormalAxis(2, v)} labelOf={(v) => `nz ${v.toFixed(2)}`} />
          </>
        )}

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

      <Group title="Display">
        <Checkbox checked={showRays} onChange={setShowRays} title="Draw the strongest arrival rays from the base station.">
          Show arrival rays
        </Checkbox>
        <FieldLabel title="How many of the strongest arrival rays to draw.">Ray count</FieldLabel>
        <Slider
          value={topK}
          min={10}
          max={500}
          step={10}
          onChange={setTopK}
          disabled={!showRays}
          labelOf={(v) => String(v)}
        />
        <Checkbox checked={showArrayPattern} onChange={setShowArrayPattern} title="Draw the base-station array pattern lobe.">
          Show array pattern
        </Checkbox>
        <Checkbox checked={wireframe} onChange={setWireframe} title="Render the phantom as a wireframe.">
          Body wireframe
        </Checkbox>
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
