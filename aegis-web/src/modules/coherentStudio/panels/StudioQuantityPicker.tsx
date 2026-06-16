import { useEffect } from 'react'
import type { StudioBodyMapStatistic, StudioFieldQuantity } from '../api'
import { useStudioStore } from '../store'
import {
  bodyMapHasPack,
  channelHasPack,
  ensembleHasPack,
  FIELD_QUANTITY_OPTIONS,
  packsOf,
  reconcileBodyMapQuantity,
} from './controls'
import { FieldLabel, HelpText, LabeledSelect, type Option } from './widgets'

// The live, focus-tracking deposited map is served from the field-channel pack
// rather than a static body-map pack, so it is offered as its own quantity.
const LIVE_DEPOSITED = 'deposited'

const QTY_LABELS: Record<string, string> = {
  deposited: 'Deposited (live, beam+focus)',
  floor: 'Floor (lower bound)',
  mrt: 'MRT (focused)',
  worstcase: 'Worst case',
  amp: 'Amplified',
}

// Code-grounded explanations (scripts/studio_precompute.py _maps_from_g, and the
// live src/aegis/viewer/routes/studio/_channel.py). All are absorbed power
// density W/m^2 per watt of transmit power, except amp which is a ratio.
const QTY_DESCRIPTIONS: Record<string, string> = {
  deposited:
    'Absorbed power density S_ab on each skin triangle under the beam and focus you set, recomputed live as you steer (S_ab = ||G̃·x||²). The headline interaction.',
  floor:
    'Incoherent lower bound: the absorbed power with no coherent focusing (equal amplitude, random phase, averaged over phase). Every coherent beam sits at or above this.',
  mrt: 'Absorbed power deposited by the matched-ratio (communication) beam at the reference chest focus. What a normal base-station beam does to the body.',
  worstcase:
    'Per-triangle upper bound: the most absorption any unit-power beam could deposit on each patch (the exposure eigenvalue λ_max). Independent of any one beam.',
  amp: 'Amplification factor = worst case / floor. How much coherent focusing can raise absorption above the incoherent baseline at each patch. Large where the array has many independent looks.',
}

/** Plain-language description for the current slice field quantity. */
function fieldDescription(value: string): string {
  return FIELD_QUANTITY_OPTIONS.find((o) => o.value === value)?.title ?? ''
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
  const preferDeposited = useStudioStore((s) => s.preferDeposited)
  const setPreferDeposited = useStudioStore((s) => s.setPreferDeposited)
  const bodyMapStatistic = useStudioStore((s) => s.bodyMapStatistic)
  const setBodyMapStatistic = useStudioStore((s) => s.setBodyMapStatistic)

  const manifest = useStudioStore((s) => s.manifest)
  const mesh = useStudioStore((s) => s.mesh)
  const condition = useStudioStore((s) => s.condition)
  const arrayN = useStudioStore((s) => s.arrayN)
  const frequencyGhz = useStudioStore((s) => s.frequencyGhz)
  const seed = useStudioStore((s) => s.seed)

  const packs = packsOf(manifest)
  // Drop any backend-advertised 'deposited' so it is not listed twice: the live
  // option is always prepended below, gated by the channel pack.
  const bodyQuantities = (manifest?.body_map_quantities ?? []).filter((q) => q !== LIVE_DEPOSITED)
  const statistics = manifest?.body_map_statistics ?? ['single']

  const liveAvailable = channelHasPack(packs, mesh, condition, arrayN, frequencyGhz, seed)
  const isLive = bodyMapQuantity === LIVE_DEPOSITED

  const bodyOptions: Option<string>[] = [
    {
      value: LIVE_DEPOSITED,
      label: QTY_LABELS[LIVE_DEPOSITED],
      disabled: !liveAvailable,
      hint: 'no channel pack',
      title: QTY_DESCRIPTIONS[LIVE_DEPOSITED],
    },
    ...bodyQuantities.map((q) => {
      const available = bodyMapHasPack(packs, mesh, condition, arrayN, q, frequencyGhz)
      return {
        value: q,
        label: QTY_LABELS[q] ?? q,
        disabled: !available,
        hint: 'no pack',
        title: QTY_DESCRIPTIONS[q],
      }
    }),
  ]

  // Explicit picks from the dropdown set the sticky preference: choosing the
  // live map turns auto-promotion on, choosing anything else turns it off (the
  // user wants that static quantity, so do not yank them back to 'deposited').
  // The auto fall-back / promote effects below use the raw setter so they never
  // touch the preference.
  const onPickQuantity = (q: string) => {
    setPreferDeposited(q === LIVE_DEPOSITED)
    setBodyMapQuantity(q)
  }

  // Keep the body-map quantity reconciled with the live map's availability and
  // the sticky preference: fall back to 'mrt' on a dead live selection, promote
  // back to 'deposited' once its channel pack returns. Gate on the manifest:
  // before it loads, packs is empty and liveAvailable is spuriously false, which
  // would otherwise clobber the default 'deposited' quantity on first mount.
  const nextQuantity = manifest
    ? reconcileBodyMapQuantity({ current: bodyMapQuantity, preferDeposited, liveAvailable })
    : null
  useEffect(() => {
    if (nextQuantity) setBodyMapQuantity(nextQuantity)
  }, [nextQuantity, setBodyMapQuantity])

  const statOptions: Option<StudioBodyMapStatistic>[] = statistics.map((st) => {
    const available = ensembleHasPack(packs, st, mesh, condition, arrayN, bodyMapQuantity, frequencyGhz)
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
  const statAvailable = ensembleHasPack(packs, bodyMapStatistic, mesh, condition, arrayN, bodyMapQuantity, frequencyGhz)
  useEffect(() => {
    if (bodyMapStatistic !== 'single' && !statAvailable) setBodyMapStatistic('single')
  }, [bodyMapStatistic, statAvailable, setBodyMapStatistic])

  return (
    <div>
      <FieldLabel title="The scalar field reduction painted onto the free-space slice plane.">Slice quantity</FieldLabel>
      <LabeledSelect<StudioFieldQuantity>
        value={fieldQuantity}
        options={FIELD_QUANTITY_OPTIONS}
        onChange={setFieldQuantity}
      />
      <HelpText>{fieldDescription(fieldQuantity)}</HelpText>

      <FieldLabel title="The per-triangle quantity painted onto the phantom body surface.">
        Body-map quantity
      </FieldLabel>
      <LabeledSelect<string>
        value={bodyMapQuantity}
        options={bodyOptions}
        onChange={onPickQuantity}
      />
      <HelpText>{QTY_DESCRIPTIONS[bodyMapQuantity] ?? ''}</HelpText>

      {isLive ? (
        <HelpText tone="live">
          Live map: tracks the focus, beam, budget and receive antenna. Move the focus and the body recolours.
        </HelpText>
      ) : (
        <>
          <HelpText tone="warn">
            Static pack, frozen at a reference chest focus and a dipole receive antenna: the focus
            slider and antenna picker do not change it. Pick &ldquo;Deposited (live)&rdquo; for a
            focus-tracking map.
          </HelpText>
          <FieldLabel title="Single seed, or the mean / 95th percentile of the body map over the LOS seed ensemble (seeds 0-5). Ensemble packs are LOS-only.">
            Body-map realisation
          </FieldLabel>
          <LabeledSelect<StudioBodyMapStatistic>
            value={bodyMapStatistic}
            options={statOptions}
            onChange={setBodyMapStatistic}
          />
        </>
      )}
    </div>
  )
}
