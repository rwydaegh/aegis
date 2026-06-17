import type { StudioFocusMode, Vec3 } from '../api'
import {
  useStudioStore,
  type StudioCameraView,
  type StudioRayColorMode,
  type StudioScaleMode,
  type StudioUeAntenna,
} from '../store'
import { useStudioScales } from '../useStudioScales'
import type { StudioScaleScope } from '../scene/colorScale'
import {
  activeOrientationKey,
  arraySizeHasRayPack,
  beamAvailability,
  beamDescription,
  beamOptions,
  conditionHasRayPack,
  EXTENT_OPTIONS_M,
  extentLabel,
  ORIENTATION_OPTIONS,
  orientationDescription,
  orientationPatch,
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
  HelpText,
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
  { value: 'jet', label: 'Jet' },
]

const UE_ANTENNA_OPTIONS: Option<StudioUeAntenna>[] = [
  { value: 'isotropic', label: 'Isotropic', title: 'Flat directivity (vertical polarisation), unit sphere-average gain. The receiver weights every arrival direction equally.' },
  { value: 'vertical', label: 'Vertical (reference)', title: 'Legacy unit-gain vertical reference, no directivity.' },
  { value: 'dipole', label: 'Half-wave dipole', title: 'Analytic half-wave dipole pattern (the default): donut directivity with a null along the dipole axis.' },
  { value: 'patch', label: 'Patch (cos^n)', title: 'cos^n(theta) front-facing patch directivity: a forward lobe that rejects the back hemisphere.' },
]

const SCALE_OPTIONS: Option<StudioScaleMode>[] = [
  { value: 'auto', label: 'Auto', title: 'Linear scale, floor pinned to zero, top taken from the data.' },
  { value: 'fixed', label: 'Fixed', title: 'Hold a user-locked min and max so frames stay comparable.' },
  { value: 'log', label: 'Log', title: 'Logarithmic over a dynamic-range window below the peak (set the dB span below).' },
]

const RAY_COLOR_OPTIONS: Option<StudioRayColorMode>[] = [
  { value: 'power', label: 'By power', title: 'Tint each ray by its path power on the active colormap (dB scale), so colour echoes the field map.' },
  { value: 'mono', label: 'Neutral', title: 'Draw the rays in a single neutral colour so they read as geometry and do not compete with the field colour scale. Power still drives width and opacity.' },
]

const CAMERA_OPTIONS: Option<StudioCameraView>[] = [
  { value: 'orbit', label: 'Free orbit', title: 'Orbit, pan and zoom the camera freely. The app never moves the camera in this mode.' },
  { value: 'bs-axis', label: 'BS axis', title: 'Park the camera looking down the base-station to focus beam axis, re-applied whenever the focus moves. Switch back to Free orbit to move the camera yourself.' },
]

const SCOPE_OPTIONS: Option<StudioScaleScope>[] = [
  { value: 'surface', label: 'Per-surface', title: 'Each surface (slice, body, volume) autoscales to its own data range.' },
  { value: 'shared', label: 'Shared', title: 'One colour range shared by all visible surfaces, so equal colours mean equal values everywhere.' },
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
  { value: 'at-skin', label: 'At skin', title: 'Snaps the focus to the nearest skin triangle before forming the beam, so it targets the body surface where absorbed power matters.' },
  { value: 'free-space', label: 'Free space', title: 'The focus stays exactly where you put it, including in mid-air.' },
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
  const resetDefaults = useStudioStore((s) => s.resetDefaults)

  const mesh = useStudioStore((s) => s.mesh)
  const setMesh = useStudioStore((s) => s.setMesh)
  const condition = useStudioStore((s) => s.condition)
  const setCondition = useStudioStore((s) => s.setCondition)
  const seed = useStudioStore((s) => s.seed)
  const setSeed = useStudioStore((s) => s.setSeed)
  const arrayN = useStudioStore((s) => s.arrayN)
  const setArrayN = useStudioStore((s) => s.setArrayN)
  const ueIdx = useStudioStore((s) => s.ueIdx)
  const setUeIdx = useStudioStore((s) => s.setUeIdx)

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
  const rayThickness = useStudioStore((s) => s.rayThickness)
  const setRayThickness = useStudioStore((s) => s.setRayThickness)
  const rayColorMode = useStudioStore((s) => s.rayColorMode)
  const setRayColorMode = useStudioStore((s) => s.setRayColorMode)
  const showBlockers = useStudioStore((s) => s.showBlockers)
  const setShowBlockers = useStudioStore((s) => s.setShowBlockers)
  const showBeamAxis = useStudioStore((s) => s.showBeamAxis)
  const setShowBeamAxis = useStudioStore((s) => s.setShowBeamAxis)
  const showGizmo = useStudioStore((s) => s.showGizmo)
  const setShowGizmo = useStudioStore((s) => s.setShowGizmo)
  const background = useStudioStore((s) => s.background)
  const setBackground = useStudioStore((s) => s.setBackground)
  const arrayPatternSizeM = useStudioStore((s) => s.arrayPatternSizeM)
  const setArrayPatternSizeM = useStudioStore((s) => s.setArrayPatternSizeM)
  const screenshotMode = useStudioStore((s) => s.screenshotMode)
  const setScreenshotMode = useStudioStore((s) => s.setScreenshotMode)
  const showRefSquare = useStudioStore((s) => s.showRefSquare)
  const setShowRefSquare = useStudioStore((s) => s.setShowRefSquare)
  const cameraView = useStudioStore((s) => s.cameraView)
  const setCameraView = useStudioStore((s) => s.setCameraView)
  const showVolume = useStudioStore((s) => s.showVolume)
  const setShowVolume = useStudioStore((s) => s.setShowVolume)
  const showCompliance = useStudioStore((s) => s.showCompliance)
  const setShowCompliance = useStudioStore((s) => s.setShowCompliance)
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

  // Corridor UE standing positions the body can occupy. The manifest advertises
  // the available indices (0..8); the body's world-x is x = -7 + 2*idx m in the
  // e11 corridor, so idx 4 is the default mid-corridor (+1 m, "14 m") UE.
  const ueIndices = manifest?.ue_indices ?? [ueIdx]
  const ueMin = ueIndices.length ? ueIndices[0] : 0
  const ueMax = ueIndices.length ? ueIndices[ueIndices.length - 1] : 8
  const ueLabel = (i: number) => `UE ${i} (x ${(-7 + 2 * i).toFixed(0)} m)`

  const beams: Option<string>[] = beamOptions(manifest).map((b) => {
    const { available, hint } = beamAvailability(packs, b.value, mesh, condition, arrayN, frequencyGhz)
    return { value: b.value, label: b.label, disabled: !available, hint, title: b.title }
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
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '2px 2px 8px',
        }}
      >
        <span style={{ fontSize: 12, fontWeight: 600, letterSpacing: 0.3, color: '#9aa' }}>CONTROLS</span>
        <button
          type="button"
          onClick={() => {
            if (window.confirm('Reset all studio controls to their defaults?')) resetDefaults()
          }}
          title="Restore every control (channel, beam, slice, colour, overlays, volume) to its default value, and clear the captured A/B reference."
          style={{
            fontSize: 11,
            color: '#bcd',
            background: 'transparent',
            border: '1px solid #2a2a33',
            borderRadius: 5,
            padding: '3px 9px',
            cursor: 'pointer',
          }}
        >
          Reset defaults
        </button>
      </div>
      <Group title="Channel">
        <FieldLabel title="Anatomical phantom (IT'IS virtual family). Switches the body geometry and all per-body dosimetry packs.">
          Phantom
        </FieldLabel>
        <LabeledSelect<string> value={mesh} options={phantomOptions} onChange={setMesh} />

        <FieldLabel title="Line-of-sight vs non-line-of-sight. NLOS inserts a blocker slab between the array and the body, so the body is lit only by reflections and diffraction. LOS ships a 6-seed fading ensemble; NLOS ships seed 0 only.">
          Condition
        </FieldLabel>
        <Segmented<string> value={condition} options={conditionOptions} onChange={setCondition} />

        <FieldLabel title="Side length of the square base-station array, so 16 is a 16x16 = 256-element URA (8 is 64). More elements give a finer focus and a higher worst-case amplification ceiling.">
          Array
        </FieldLabel>
        <Segmented<number> value={arrayN} options={arrayOptions} onChange={setArrayN} />

        <FieldLabel title="Fading realisation index: an independent draw of the small-scale multipath (scatterer placement and phases). LOS has seeds 0-5, NLOS only 0. Shows how much the hotspot moves between statistically-equivalent channels.">Seed</FieldLabel>
        <LabeledSelect<number>
          value={seed}
          options={seedOptions}
          onChange={setSeed}
          parse={(raw) => Number(raw)}
        />

        <FieldLabel title="Where the person stands in the corridor. Slides the body through the 9 candidate UE positions (x = -7..+9 m); the deposited body map and the phantom geometry follow it down the corridor. UE 4 is the default mid-corridor position.">
          Standing position (UE)
        </FieldLabel>
        <Slider
          value={ueIdx}
          min={ueMin}
          max={ueMax}
          step={1}
          onChange={(v) => setUeIdx(Math.round(v))}
          labelOf={ueLabel}
        />
      </Group>

      <Group title="Beam">
        <LabeledSelect<string> value={beam} options={beams} onChange={setBeam} />
        <HelpText>{beamDescription(beam)}</HelpText>

        <FieldLabel title="UE receive antenna pattern C_R(k). The signal channel projects each path via C_R(k)^H psi, so the receive antenna reshapes the matched filter and the resulting beam, hence (indirectly) the deposited map.">
          Receive antenna
        </FieldLabel>
        <LabeledSelect<StudioUeAntenna> value={ueAntenna} options={UE_ANTENNA_OPTIONS} onChange={setUeAntenna} />
        <HelpText>
          Shapes the matched filter, so it affects the MRT / decoy / ECBF / decohered beams and the
          live deposited map. The worst-case beam ignores it, and the static body-map packs are
          frozen at dipole.
        </HelpText>
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
        <FieldLabel title="The cut plane through the focus that the field is reconstructed on. Anatomical planes use fixed world axes; 'facing base station' is the tilted wavefront plane.">
          Orientation
        </FieldLabel>
        <LabeledSelect<string>
          value={activeOrientationKey(plane.orientation, plane.normalXyz)}
          options={ORIENTATION_OPTIONS}
          onChange={(key) => {
            // The free plane needs a finite normal or the backend rejects the
            // slice; seed one when stepping into Custom from a canned orientation.
            const patch = orientationPatch(key)
            if (key === 'free' && !plane.normalXyz) patch.normalXyz = [1, 0, 0]
            setPlane(patch)
          }}
        />
        <HelpText>{orientationDescription(activeOrientationKey(plane.orientation, plane.normalXyz))}</HelpText>

        {plane.orientation === 'free' && (
          <>
            <FieldLabel title="Plane normal in world Z-up metres (unnormalised; the backend normalises). The plane passes through the focus.">
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

      <Group title="Compliance" active={showCompliance}>
        <Checkbox
          checked={showCompliance}
          onChange={setShowCompliance}
          title="Show the ICNIRP compliance readouts for the current beam in the HUD: absorbed power, whole-body SAR, the 4 cm² spatially-averaged peak (psSAR), the peak/mean ratio, and the served signal relative to MRT. Opt-in: the first request per phantom builds the 4 cm² averaging matrix (a few seconds), then updates live as you steer."
        >
          Compliance metrics
        </Checkbox>
      </Group>

      <Group title="Rays" active={showRays}>
        <Checkbox checked={showRays} onChange={setShowRays} title="Draw the strongest arrival rays from the base station, pointing in toward the focus.">
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
        <FieldLabel title="Overall ray thickness. Each ray's width still scales with its path power on top of this, so a higher value makes the strong arrivals bolder relative to the faint ones.">
          Ray thickness
        </FieldLabel>
        <Slider
          value={rayThickness}
          min={0.4}
          max={2.5}
          step={0.1}
          onChange={setRayThickness}
          disabled={!showRays}
          labelOf={(v) => `${v.toFixed(1)}x`}
        />
        <FieldLabel title="Colour the rays by path power (echoing the field colormap) or in a single neutral colour so they read as pure geometry. Width and opacity always track power.">
          Ray colour
        </FieldLabel>
        <Segmented<StudioRayColorMode>
          value={rayColorMode}
          options={RAY_COLOR_OPTIONS}
          onChange={setRayColorMode}
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
      </Group>

      <Group title="Overlays" active={showArrayPattern || showRxPattern || showBeamAxis || showRefSquare || showGizmo}>
        <Checkbox checked={showArrayPattern} onChange={setShowArrayPattern} title="Draw the base-station array pattern lobe.">
          Show array pattern
        </Checkbox>
        <FieldLabel title="Visible radius of the array pattern lobe. The panel is ~14 m from the body so the true lobe is tiny; this is a display size, not the physical beamwidth.">
          Pattern size
        </FieldLabel>
        <Slider
          value={arrayPatternSizeM}
          min={0.6}
          max={6}
          step={0.2}
          onChange={setArrayPatternSizeM}
          disabled={!showArrayPattern}
          labelOf={(v) => `${v.toFixed(1)} m`}
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
        <Checkbox
          checked={showBeamAxis}
          onChange={setShowBeamAxis}
          title="Draw the dashed base-station to focus beam axis and its range / downtilt label (working dark view only)."
        >
          Beam axis
        </Checkbox>
        <Checkbox
          checked={showGizmo}
          onChange={setShowGizmo}
          title="Show the slice's drag gizmo (the RGB axis triad). Turn off for an unobstructed view; it is always hidden in screenshot mode."
        >
          Slice gizmo
        </Checkbox>
        <Checkbox
          checked={showRefSquare}
          onChange={setShowRefSquare}
          title="Draw the 4 cm² (2 cm x 2 cm) ICNIRP spatial-averaging reference square on the slice at the focus."
        >
          Reference square (4 cm²)
        </Checkbox>
      </Group>

      <Group title="Scene & capture" active={screenshotMode}>
        <FieldLabel title="Free orbit lets you move the camera. BS axis parks it looking down the beam and follows the focus.">
          Camera view
        </FieldLabel>
        <Segmented<StudioCameraView> value={cameraView} options={CAMERA_OPTIONS} onChange={setCameraView} />
        <Checkbox
          checked={showBlockers}
          onChange={setShowBlockers}
          title="Draw the real traced factory blockers: metallic scatterer cuboids, plus the NLOS corridor slab (semi-transparent) in the NLOS condition."
        >
          Show blockers
        </Checkbox>
        <FieldLabel title="Scene backdrop for the working view. The room outline is always drawn (black on white, white on dark).">Background</FieldLabel>
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

      <Group title="Field volume (3D)" defaultCollapsed active={showVolume}>
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

      <Group title="Distribution" defaultCollapsed>
        <StudioExposureHistogram />
      </Group>

      <Group title="Line probe" defaultCollapsed>
        <StudioLineProfile />
      </Group>

      <Group title="Falloff" defaultCollapsed>
        <StudioRadialFalloff />
      </Group>

      <Group title="Array pattern" defaultCollapsed>
        <StudioPatternCut />
      </Group>

      <Group title="A/B compare" defaultCollapsed>
        <StudioCompare />
      </Group>
    </div>
  )
}
