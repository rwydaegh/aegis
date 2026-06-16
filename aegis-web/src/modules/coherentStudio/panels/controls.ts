import type { SlicePlane, StudioFieldQuantity, StudioManifest, StudioPacks, StudioPlaneOrientation, Vec3 } from '../api'

// ---------------------------------------------------------------------------
// Pure (no React, no DOM) helpers backing the studio control surface. Kept in a
// standalone module so the pack-availability and extent-label logic can be unit
// tested in the node vitest env.
// ---------------------------------------------------------------------------

const EMPTY_PACKS: StudioPacks = { rays: [], phantom: [], bodymaps: [], ensemble: [], qop: [], channel: [] }

/** Read the typed pack lists off the manifest, tolerating a missing manifest. */
export function packsOf(manifest: StudioManifest | null): StudioPacks {
  const p = manifest?.packs
  if (!p || typeof p !== 'object') return EMPTY_PACKS
  // Cast through unknown: the backend is trusted to send a dict, but tolerate
  // missing / malformed keys defensively rather than assuming all the lists.
  const o = p as unknown as Record<string, unknown>
  const list = (v: unknown): string[] => (Array.isArray(v) ? (v.filter((x) => typeof x === 'string') as string[]) : [])
  return {
    rays: list(o.rays),
    phantom: list(o.phantom),
    bodymaps: list(o.bodymaps),
    ensemble: list(o.ensemble),
    qop: list(o.qop),
    channel: list(o.channel),
  }
}

// Backend pack-stem conventions (see routes/studio/_paths.py and _bodymap.py):
//   ray pack:      bs{arrayN}_{condition}_seed{seed}            (body-independent)
//   body-map pack: {mesh}_{condition}_bs{arrayN}_{quantity}_{freqTag}
//   Q / channel:   {mesh}_{condition}_bs{arrayN}_{freqTag}[...]
// Rays are shared across phantoms; every body-dependent pack carries the mesh
// as a prefix. freqTag mirrors python's f"{float(ghz):g}" (integers print bare).

/** Frequency tag used in body-map pack stems (python `%g` for the GHz value). */
export function freqTag(frequencyGhz: number): string {
  return String(frequencyGhz)
}

/** Ray-pack stem for a (condition, array) at a given seed. */
export function rayPackStem(condition: string, arrayN: number, seed: number): string {
  return `bs${arrayN}_${condition}_seed${seed}`
}

/** Body-map pack stem for a (mesh, condition, array, quantity, frequency). */
export function bodyMapStem(
  mesh: string,
  condition: string,
  arrayN: number,
  quantity: string,
  frequencyGhz: number,
): string {
  return `${mesh}_${condition}_bs${arrayN}_${quantity}_${freqTag(frequencyGhz)}`
}

/**
 * A condition is selectable for the slice if at least one ray pack ships for it
 * at the current array size (any seed). LOS ships today; NLOS packs are produced
 * on demand, so NLOS greys out until its packs exist.
 */
export function conditionHasRayPack(packs: StudioPacks, condition: string, arrayN: number): boolean {
  const prefix = `bs${arrayN}_${condition}_seed`
  return packs.rays.some((s) => s.startsWith(prefix))
}

/**
 * An array size is selectable if a ray pack ships for it at the current
 * condition (any seed). Rays are body-independent, so this gates the array
 * selector the same way conditionHasRayPack gates the condition segmented
 * control, just with the array size as the free variable.
 */
export function arraySizeHasRayPack(packs: StudioPacks, arrayN: number, condition: string): boolean {
  return conditionHasRayPack(packs, condition, arrayN)
}

/** A body-map quantity is selectable if its precomputed pack is present. */
export function bodyMapHasPack(
  packs: StudioPacks,
  mesh: string,
  condition: string,
  arrayN: number,
  quantity: string,
  frequencyGhz: number,
): boolean {
  return packs.bodymaps.includes(bodyMapStem(mesh, condition, arrayN, quantity, frequencyGhz))
}

/** A phantom geometry pack is present for the mesh. */
export function phantomHasPack(packs: StudioPacks, mesh: string): boolean {
  return packs.phantom.includes(mesh)
}

/**
 * Whether an ensemble statistic (mean / p95) pack is present for a given
 * (condition, array, quantity, frequency). Ensemble packs are LOS-only and
 * named `{condition}_bs{n}_{quantity}_{freqTag}_{mean<K>|p95}`; the mean pack
 * carries the seed count K, so match it by prefix. The "single" statistic is
 * always available (it is the default body-map pack, gated by bodyMapHasPack).
 */
export function ensembleHasPack(
  packs: StudioPacks,
  statistic: string,
  mesh: string,
  condition: string,
  arrayN: number,
  quantity: string,
  frequencyGhz: number,
): boolean {
  if (statistic === 'single') return true
  const base = `${mesh}_${condition}_bs${arrayN}_${quantity}_${freqTag(frequencyGhz)}`
  if (statistic === 'p95') return packs.ensemble.includes(`${base}_p95`)
  if (statistic === 'mean') return packs.ensemble.some((s) => s.startsWith(`${base}_mean`))
  return false
}

/**
 * Reconcile the body-map quantity against the live "deposited" map's
 * availability and the user's sticky preference. Returns the quantity to switch
 * TO, or null to leave the current selection untouched.
 *
 * - Live selected but its channel pack is gone -> fall back to 'mrt' (so the
 *   body never greys out on a dead selection), without clearing the preference.
 * - Preference on, currently off the live map, and the channel pack is back ->
 *   promote to 'deposited' so cycling scenarios snaps back to the focus-tracking
 *   map whenever the combo supports it.
 *
 * The two cases are mutually exclusive on `liveAvailable`, so this never
 * ping-pongs.
 */
export function reconcileBodyMapQuantity(args: {
  current: string
  preferDeposited: boolean
  liveAvailable: boolean
}): string | null {
  const { current, preferDeposited, liveAvailable } = args
  const isLive = current === 'deposited'
  if (isLive && !liveAvailable) return 'mrt'
  if (preferDeposited && !isLive && liveAvailable) return 'deposited'
  return null
}

/** Exposure-operator (Q) pack stem for a (mesh, condition, array, frequency). */
export function qopStem(mesh: string, condition: string, arrayN: number, frequencyGhz: number): string {
  return `${mesh}_${condition}_bs${arrayN}_${freqTag(frequencyGhz)}`
}

/**
 * The ECBF beam needs a precomputed exposure operator Q for the current
 * (condition, array, frequency). Q packs ship at the dosimetry frequencies the
 * offline precompute covered (10 and 28 GHz today), so ECBF greys out at the
 * intermediate frequencies until their Q packs exist.
 */
export function qopHasPack(
  packs: StudioPacks,
  mesh: string,
  condition: string,
  arrayN: number,
  frequencyGhz: number,
): boolean {
  return packs.qop.includes(qopStem(mesh, condition, arrayN, frequencyGhz))
}

/** Field-channel pack stem for a (mesh, condition, array, frequency, seed). */
export function channelStem(
  mesh: string,
  condition: string,
  arrayN: number,
  frequencyGhz: number,
  seed: number,
): string {
  return `${mesh}_${condition}_bs${arrayN}_${freqTag(frequencyGhz)}_seed${seed}`
}

/**
 * The live ("deposited") body map needs a precomputed field channel for the
 * current (condition, array, frequency, seed). Channel packs ship at the
 * dosimetry frequencies and seeds the offline precompute covered, so the live
 * map greys out elsewhere until those packs exist.
 */
export function channelHasPack(
  packs: StudioPacks,
  mesh: string,
  condition: string,
  arrayN: number,
  frequencyGhz: number,
  seed: number,
): boolean {
  return packs.channel.includes(channelStem(mesh, condition, arrayN, frequencyGhz, seed))
}

/**
 * Whether a beam can be computed for the current scenario. Every beam needs the
 * condition's ray pack; ECBF additionally needs the exposure-operator (Q) pack
 * at this frequency (it solves the QCQP against the precomputed operator).
 */
export function beamAvailability(
  packs: StudioPacks,
  beam: string,
  mesh: string,
  condition: string,
  arrayN: number,
  frequencyGhz: number,
): { available: boolean; hint?: string } {
  if (!conditionHasRayPack(packs, condition, arrayN)) return { available: false, hint: 'no ray pack' }
  if (beam === 'ecbf' && !qopHasPack(packs, mesh, condition, arrayN, frequencyGhz)) {
    return { available: false, hint: 'no Q pack at this freq' }
  }
  return { available: true }
}

// ---------------------------------------------------------------------------
// Beam catalogue. Every beam is wired end to end (the backend synthesizes the
// precoder / field for each); a beam greys out only when its precomputed packs
// are absent for the current scenario (see beamAvailability).
// ---------------------------------------------------------------------------

export interface BeamOption {
  value: string
  label: string
  /** Plain-language explanation of the precoder this beam synthesises. */
  title: string
}

// Definitions are code-grounded (src/aegis/viewer/routes/studio/_precoders.py and
// src/aegis/coherent/ecbf.py). The precoder x is normalised to unit transmit
// power for every beam except ECBF, which may sit below it.
const BEAM_CATALOGUE: BeamOption[] = [
  {
    value: 'mrt',
    label: 'MRT (focused)',
    title:
      'Maximum-ratio transmission, the realistic communication beam. Conjugate-matches the channel to put the strongest signal at the focus (x = conj(h)/||h||). This is the operating point a base station would actually use.',
  },
  {
    value: 'unfocused',
    label: 'Unfocused',
    title:
      'Equal power per element with independent random phases. No focusing at all, just diffuse illumination of the region at the same total transmit power. A no-beamforming baseline.',
  },
  {
    value: 'worstcase',
    label: 'Worst case',
    title:
      'The single unit-power beam that maximises absorbed power density at the focus (field intensity in free space). An absolute upper bound no real beam exceeds at that point, not a beam anyone deploys. It is the top eigenvector of the local channel.',
  },
  {
    value: 'decohered',
    label: 'Decohered',
    title:
      'The MRT beam with each arrival direction phase-scrambled. The same multipath power still lights the body, but the wavefront alignment that builds the hotspot is gone, so the field falls to the incoherent floor. Shows what coherent focusing adds. The live deposited body map is not available for this beam.',
  },
  {
    value: 'decoy',
    label: 'Decoy',
    title:
      'A matched-ratio beam focused 6 cm above the target. Still a tight coherent hotspot, just aimed at the wrong place. Shows how sharply the focus localises and how fast exposure drops when mis-aimed. The opposite of decohered: focus elsewhere, vs no focus anywhere.',
  },
  {
    value: 'ecbf',
    label: 'ECBF',
    title:
      'Exposure-constrained beamformer. Maximises received signal subject to a cap on total absorbed power (max |h^T x|^2 s.t. x^H Q x <= budget). The compliant beam: keep the link strong while holding whole-body absorption under a budget. Set the cap with the budget slider.',
  },
]

/** Plain-language explanation for a beam value (falls back to the value). */
export function beamDescription(value: string): string {
  return BEAM_CATALOGUE.find((b) => b.value === value)?.title ?? value
}

/** Beam options to show, ordered, restricted to those the manifest advertises. */
export function beamOptions(manifest: StudioManifest | null): BeamOption[] {
  const advertised = manifest?.beams
  if (!advertised || advertised.length === 0) return BEAM_CATALOGUE
  const known = new Set(BEAM_CATALOGUE.map((b) => b.value))
  const extra = advertised.filter((v) => !known.has(v)).map((v) => ({ value: v, label: v, title: v }))
  return [...BEAM_CATALOGUE.filter((b) => advertised.includes(b.value)), ...extra]
}

// ---------------------------------------------------------------------------
// Field-quantity catalogue (the slice). The backend reconstructs the coherent
// field on the plane and reduces it to the requested scalar. The signed real
// components (ReEx/y/z) read best on a diverging colour map (a follow-up; the
// current viridis LUT still renders them, just not centred on zero). Sab is a
// per-triangle surface quantity, so it is served by the body-map endpoint, not
// the free-space slice.
// ---------------------------------------------------------------------------

export interface FieldQuantityOption {
  value: StudioFieldQuantity
  label: string
  title: string
}

// Reductions of the synthesised complex E-field phasor on the plane
// (src/aegis/viewer/routes/studio/_slice.py).
export const FIELD_QUANTITY_OPTIONS: FieldQuantityOption[] = [
  {
    value: 'S',
    label: 'Power density |E|²',
    title: 'Time-averaged power density S = |E|^2 / (2 Z0), in W/m^2. Note this is not |E|^2 itself.',
  },
  { value: 'absE', label: 'Field magnitude |E|', title: 'Electric field magnitude ||E|| (vector 2-norm of the complex field), in V/m.' },
  { value: 'absH', label: 'Field magnitude |H|', title: 'Magnetic field magnitude ||H||, in A/m, from the plane-wave relation H = (k x E)/Z0.' },
  {
    value: 'poynting',
    label: 'Poynting |Re(E×H*)|/2',
    title:
      'Magnitude of the active (time-averaged) power-flow vector |Re(E x H*)|/2, in W/m^2. Differs from S where reactive standing-wave field exists.',
  },
  { value: 'ReEx', label: 'Re(Eₓ)', title: 'Signed real part of the world-x E-field component, in V/m. Shown on a diverging scale about zero.' },
  { value: 'ReEy', label: 'Re(E_y)', title: 'Signed real part of the world-y E-field component, in V/m. Shown on a diverging scale about zero.' },
  { value: 'ReEz', label: 'Re(E_z)', title: 'Signed real part of the world-z E-field component, in V/m. Shown on a diverging scale about zero.' },
]

// ---------------------------------------------------------------------------
// Slice plane controls.
// ---------------------------------------------------------------------------

/** Selectable plane extents (metres), labelled in cm up to ~2.56 m. */
export const EXTENT_OPTIONS_M = [0.04, 0.08, 0.16, 0.4, 0.8, 1.6, 2.56] as const

/**
 * Human label for a plane extent in metres: centimetres below 1 m, metres above.
 * 0.04 -> "4 cm", 0.4 -> "40 cm", 1.6 -> "1.6 m", 2.56 -> "2.56 m".
 */
export function extentLabel(extentM: number): string {
  if (extentM < 1) return `${Math.round(extentM * 100)} cm`
  return `${parseFloat(extentM.toFixed(2))} m`
}

export interface ResolutionOption {
  value: number
  label: string
}

export const RESOLUTION_OPTIONS: ResolutionOption[] = [
  { value: 160, label: 'Fast (160)' },
  { value: 320, label: 'Crisp (320)' },
]

// Slice-plane orientation presets. The phantom is placed axis-aligned in the
// world frame (feet at z=0, facing -x toward the base station, up is +z), so the
// anatomical planes map to fixed world-axis normals through the focus and are
// exactly reproducible. They are sent to the backend as orientation 'free' with
// that normal, so they never depend on the oblique beam axis (unlike the old
// 'transverse'/'axial', which were beam-relative and only "kind of" axis-aligned).
// 'facing-bs' keeps the genuinely beam-defined wavefront plane, honestly labelled.
export interface OrientationOption {
  value: string
  label: string
  title: string
}

export const ORIENTATION_OPTIONS: OrientationOption[] = [
  {
    value: 'horizontal',
    label: 'Horizontal (transverse)',
    title: 'Level cut through the focus, normal along world up (+Z). The anatomical transverse plane: shows the hotspot spread at one height.',
  },
  {
    value: 'coronal',
    label: 'Coronal (frontal)',
    title: 'Front-facing cut, normal along +X (toward the base station). Contains up and left-right, shows the hotspot across the chest as the array sees it.',
  },
  {
    value: 'sagittal',
    label: 'Sagittal',
    title: 'Front-to-back cut, normal along +Y. Contains up and the base-station axis, shows beam penetration depth versus height.',
  },
  {
    value: 'facing-bs',
    label: 'Facing base station',
    title: 'Plane perpendicular to the beam (focus toward the base station), the wavefront plane. Tilted off the world axes by the array downtilt, so it is deliberately not axis-aligned.',
  },
  {
    value: 'free',
    label: 'Custom normal',
    title: 'Set the plane normal by hand with the sliders below.',
  },
]

// World-axis normals for the anatomical planes (server Z-up frame).
const ORIENTATION_NORMAL: Record<string, Vec3> = {
  horizontal: [0, 0, 1],
  coronal: [1, 0, 0],
  sagittal: [0, 1, 0],
}

/** Is a (possibly unnormalised) normal aligned with an axis (either sign)? */
function alignedWith(n: Vec3, axis: Vec3): boolean {
  const len = Math.hypot(n[0], n[1], n[2])
  if (len < 1e-9) return false
  const d = (n[0] * axis[0] + n[1] * axis[1] + n[2] * axis[2]) / len
  return Math.abs(d) > 0.999
}

/** The plane-state patch a preset selection produces (kept fork-free: every
 * anatomical plane is a 'free' plane with a fixed world-axis normal). */
export function orientationPatch(key: string): Partial<SlicePlane> {
  if (key === 'facing-bs') return { orientation: 'transverse' as StudioPlaneOrientation }
  if (key === 'free') return { orientation: 'free' as StudioPlaneOrientation }
  const normal = ORIENTATION_NORMAL[key]
  return { orientation: 'free' as StudioPlaneOrientation, normalXyz: normal ?? [0, 1, 0] }
}

/** Which preset key the current plane state corresponds to (for the dropdown). */
export function activeOrientationKey(orientation: string, normalXyz: Vec3 | null): string {
  if (orientation === 'transverse') return 'facing-bs'
  if (orientation !== 'free' || !normalXyz) return 'free'
  for (const key of Object.keys(ORIENTATION_NORMAL)) {
    if (alignedWith(normalXyz, ORIENTATION_NORMAL[key])) return key
  }
  return 'free'
}

/** Plain-language explanation for an orientation preset key. */
export function orientationDescription(key: string): string {
  return ORIENTATION_OPTIONS.find((o) => o.value === key)?.title ?? ''
}

// ---------------------------------------------------------------------------
// Provenance summary for the HUD dot. Combines the live-computed slice with the
// served / not-precomputed body map into a single confidence + title.
// ---------------------------------------------------------------------------

export interface FrameProvenance {
  confidence: number
  label: string
  title: string
}

function provenanceTag(provenance: unknown): string | null {
  if (typeof provenance === 'string') return provenance
  if (provenance && typeof provenance === 'object') {
    const o = provenance as Record<string, unknown>
    for (const key of ['kind', 'source', 'origin', 'tag']) {
      if (typeof o[key] === 'string') return o[key] as string
    }
  }
  return null
}

/**
 * Summarise the current frame's data source for the provenance dot.
 *
 * - A served body-map pack is the highest-confidence, fully-precomputed frame.
 * - A selected body-map quantity with no pack is "not precomputed" (low).
 * - The slice itself is computed live from the ray pack on every parameter
 *   change; that is mid confidence (real physics, but not a cached golden).
 */
export function frameProvenance(args: {
  sliceProvenance: unknown
  hasBodyMap: boolean
  bodyMapNotPrecomputed: boolean
}): FrameProvenance {
  const { sliceProvenance, hasBodyMap, bodyMapNotPrecomputed } = args
  const sliceTag = provenanceTag(sliceProvenance)

  if (hasBodyMap) {
    return {
      confidence: 0.9,
      label: 'precomputed',
      title: 'Body map served from a precomputed pack; slice computed live from the ray pack',
    }
  }
  if (bodyMapNotPrecomputed) {
    return {
      confidence: 0.2,
      label: 'not precomputed',
      title: 'No precomputed body-map pack for this combination; only the live slice is shown',
    }
  }
  return {
    confidence: 0.6,
    label: 'live',
    title: sliceTag
      ? `Slice computed live (${sliceTag})`
      : 'Slice computed live from the ray pack',
  }
}
