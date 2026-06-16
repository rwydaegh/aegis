import type { StudioFocusMode, StudioPlaneOrientation, Vec3 } from '../api'
import { useStudioStore, type StudioScaleMode, type StudioUeAntenna } from '../store'
import { useStudioScales } from '../useStudioScales'
import type { StudioScaleScope } from '../scene/colorScale'
import {
  arraySizeHasRayPack,
  beamAvailability,
  beamOptions,
  conditionHasRayPack,
  EXTENT_OPTIONS_M,
  extentLabel,
  ORIENTATION_OPTIONS,
  packsOf,
  phantomHasPack,
  RESOLUTION_OPTIONS,
} from './controls'
import StudioQuantityPicker from './StudioQuantityPicker'
import StudioExposureHistogram from './StudioExposureHistogram'
import StudioRadialFalloff from './StudioRadialFalloff'
import StudioLineProfile from './StudioLineProfile'
import StudioPatternCut from './StudioPatternCut'
import StudioCompare from './StudioCompare'
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
  { value: 'plasma', label: 'Plasma' },
  { value: 'inferno', label: 'Inferno' },
  { value: 'magma', label: 'Magma' },
  { value: 'cividis', label: 'Cividis' },
  { value: 'turbo', label: 'Turbo' },
  { value: 'jet', label: 'Jet (legacy)' },
]

const UE_ANTENNA_OPTIONS: Option<StudioUeAntenna>[] = [
  { value: 'isotropic', label: 'Isotropic' },
  { value: 'vertical', label: 'Vertical (reference)' },
  { value: 'dipole', label: 'Half-wave dipole' },
  { value: 'patch', label: 'Patch (cos^n)' },
]

const SCALE_OPTIONS: Option<StudioScaleMode>[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'fixed', label: 'Fixed' },
  { value: 'log', label: 'Log' },
]

const SCOPE_OPTIONS: Option<StudioScaleScope>[] = [
  { value: 'surface', label: 'Per-surface' },
  { value: 'shared', label: 'Shared' },
]

// A compact numeric field for the fixed colour range. Shows the live value but
// only commits a parsed, finite number on blur / Enter, so partial typing never
// pushes a NaN range into the store.
function RangeInput({ value, onCommit, label }: { value: number; onCommit: (v: number) => void; label: string }) {
  const commit = (raw: string) => {
    const n = parseFloat(raw)
    if (Number.isFinite(n)) onCommit(n)
  }
  return (
    <label style={{ flex: 1, fontSize: 10, color: '#8a93a6' }}>
      {label}
      <input
        type="number"
        defaultValue={value}
        key={value}
        step="any"
        onBlur={(e) => commit(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') commit((e.target as HTMLInputElement).value)
        }}
        style={{
          width: '100%',
          marginTop: 2,
          padding: '3px 5px',
          fontSize: 11,
          fontFamily: 'monospace',
          color: '#dde',
          background: '#0e1016',
          border: '1px solid #2a2f3a',
          borderRadius: 4,
        }}
      />
    </label>
  )
}

const FOCUS_MODE_OPTIONS: Option<StudioFocusMode>[] = [
  { value: 'at-skin', label: 'At skin' },
  { value: 'free-space', label: 'Free space' },
]

// Per-axis sample counts for the 3D field-volume box (clamped 8..48 server-side;
// res^3 points, so 40^3 ~ 64k is the practical ceiling on CPU).
const VOLUME_RES_OPTIONS: Option<number>[] = [
  { value: 16, label: '16' },
  { value: 24, label: '24' },
  { value: 32, label: '32' },
  { value: 40, label: '40' },
]

// Box side lengths for the field volume; kept small (the box is centred on the
// focus to show the focal lobe, not the whole room).
const VOLUME_EXTENT_OPTIONS_M = [0.08, 0.16, 0.4] as const

const CONDITION_LABELS: Record<string, string> = { los: 'LOS', nlos: 'NLOS' }

// IT'IS virtual family phantoms. Labels carry the age/sex so the geometry change
// reads as deliberate (Thelonious is a 6-year-old; Duke/Ella/Eartha are adults).
const PHANTOM_LABELS: Record<string, string> = {
  thelonious: 'Thelonious (6 yo)',
  duke: 'Duke (34 yo M)',
  ella: 'Ella (26 yo F)',
  eartha: 'Eartha (8 yo F)',
}

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

  const mesh = useStudioStore((s) => s.mesh)
  const setMesh = useStudioStore((s) => s.setMesh)
  const condition = useStudioStore((s) => s.condition)
  const setCondition = useStudioStore((s) => s.setCondition)
  const seed = useStudioStore((s) => s.seed)
  const setSeed = useStudioStore((s) => s.setSeed)
  const arrayN = useStudioStore((s) => s.arrayN)
  const setArrayN = useStudioStore((s) => s.setArrayN)

  const beam = useStudioStore((s) => s.beam)
  const setBeam = useStudioStore((s) => s.setBeam)
  const ueAntenna = useStudioStore((s) => s.ueAntenna)
  const setUeAntenna = useStudioStore((s) => s.setUeAntenna)
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
  const scaleScope = useStudioStore((s) => s.scaleScope)
  const setScaleScope = useStudioStore((s) => s.setScaleScope)
  const dynamicRangeDb = useStudioStore((s) => s.dynamicRangeDb)
  const setDynamicRangeDb = useStudioStore((s) => s.setDynamicRangeDb)
  const robustClip = useStudioStore((s) => s.robustClip)
  const setRobustClip = useStudioStore((s) => s.setRobustClip)
  const fixedRange = useStudioStore((s) => s.fixedRange)
  const setFixedRange = useStudioStore((s) => s.setFixedRange)
  const scales = useStudioScales()

  const topK = useStudioStore((s) => s.topK)
  const setTopK = useStudioStore((s) => s.setTopK)
  const showRays = useStudioStore((s) => s.showRays)
  const setShowRays = useStudioStore((s) => s.setShowRays)
  const showArrayPattern = useStudioStore((s) => s.showArrayPattern)
  const setShowArrayPattern = useStudioStore((s) => s.setShowArrayPattern)
  const showRxPattern = useStudioStore((s) => s.showRxPattern)
  const setShowRxPattern = useStudioStore((s) => s.setShowRxPattern)
  const rxPatternExtentM = useStudioStore((s) => s.rxPatternExtentM)
  const setRxPatternExtentM = useStudioStore((s) => s.setRxPatternExtentM)
  const rayCutoffM = useStudioStore((s) => s.rayCutoffM)
  const setRayCutoffM = useStudioStore((s) => s.setRayCutoffM)
  const wireframe = useStudioStore((s) => s.wireframe)
  const setWireframe = useStudioStore((s) => s.setWireframe)
  const showBlockers = useStudioStore((s) => s.showBlockers)
  const setShowBlockers = useStudioStore((s) => s.setShowBlockers)
  const showRoomOutline = useStudioStore((s) => s.showRoomOutline)
  const setShowRoomOutline = useStudioStore((s) => s.setShowRoomOutline)
  const background = useStudioStore((s) => s.background)
  const setBackground = useStudioStore((s) => s.setBackground)
  const arrayPatternScale = useStudioStore((s) => s.arrayPatternScale)
  const setArrayPatternScale = useStudioStore((s) => s.setArrayPatternScale)
  const screenshotMode = useStudioStore((s) => s.screenshotMode)
  const setScreenshotMode = useStudioStore((s) => s.setScreenshotMode)
  const showVolume = useStudioStore((s) => s.showVolume)
  const setShowVolume = useStudioStore((s) => s.setShowVolume)
  const volumeRes = useStudioStore((s) => s.volumeRes)
  const setVolumeRes = useStudioStore((s) => s.setVolumeRes)
  const volumeExtentM = useStudioStore((s) => s.volumeExtentM)
  const setVolumeExtentM = useStudioStore((s) => s.setVolumeExtentM)
  const volumeThreshold = useStudioStore((s) => s.volumeThreshold)
  const setVolumeThreshold = useStudioStore((s) => s.setVolumeThreshold)
  const volumeOpacity = useStudioStore((s) => s.volumeOpacity)
  const setVolumeOpacity = useStudioStore((s) => s.setVolumeOpacity)

  const packs = packsOf(manifest)

  const phantomOptions: Option<string>[] = (manifest?.phantoms ?? [mesh]).map((p) => ({
    value: p,
    label: PHANTOM_LABELS[p] ?? p,
    disabled: !phantomHasPack(packs, p),
    hint: 'no pack',
  }))

  const conditionOptions: Option<string>[] = (manifest?.conditions ?? ['los']).map((c) => ({
    value: c,
    label: CONDITION_LABELS[c] ?? c.toUpperCase(),
    disabled: !conditionHasRayPack(packs, c, arrayN),
    hint: 'no pack',
  }))

  // Per-side URA count: bs{n} is an n x n array, so n = 16 is 256 elements.
  // Surface the element count in the label so the array size reads physically.
  const arrayOptions: Option<number>[] = (manifest?.array_sizes ?? [arrayN]).map((n) => ({
    value: n,
    label: `${n}x${n} (${n * n} ant)`,
    disabled: !arraySizeHasRayPack(packs, n, condition),
    hint: 'no pack',
  }))

  const seedOptions: Option<number>[] = (manifest?.seeds ?? [seed]).map((s) => ({
    value: s,
    label: `Seed ${s}`,
  }))

  const beams: Option<string>[] = beamOptions(manifest).map((b) => {
    const { available, hint } = beamAvailability(packs, b.value, mesh, condition, arrayN, frequencyGhz)
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
        <FieldLabel title="Anatomical phantom (IT'IS virtual family). Switches the body geometry and all per-body dosimetry packs.">
          Phantom
        </FieldLabel>
        <LabeledSelect<string> value={mesh} options={phantomOptions} onChange={setMesh} />

        <FieldLabel title="Line-of-sight or non-line-of-sight multipath condition.">
          Condition
        </FieldLabel>
        <Segmented<string> value={condition} options={conditionOptions} onChange={setCondition} />

        <FieldLabel title="Base-station array size (per-side count of the square URA). 16 is a 256-element array.">
          Array
        </FieldLabel>
        <Segmented<number> value={arrayN} options={arrayOptions} onChange={setArrayN} />

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

        <FieldLabel title="UE receive antenna pattern C_R(k). The signal channel projects each path via C_R(k)^H psi, so the receive antenna reshapes the matched filter and the resulting beam, hence (indirectly) the deposited map. Affects the live slice / deposited / volume; the worst-case beam and the static body-map packs do not use it.">
          Receive antenna
        </FieldLabel>
        <LabeledSelect<StudioUeAntenna> value={ueAntenna} options={UE_ANTENNA_OPTIONS} onChange={setUeAntenna} />
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
        <FieldLabel title="Gap between the focus and the ray arrowheads, so the rays stop short of the hotspot instead of occluding it. Independent of the Rx pattern size.">
          Ray cutoff radius
        </FieldLabel>
        <Slider
          value={rayCutoffM}
          min={0}
          max={2}
          step={0.05}
          onChange={setRayCutoffM}
          disabled={!showRays}
          labelOf={(v) => `${v.toFixed(2)} m`}
        />
        <Checkbox checked={showArrayPattern} onChange={setShowArrayPattern} title="Draw the base-station array pattern lobe.">
          Show array pattern
        </Checkbox>
        <FieldLabel title="Cosmetically blow up the array pattern lobe so it reads from the distant Rx vantage (the array is ~14 m away). 1 = true size.">
          Pattern magnify
        </FieldLabel>
        <Slider
          value={arrayPatternScale}
          min={1}
          max={60}
          step={1}
          onChange={setArrayPatternScale}
          disabled={!showArrayPattern}
          labelOf={(v) => `${v}x`}
        />
        <Checkbox checked={showRxPattern} onChange={setShowRxPattern} title="Draw the UE receive antenna pattern |C_R(k)| as a 3D lobe at the focus (r_UE). Reflects the selected receive antenna in the world (Z-up) frame the precoder uses.">
          Show Rx pattern
        </Checkbox>
        <FieldLabel title="Maximum radius of the Rx pattern lobe in metres (display only).">Rx pattern size</FieldLabel>
        <Slider
          value={rxPatternExtentM}
          min={0.1}
          max={2}
          step={0.1}
          onChange={setRxPatternExtentM}
          disabled={!showRxPattern}
          labelOf={(v) => `${v.toFixed(1)} m`}
        />
        <Checkbox checked={wireframe} onChange={setWireframe} title="Render the phantom as a wireframe.">
          Body wireframe
        </Checkbox>
      </Group>

      <Group title="Scene & capture">
        <Checkbox
          checked={showBlockers}
          onChange={setShowBlockers}
          title="Draw the real traced factory blockers: metallic scatterer cuboids, plus the NLOS corridor slab (semi-transparent) in the NLOS condition."
        >
          Show blockers
        </Checkbox>
        <Checkbox
          checked={showRoomOutline}
          onChange={setShowRoomOutline}
          title="Draw the room as a lineart wireframe (the factory outline) to convey the 3D space."
        >
          Room outline
        </Checkbox>
        <FieldLabel title="Scene backdrop. Transparent exports a figure-ready PNG with no background.">Background</FieldLabel>
        <Segmented<'dark' | 'white' | 'transparent'>
          value={background}
          options={[
            { value: 'dark', label: 'Dark' },
            { value: 'white', label: 'White' },
            { value: 'transparent', label: 'None' },
          ]}
          onChange={setBackground}
        />
        <Checkbox
          checked={screenshotMode}
          onChange={setScreenshotMode}
          title="Strip the grid, gizmos and overlays and force a transparent backdrop, leaving only the phantom, field and blockers for a clean figure capture."
        >
          Screenshot mode
        </Checkbox>
      </Group>

      <Group title="Field volume (3D)">
        <Checkbox
          checked={showVolume}
          onChange={setShowVolume}
          title="Reconstruct the field on a 3D box around the focus and draw the focal lobe as a coloured voxel cloud. More expensive than the 2D slice."
        >
          Show field volume
        </Checkbox>
        {showVolume && (
          <>
            <FieldLabel title="Side length of the box centred on the focus.">Box size</FieldLabel>
            <DiscreteSlider<number>
              value={volumeExtentM}
              options={VOLUME_EXTENT_OPTIONS_M as unknown as number[]}
              labelOf={extentLabel}
              onChange={setVolumeExtentM}
            />

            <FieldLabel title="Per-axis sample count; the box holds res³ voxels, so higher is sharper but slower.">
              Resolution
            </FieldLabel>
            <Segmented<number> value={volumeRes} options={VOLUME_RES_OPTIONS} onChange={setVolumeRes} />

            <FieldLabel title="Hide voxels below this fraction of the box peak, so only the bright lobe is drawn.">
              Threshold
            </FieldLabel>
            <Slider
              value={volumeThreshold}
              min={0.05}
              max={0.95}
              step={0.05}
              onChange={setVolumeThreshold}
              labelOf={(v) => `${Math.round(v * 100)}% of peak`}
            />

            <FieldLabel title="Per-voxel cube opacity. Lower to see through a dense cloud.">
              Opacity
            </FieldLabel>
            <Slider
              value={volumeOpacity}
              min={0.1}
              max={1}
              step={0.05}
              onChange={setVolumeOpacity}
              labelOf={(v) => `${Math.round(v * 100)}%`}
            />
          </>
        )}
      </Group>

      <Group title="Colour scale">
        <FieldLabel>Colormap</FieldLabel>
        <LabeledSelect<string> value={colormap} options={COLORMAP_OPTIONS} onChange={setColormap} />

        <FieldLabel title="Per-surface autoscales each of the slice, body, and volume to its own range. Shared puts all three on one range so equal colours mean equal values.">
          Scope
        </FieldLabel>
        <Segmented<StudioScaleScope> value={scaleScope} options={SCOPE_OPTIONS} onChange={setScaleScope} />

        <FieldLabel title="Auto autoscales to the data. Fixed locks an editable range. Log uses a dB window below the peak.">
          Scale
        </FieldLabel>
        <Segmented<StudioScaleMode>
          value={scaleMode}
          options={SCALE_OPTIONS}
          onChange={(m) => {
            // Entering Fixed for the first time, seed the locked range from what is
            // currently on screen so the view does not jump.
            if (m === 'fixed' && !fixedRange) setFixedRange(scales.autoRange)
            setScaleMode(m)
          }}
        />

        {scaleMode === 'log' && (
          <>
            <FieldLabel title="Span of the logarithmic colour window below the peak, in decibels.">
              Dynamic range
            </FieldLabel>
            <Slider
              value={dynamicRangeDb}
              min={10}
              max={60}
              step={5}
              onChange={setDynamicRangeDb}
              labelOf={(v) => `${v} dB`}
            />
          </>
        )}

        {scaleMode === 'fixed' && (
          <>
            <FieldLabel>Fixed range</FieldLabel>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', margin: '2px 0 6px' }}>
              <RangeInput
                value={fixedRange?.vmin ?? scales.autoRange.vmin}
                onCommit={(vmin) => setFixedRange({ vmin, vmax: fixedRange?.vmax ?? scales.autoRange.vmax })}
                label="min"
              />
              <RangeInput
                value={fixedRange?.vmax ?? scales.autoRange.vmax}
                onCommit={(vmax) => setFixedRange({ vmin: fixedRange?.vmin ?? scales.autoRange.vmin, vmax })}
                label="max"
              />
            </div>
            <button
              type="button"
              onClick={() => setFixedRange(scales.autoRange)}
              style={{
                width: '100%',
                padding: '5px 8px',
                fontSize: 11,
                color: '#bcd',
                background: '#161922',
                border: '1px solid #2a2f3a',
                borderRadius: 5,
                cursor: 'pointer',
              }}
            >
              Lock to current view
            </button>
          </>
        )}

        <Checkbox
          checked={robustClip}
          onChange={setRobustClip}
          title="Clip the colour range to the 0.5th..99.5th percentiles so a single hot triangle or voxel does not wash out the map."
        >
          Robust autoscale (clip outliers)
        </Checkbox>
      </Group>

      <Group title="Distribution">
        <StudioExposureHistogram />
      </Group>

      <Group title="Line probe">
        <StudioLineProfile />
      </Group>

      <Group title="Falloff">
        <StudioRadialFalloff />
      </Group>

      <Group title="Array pattern">
        <StudioPatternCut />
      </Group>

      <Group title="A/B compare">
        <StudioCompare />
      </Group>
    </div>
  )
}
