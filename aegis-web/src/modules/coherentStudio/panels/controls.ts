import type { StudioFieldQuantity, StudioManifest, StudioPacks } from '../api'

// ---------------------------------------------------------------------------
// Pure (no React, no DOM) helpers backing the studio control surface. Kept in a
// standalone module so the pack-availability and extent-label logic can be unit
// tested in the node vitest env.
// ---------------------------------------------------------------------------

const EMPTY_PACKS: StudioPacks = { rays: [], phantom: [], bodymaps: [], ensemble: [] }

/** Read the typed pack lists off the manifest, tolerating a missing manifest. */
export function packsOf(manifest: StudioManifest | null): StudioPacks {
  const p = manifest?.packs
  if (!p || typeof p !== 'object') return EMPTY_PACKS
  // Cast through unknown: the backend is trusted to send a dict, but tolerate
  // missing / malformed keys defensively rather than assuming all four lists.
  const o = p as unknown as Record<string, unknown>
  const list = (v: unknown): string[] => (Array.isArray(v) ? (v.filter((x) => typeof x === 'string') as string[]) : [])
  return {
    rays: list(o.rays),
    phantom: list(o.phantom),
    bodymaps: list(o.bodymaps),
    ensemble: list(o.ensemble),
  }
}

// Backend pack-stem conventions (see routes/studio/_paths.py and _bodymap.py):
//   ray pack:      bs{arrayN}_{condition}_seed{seed}
//   body-map pack: {condition}_bs{arrayN}_{quantity}_{freqTag}
// where freqTag mirrors python's f"{float(ghz):g}" (integers print bare).

/** Frequency tag used in body-map pack stems (python `%g` for the GHz value). */
export function freqTag(frequencyGhz: number): string {
  return String(frequencyGhz)
}

/** Ray-pack stem for a (condition, array) at a given seed. */
export function rayPackStem(condition: string, arrayN: number, seed: number): string {
  return `bs${arrayN}_${condition}_seed${seed}`
}

/** Body-map pack stem for a (condition, array, quantity, frequency). */
export function bodyMapStem(
  condition: string,
  arrayN: number,
  quantity: string,
  frequencyGhz: number,
): string {
  return `${condition}_bs${arrayN}_${quantity}_${freqTag(frequencyGhz)}`
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

/** A body-map quantity is selectable if its precomputed pack is present. */
export function bodyMapHasPack(
  packs: StudioPacks,
  condition: string,
  arrayN: number,
  quantity: string,
  frequencyGhz: number,
): boolean {
  return packs.bodymaps.includes(bodyMapStem(condition, arrayN, quantity, frequencyGhz))
}

// ---------------------------------------------------------------------------
// Beam catalogue. Phase 1 wires the focused / unfocused / worst-case precoders;
// the decohered / decoy / ECBF beams exist in the backend but are Phase 2, so we
// surface them disabled with a hint rather than hiding them.
// ---------------------------------------------------------------------------

export interface BeamOption {
  value: string
  label: string
  phase2: boolean
}

const BEAM_CATALOGUE: BeamOption[] = [
  { value: 'mrt', label: 'MRT (focused)', phase2: false },
  { value: 'unfocused', label: 'Unfocused', phase2: false },
  { value: 'worstcase', label: 'Worst case', phase2: false },
  { value: 'decohered', label: 'Decohered', phase2: true },
  { value: 'decoy', label: 'Decoy', phase2: true },
  { value: 'ecbf', label: 'ECBF', phase2: true },
]

/** Beam options to show, ordered, restricted to those the manifest advertises. */
export function beamOptions(manifest: StudioManifest | null): BeamOption[] {
  const advertised = manifest?.beams
  if (!advertised || advertised.length === 0) return BEAM_CATALOGUE
  const known = new Set(BEAM_CATALOGUE.map((b) => b.value))
  const extra = advertised
    .filter((v) => !known.has(v))
    .map((v) => ({ value: v, label: v, phase2: true }))
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
}

export const FIELD_QUANTITY_OPTIONS: FieldQuantityOption[] = [
  { value: 'S', label: 'Power density |E|²' },
  { value: 'absE', label: 'Field magnitude |E|' },
  { value: 'absH', label: 'Field magnitude |H|' },
  { value: 'poynting', label: 'Poynting |Re(E×H*)|/2' },
  { value: 'ReEx', label: 'Re(Eₓ)' },
  { value: 'ReEy', label: 'Re(E_y)' },
  { value: 'ReEz', label: 'Re(E_z)' },
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

export const ORIENTATION_OPTIONS: { value: 'transverse' | 'axial' | 'free'; label: string }[] = [
  { value: 'transverse', label: 'Transverse' },
  { value: 'axial', label: 'Axial' },
  { value: 'free', label: 'Free' },
]

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
