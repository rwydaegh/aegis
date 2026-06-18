import {
  ApiError,
  fetchWithRetry,
  handle401,
  parseJsonHeader,
} from '@/api/client'

// Studio endpoints live under /api/studio. The dev server proxies /api to the
// Flask backend (see vite.config.ts), so a relative base is correct in both dev
// and production (where Flask serves the built bundle from /).
const BASE = ''
const STUDIO = '/api/studio'

// ---------------------------------------------------------------------------
// Parameter / value types (mirror the store and the backend contract)
// ---------------------------------------------------------------------------

export type StudioFocusMode = 'at-skin' | 'free-space'
export type StudioFieldQuantity = 'S' | 'absE' | 'ReEx' | 'ReEy' | 'ReEz' | 'absH' | 'poynting'
export type StudioPlaneOrientation = 'transverse' | 'axial' | 'free'

/** Server-side (Z-up, metres) 3-vector. */
export type Vec3 = [number, number, number]

/** Opaque provenance blob returned by the backend (string tag or JSON object). */
export type Provenance = unknown

/** Total radiated power in watts from a dBm reading (P[W] = 10^((dBm-30)/10)). */
export function dbmToWatts(dbm: number): number {
  return Math.pow(10, (dbm - 30) / 10)
}

/** ECBF constraint-mode fields shared by every precoder-bearing request. In
 * relative mode (default) they are inert; in absolute mode they select the
 * ICNIRP restrictions and the literal transmit power the QCQP is solved at. */
export interface EcbfConstraintParams {
  /** 'relative' (budget-fraction ECBF, default) or 'absolute' (ICNIRP limits). */
  constraintMode?: string
  /** Enforce the whole-body SAR restriction (absolute mode). */
  sarWbOn?: boolean
  /** Enforce the peak 4 cm^2 S_ab restriction (absolute mode, above 6 GHz). */
  peakSabOn?: boolean
  /** Absolute transmit power in watts the absolute solve uses for ||x||^2 <= P. */
  txPowerW?: number
}

/** Snake-case request body for the ECBF constraint fields, with defaults that
 * reproduce the existing relative-mode behaviour when the caller omits them. */
function ecbfConstraintBody(p: EcbfConstraintParams): Record<string, unknown> {
  return {
    constraint_mode: p.constraintMode ?? 'relative',
    sar_wb_on: p.sarWbOn ?? true,
    peak_sab_on: p.peakSabOn ?? true,
    tx_power_w: p.txPowerW ?? 1.0,
  }
}

/** General-public ICNIRP 2020 basic restrictions at a frequency, for the
 * client-side utilisation bars in relative mode (the backend echoes the same
 * values in absolute mode). The 4 cm^2 S_ab limit only exists above 6 GHz. */
export function icnirpLimits(freqGhz: number): { sarWb: number; sab4cm2: number | null } {
  return { sarWb: 0.08, sab4cm2: freqGhz > 6 ? 20.0 : null }
}

// ---------------------------------------------------------------------------
// Manifest
// ---------------------------------------------------------------------------

/**
 * Precomputed packs present in the studio data dir, keyed by pack kind. The
 * backend (`routes/studio/_config.py::available_packs`) returns a dict of pack
 * kind -> sorted list of pack stems (filenames without the `.npz` suffix), not
 * a flat array.
 */
export interface StudioPacks {
  rays: string[]
  phantom: string[]
  bodymaps: string[]
  ensemble: string[]
  /** Exposure-operator (Q) pack stems, e.g. `los_bs16_10`. Gates the ECBF beam. */
  qop: string[]
  /** Field-channel pack stems, e.g. `los_bs16_10_seed0`. Gates the live body map. */
  channel: string[]
}

export interface StudioManifest {
  phantoms: string[]
  conditions: string[]
  frequencies: number[]
  seeds: number[]
  array_sizes: number[]
  beams: string[]
  /** Per-triangle body-map quantities the backend can serve (floor, mrt, ...). */
  body_map_quantities: string[]
  /** Body-map realisation statistics (single, mean, p95). */
  body_map_statistics?: string[]
  /** Corridor UE standing positions the body can occupy (indices 0..8). */
  ue_indices?: number[]
  /** Default corridor UE index (mid-corridor, 14 m; its packs are unsuffixed). */
  default_ue_idx?: number
  /** Per-element transmit power the packs were traced at (dBm); also the total
   * array power the ||x||^2 = 1 outputs are calibrated to. The Tx-power slider
   * rescales absolute quantities from here. */
  calibration_tx_power_dbm?: number
  /** Total transmit power [W] the absolute outputs are calibrated to (= 10^((dBm-30)/10)). */
  calibration_power_w?: number
  /**
   * Precomputed pack descriptors. The backend manifest returns these under the
   * key `packs` (verified against routes/studio/_presets.py::manifest).
   */
  packs: StudioPacks
  /** Canonical opening scene; shape is backend-defined (snake_case keys). */
  default_scene: Record<string, unknown>
}

// ---------------------------------------------------------------------------
// Rays
// ---------------------------------------------------------------------------

export interface RaysParams {
  condition: string
  arrayN: number
  seed: number
  topK?: number
  /** Corridor standing position of the body (UE index 0..8; default 4). */
  ueIdx?: number
}

export interface RaysResponse {
  /** Incoming ray directions, Z-up unit vectors. */
  directions: Vec3[]
  /** Per-ray power (linear, descending). */
  power: number[]
  /** Propagation direction k_hat, Z-up unit vectors. */
  k_hat: Vec3[]
}

// ---------------------------------------------------------------------------
// Slice (field plane)
// ---------------------------------------------------------------------------

export interface SlicePlane {
  orientation: StudioPlaneOrientation
  /** Plane normal for orientation 'free'; null for the canned orientations. */
  normalXyz: Vec3 | null
  extentM: number
  res: number
}

export interface SliceParams extends EcbfConstraintParams {
  mesh: string
  condition: string
  arrayN: number
  seed: number
  beam: string
  focusMode: StudioFocusMode
  focusXyz: Vec3
  frequencyGhz: number
  plane: SlicePlane
  quantity: StudioFieldQuantity
  /** ECBF absorbed-power budget as a fraction of MRT; only used when beam=ecbf. */
  ecbfBudgetFrac?: number
  /** UE receive antenna pattern; shapes the matched-filter precoder. */
  ueAntenna?: string
  /** Corridor standing position of the body (UE index 0..8; default 4). */
  ueIdx?: number
}

/** World-space frame of the returned scalar grid (all Z-up metres). */
export interface SliceWorld {
  center: Vec3
  e1: Vec3
  e2: Vec3
  /** Physical plane size as [width along e1, height along e2], metres. */
  extent: [number, number]
}

export interface SliceResult {
  /** Row-major float32 scalar grid, length shape[0] * shape[1]. */
  scalar: Float32Array
  shape: [number, number]
  world: SliceWorld
  vmin: number
  vmax: number
  units: string
  peakXyz: Vec3
  peakValue: number
  provenance: Provenance
  quantity: StudioFieldQuantity
}

/** Raw X-Stats header schema for the /slice endpoint. */
interface SliceStatsHeader {
  shape: [number, number]
  world: SliceWorld
  vmin: number
  vmax: number
  units: string
  peak_xyz: Vec3
  peak_value: number
  provenance: Provenance
  quantity: StudioFieldQuantity
}

// ---------------------------------------------------------------------------
// Field volume (3D box)
// ---------------------------------------------------------------------------

export interface VolumeParams extends EcbfConstraintParams {
  mesh: string
  condition: string
  arrayN: number
  seed: number
  beam: string
  focusMode: StudioFocusMode
  focusXyz: Vec3
  frequencyGhz: number
  /** Full cube side length, metres (clamped server-side to [1e-3, 3]). */
  extentM: number
  /** Per-axis sample count (clamped server-side to [8, 48]). */
  res: number
  /** ECBF budget as a fraction of MRT; only used when beam=ecbf. */
  ecbfBudgetFrac?: number
  /** UE receive antenna pattern; shapes the matched-filter precoder. */
  ueAntenna?: string
  /** Corridor standing position of the body (UE index 0..8; default 4). */
  ueIdx?: number
}

export interface VolumeResult {
  /** Row-major float32 grid, indexed [i, j, k] (i->x, j->y, k->z), length nx*ny*nz. */
  scalar: Float32Array
  shape: [number, number, number]
  /** Min-corner voxel centre, server Z-up metres. */
  origin: Vec3
  /** Isotropic voxel pitch, metres. */
  spacing: number
  vmin: number
  vmax: number
  units: string
  peakXyz: Vec3
  peakValue: number
  provenance: Provenance
  quantity: string
}

interface VolumeStatsHeader {
  shape: [number, number, number]
  origin: Vec3
  spacing: number
  vmin: number
  vmax: number
  units: string
  peak_xyz: Vec3
  peak_value: number
  provenance: Provenance
  quantity: string
}

function volumePayload(params: VolumeParams) {
  return {
    mesh: params.mesh,
    condition: params.condition,
    array_n: params.arrayN,
    seed: params.seed,
    beam: params.beam,
    focus_mode: params.focusMode,
    focus_xyz: params.focusXyz,
    frequency_ghz: params.frequencyGhz,
    extent_m: params.extentM,
    res: params.res,
    ecbf_budget_frac: params.ecbfBudgetFrac ?? 0.5,
    ...ecbfConstraintBody(params),
    ue_antenna: params.ueAntenna ?? 'dipole',
    ue_idx: params.ueIdx ?? 4,
  }
}

export async function fetchVolume(params: VolumeParams, signal?: AbortSignal): Promise<VolumeResult> {
  const path = `${STUDIO}/volume`
  const res = await fetchWithRetry(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(volumePayload(params)),
    signal,
  })
  if (res.status === 401) {
    handle401()
    throw new ApiError(`POST ${path} failed: 401 Unauthorized`, 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'POST', path), res.status)

  const stats = parseJsonHeader<VolumeStatsHeader>(res.headers.get('X-Stats'), 'X-Stats')
  const buffer = await res.arrayBuffer()
  const scalar = new Float32Array(buffer)

  return {
    scalar,
    shape: stats.shape,
    origin: stats.origin,
    spacing: stats.spacing,
    vmin: stats.vmin,
    vmax: stats.vmax,
    units: stats.units,
    peakXyz: stats.peak_xyz,
    peakValue: stats.peak_value,
    provenance: stats.provenance,
    quantity: stats.quantity,
  }
}

// ---------------------------------------------------------------------------
// Body map
// ---------------------------------------------------------------------------

/** Body-map realisation statistic: a single realisation, or the mean / 95th
 * percentile over the LOS seed ensemble. */
export type StudioBodyMapStatistic = 'single' | 'mean' | 'p95'

export interface BodyMapParams {
  mesh: string
  condition: string
  arrayN: number
  beam: string
  quantity: string
  frequencyGhz: number
  /** Realisation index (the seed / ensemble member). */
  realisation: number
  /** Single realisation (default) or an ensemble statistic over the LOS seeds. */
  statistic?: StudioBodyMapStatistic
}

export interface BodyMapResult {
  /** Per-triangle values, one per phantom face, aligned to the phantom mesh. */
  values: number[]
  vmin: number
  vmax: number
  units: string
  provenance: Provenance
}

/**
 * Discriminated result for the body map: either the data, or a flag that this
 * (condition, array, beam, ...) combo was not precomputed (backend 409).
 */
export type BodyMapFetch =
  | { ok: true; data: BodyMapResult }
  | { ok: false; notPrecomputed: true; error: string }

// ---------------------------------------------------------------------------
// Phantom geometry
// ---------------------------------------------------------------------------

export interface PhantomGeometry {
  /** Non-indexed triangle soup, length nVertices * 3. */
  vertices: Float32Array
  /** Face indices into vertices, length nFaces * 3. */
  faces: Int32Array
  /** Per-triangle centroids, length nFaces * 3. */
  centroids: Float32Array
  /** Per-triangle normals, length nFaces * 3. */
  normals: Float32Array
  nVertices: number
  nFaces: number
}

interface PhantomArrayMeta {
  name: string
  dtype: string
  /** Byte offset into the response buffer. */
  offset: number
  /** Element count (not bytes). */
  length: number
  shape: number[]
}

interface PhantomStatsHeader {
  n_vertices: number
  n_faces: number
  frame: string
  arrays: PhantomArrayMeta[]
}

// ---------------------------------------------------------------------------
// Scene geometry (real factory blockers)
// ---------------------------------------------------------------------------

/** One scatterer cuboid. `size` is (length, width, height) in the server frame;
 * `yaw_rad` rotates it about the server +z (up) axis. */
export interface SceneScatterer {
  center: Vec3
  size: Vec3
  yaw_rad: number
}

/** The NLOS blocker slab. Axis-aligned in the server frame. */
export interface SceneBlocker {
  center: Vec3
  size: Vec3
}

/** Real scene geometry from the traced e8/e11 world (server Z-up metres). */
export interface SceneGeometry {
  room_dims: Vec3
  bs_position: Vec3
  bs_n: number
  bs_tilt_deg: number
  scatterers: SceneScatterer[]
  /** Present only in the NLOS condition. */
  blocker: SceneBlocker | null
  ue_positions: Vec3[]
  provenance: Provenance
}

/** Either the geometry, or a flag that this (condition, seed) was not precomputed. */
export type SceneFetch =
  | { ok: true; data: SceneGeometry }
  | { ok: false; notPrecomputed: true; error: string }

// ---------------------------------------------------------------------------
// Internal helpers (mirror src/api/client.ts patterns)
// ---------------------------------------------------------------------------

async function extractErrorMessage(res: Response, method: string, path: string): Promise<string> {
  const fallback = `${method} ${path} failed: ${res.status} ${res.statusText}`
  try {
    const data = await res.json()
    if (data && typeof data.error === 'string') return data.error
  } catch {
    // Response body is not JSON or is empty
  }
  return fallback
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetchWithRetry(`${BASE}${path}`, signal ? { signal } : undefined)
  if (res.status === 401) {
    handle401()
    throw new ApiError(`GET ${path} failed: 401 Unauthorized`, 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'GET', path), res.status)
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Manifest
// ---------------------------------------------------------------------------

export async function fetchManifest(): Promise<StudioManifest> {
  return getJson<StudioManifest>(`${STUDIO}/manifest`)
}

// ---------------------------------------------------------------------------
// Rays
// ---------------------------------------------------------------------------

export async function fetchRays(params: RaysParams): Promise<RaysResponse> {
  const qs = new URLSearchParams({
    condition: params.condition,
    array_n: String(params.arrayN),
    seed: String(params.seed),
    ue_idx: String(params.ueIdx ?? 4),
  })
  if (params.topK != null) qs.set('top_k', String(params.topK))
  return getJson<RaysResponse>(`${STUDIO}/rays?${qs}`)
}

// ---------------------------------------------------------------------------
// Slice
// ---------------------------------------------------------------------------

function slicePayload(params: SliceParams) {
  return {
    mesh: params.mesh,
    condition: params.condition,
    array_n: params.arrayN,
    seed: params.seed,
    beam: params.beam,
    focus_mode: params.focusMode,
    focus_xyz: params.focusXyz,
    frequency_ghz: params.frequencyGhz,
    plane: {
      orientation: params.plane.orientation,
      normal_xyz: params.plane.normalXyz,
      extent_m: params.plane.extentM,
      res: params.plane.res,
    },
    quantity: params.quantity,
    ecbf_budget_frac: params.ecbfBudgetFrac ?? 0.5,
    ...ecbfConstraintBody(params),
    ue_antenna: params.ueAntenna ?? 'dipole',
    ue_idx: params.ueIdx ?? 4,
  }
}

export async function fetchSlice(params: SliceParams, signal?: AbortSignal): Promise<SliceResult> {
  const path = `${STUDIO}/slice`
  const res = await fetchWithRetry(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(slicePayload(params)),
    signal,
  })
  if (res.status === 401) {
    handle401()
    throw new ApiError(`POST ${path} failed: 401 Unauthorized`, 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'POST', path), res.status)

  const stats = parseJsonHeader<SliceStatsHeader>(res.headers.get('X-Stats'), 'X-Stats')
  const buffer = await res.arrayBuffer()
  const scalar = new Float32Array(buffer)

  return {
    scalar,
    shape: stats.shape,
    world: stats.world,
    vmin: stats.vmin,
    vmax: stats.vmax,
    units: stats.units,
    peakXyz: stats.peak_xyz,
    peakValue: stats.peak_value,
    provenance: stats.provenance,
    quantity: stats.quantity,
  }
}

// ---------------------------------------------------------------------------
// Body map
// ---------------------------------------------------------------------------

/** Params for the live (focus-tracking) body map: the precoder-bearing axes. */
export interface LiveBodyMapParams extends EcbfConstraintParams {
  mesh: string
  condition: string
  arrayN: number
  seed: number
  beam: string
  focusMode: StudioFocusMode
  focusXyz: Vec3
  frequencyGhz: number
  ecbfBudgetFrac?: number
  /** UE receive antenna pattern; shapes the matched-filter precoder. */
  ueAntenna?: string
  /** Corridor standing position of the body (UE index 0..8; default 4). */
  ueIdx?: number
}

/**
 * Live per-triangle deposited S_ab for the current beam + focus, applying the
 * precoder to the precomputed field channel on the backend. Returns the same
 * discriminated shape as fetchBodyMap: a 409 (no channel pack, or a beam the
 * live map cannot express such as decohered) is reported as not-precomputed.
 */
export async function fetchLiveBodyMap(params: LiveBodyMapParams): Promise<BodyMapFetch> {
  const path = `${STUDIO}/bodymap-live`
  const res = await fetchWithRetry(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mesh: params.mesh,
      condition: params.condition,
      array_n: params.arrayN,
      seed: params.seed,
      beam: params.beam,
      focus_mode: params.focusMode,
      focus_xyz: params.focusXyz,
      frequency_ghz: params.frequencyGhz,
      ecbf_budget_frac: params.ecbfBudgetFrac ?? 0.5,
      ...ecbfConstraintBody(params),
      ue_antenna: params.ueAntenna ?? 'dipole',
      ue_idx: params.ueIdx ?? 4,
    }),
  })
  if (res.status === 401) {
    handle401()
    throw new ApiError(`POST ${path} failed: 401 Unauthorized`, 401)
  }
  if (res.status === 409) {
    const body = await res.json().catch(() => ({}))
    return {
      ok: false,
      notPrecomputed: true,
      error: typeof body?.error === 'string' ? body.error : 'Live body map not available for this combination',
    }
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'POST', path), res.status)
  const data = (await res.json()) as BodyMapResult
  return { ok: true, data }
}

// ---------------------------------------------------------------------------
// Compliance scalars (ICNIRP readouts)
// ---------------------------------------------------------------------------

/**
 * ICNIRP compliance scalars for the current beam + focus, all per watt
 * transmitted (the precoders are unit-power). Returned by /api/studio/compliance.
 */
export interface ComplianceResult {
  /** Total absorbed power, W per W transmitted (the absorption fraction). */
  p_abs_w: number
  /** Whole-body SAR = p_abs / body mass, W/kg per W transmitted (null if mass unknown). */
  sar_wb: number | null
  /** 4 cm^2 spatially-averaged peak absorbed power density (psSAR proxy), W/m^2 per W. */
  pssar_4cm2: number
  /** Raw per-triangle peak absorbed power density, W/m^2 per W. */
  peak_sab: number
  /** Area-weighted mean absorbed power density, W/m^2 per W. */
  mean_sab: number
  /** Peak (4 cm^2) over mean absorbed power density (dimensionless). */
  eta_4cm2: number
  /** Served signal relative to the matched-filter (MRT) beam (1.0 = MRT). */
  signal_rel: number
  /** Single-user spectral efficiency log2(1 + SNR_mrt * signal_rel), bit/s/Hz
   * (null if no SNR anchor was requested). The frontend recomputes this live
   * from signal_rel + the SNR knob, so the slider needs no server round-trip. */
  spectral_efficiency_bps_hz: number | null
  /** MRT-reference SNR used to anchor the spectral efficiency, dB (null if none). */
  snr_mrt_db: number | null
  /** Whole-body mass used for SAR_wb, kg (null if unknown). */
  body_mass_kg: number | null
  /** Spatial-averaging area used for psSAR, cm^2 (4.0). */
  averaging_area_cm2: number
  units: Record<string, string>
  provenance?: string

  // --- Absolute-mode fields (present only when constraint_mode === 'absolute') ---
  /** 'relative' (default) or 'absolute'. Selects how the HUD reads the scalars:
   * relative values are per-watt and rescaled client-side; absolute values are
   * already at tx_power_w and come with the regime + per-restriction readout. */
  constraint_mode?: 'relative' | 'absolute'
  /** Which ICNIRP restriction binds the absolute ECBF solution. */
  regime?: 'free' | 'sar_wb' | 'peak_sab' | 'both' | 'infeasible'
  /** Per-restriction utilisation readout (one entry per enforced restriction). */
  per_constraint?: PerConstraint[]
  /** Number of local 4 cm^2 region operators binding at the solution. */
  n_regions_active?: number
  /** Whether the absolute solve converged (constraint generation did not hit the cap). */
  ecbf_converged?: boolean
  /** Absolute transmit power the solve ran at, W. */
  tx_power_w?: number
  /** ICNIRP limit values for the current frequency (sab_4cm2 null at/below 6 GHz). */
  icnirp_limits?: { sar_wb: number; sab_4cm2: number | null; scenario: string }
}

/** One ICNIRP basic restriction at the absolute ECBF solution. */
export interface PerConstraint {
  /** 'sar_wb' (whole-body SAR) or 'peak_sab' (peak 4 cm^2 S_ab). */
  name: 'sar_wb' | 'peak_sab'
  /** The restricted quantity at the solution (W/kg for SAR_wb, W/m^2 for peak). */
  value: number
  /** The ICNIRP limit for this restriction (same unit as value). */
  limit: number
  unit: string
  /** value / limit; >= 1 means the restriction is at or over its limit. */
  utilisation: number | null
  /** True when this restriction binds (sits on its limit) at the solution. */
  active: boolean
}

export type ComplianceFetch =
  | { ok: true; data: ComplianceResult }
  | { ok: false; notPrecomputed: true; error: string }

/** Single-user spectral efficiency from the served-signal ratio and an MRT SNR
 * anchor: R = log2(1 + SNR_mrt * signal_rel). SINR is linear in received signal
 * power, so scaling the MRT operating SNR by signal_rel gives this beam's SNR.
 * Computed client-side so the SNR knob updates the card and chart instantly. */
export function spectralEfficiency(signalRel: number, snrMrtDb: number): number {
  return Math.log2(1 + Math.pow(10, snrMrtDb / 10) * signalRel)
}

/** ECBF compliance scalars swept across the absorbed-power budget (the Pareto
 * front the budget slider rides). Each array is parallel to budget_frac. */
export interface ComplianceSweepResult {
  budget_frac: number[]
  series: {
    p_abs_w: number[]
    sar_wb: (number | null)[]
    pssar_4cm2: number[]
    peak_sab: number[]
    eta_4cm2: number[]
    signal_rel: number[]
    spectral_efficiency_bps_hz: (number | null)[]
  }
  snr_mrt_db: number
  units: Record<string, string>
  provenance?: string
}

export type ComplianceSweepFetch =
  | { ok: true; data: ComplianceSweepResult }
  | { ok: false; notPrecomputed: true; error: string }

/**
 * ECBF compliance scalars swept across the budget (5% to 100%). Independent of
 * the live budget (it covers the whole range), so dragging the slider only moves
 * the cursor on the returned curves; the fetch is keyed on everything else. A 409
 * (no channel / Q pack) is reported as not-precomputed like the compliance route.
 */
export async function fetchComplianceSweep(
  params: LiveBodyMapParams,
  nPoints = 20,
  signal?: AbortSignal,
): Promise<ComplianceSweepFetch> {
  const path = `${STUDIO}/compliance-sweep`
  const res = await fetchWithRetry(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mesh: params.mesh,
      condition: params.condition,
      array_n: params.arrayN,
      seed: params.seed,
      focus_mode: params.focusMode,
      focus_xyz: params.focusXyz,
      frequency_ghz: params.frequencyGhz,
      n_points: nPoints,
      ue_antenna: params.ueAntenna ?? 'dipole',
      ue_idx: params.ueIdx ?? 4,
    }),
    signal,
  })
  if (res.status === 401) {
    handle401()
    throw new ApiError(`POST ${path} failed: 401 Unauthorized`, 401)
  }
  if (res.status === 409) {
    const body = await res.json().catch(() => ({}))
    return {
      ok: false,
      notPrecomputed: true,
      error: typeof body?.error === 'string' ? body.error : 'Budget sweep not available for this combination',
    }
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'POST', path), res.status)
  const data = (await res.json()) as ComplianceSweepResult
  return { ok: true, data }
}

/** Absolute-ICNIRP ECBF vs MRT absorbed power swept across transmit power. The
 * payload of the absolute-mode power chart: ECBF flattens against the fixed
 * ICNIRP limit while MRT diverges. Arrays are parallel to power_dbm / power_w. */
export interface PowerSweepResult {
  /** Swept total transmit power, dBm (the chart X axis). */
  power_dbm: number[]
  /** The same powers in watts. */
  power_w: number[]
  /** Absolute-limit ECBF curves at each power (nulls where a restriction is off
   * or does not apply, e.g. peak S_ab at or below 6 GHz). */
  ecbf: {
    p_abs_w: number[]
    sar_wb: (number | null)[]
    peak_sab: (number | null)[]
    /** Which restriction binds at each power (free / sar_wb / peak_sab / both / infeasible). */
    regime: ComplianceResult['regime'][]
  }
  /** Matched-filter (MRT) reference at the same powers: linear, so it diverges. */
  mrt: {
    p_abs_w: number[]
    sar_wb: (number | null)[]
    peak_sab: number[]
  }
  /** ICNIRP limits plus the absolute whole-body P_abs limit (L_wb * mass, W). */
  limits: { sar_wb: number; sab_4cm2: number | null; scenario: string; p_abs_wb_w: number | null }
  /** Whole-body mass used for the P_abs limit, kg (null if unknown). */
  mass_kg: number | null
  /** Whether each restriction was actually enforced in this sweep. */
  sar_wb_on: boolean
  peak_sab_on: boolean
  provenance?: string
}

export type PowerSweepFetch =
  | { ok: true; data: PowerSweepResult }
  | { ok: false; notPrecomputed: true; error: string }

/**
 * Absolute-ICNIRP ECBF vs MRT absorbed power swept across the transmit-power
 * range (default 0..100 dBm). Independent of the live transmit power (it covers
 * the whole range), so dragging the dBm slider only moves the cursor; the fetch
 * is keyed on everything else, plus which restrictions are enforced. A 409 (no
 * channel pack) is reported as not-precomputed like the compliance route.
 */
export async function fetchPowerSweep(
  params: LiveBodyMapParams,
  nPoints = 18,
  signal?: AbortSignal,
): Promise<PowerSweepFetch> {
  const path = `${STUDIO}/power-sweep`
  const res = await fetchWithRetry(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mesh: params.mesh,
      condition: params.condition,
      array_n: params.arrayN,
      seed: params.seed,
      focus_mode: params.focusMode,
      focus_xyz: params.focusXyz,
      frequency_ghz: params.frequencyGhz,
      n_points: nPoints,
      sar_wb_on: params.sarWbOn ?? true,
      peak_sab_on: params.peakSabOn ?? true,
      ue_antenna: params.ueAntenna ?? 'dipole',
      ue_idx: params.ueIdx ?? 4,
    }),
    signal,
  })
  if (res.status === 401) {
    handle401()
    throw new ApiError(`POST ${path} failed: 401 Unauthorized`, 401)
  }
  if (res.status === 409) {
    const body = await res.json().catch(() => ({}))
    return {
      ok: false,
      notPrecomputed: true,
      error: typeof body?.error === 'string' ? body.error : 'Power sweep not available for this combination',
    }
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'POST', path), res.status)
  const data = (await res.json()) as PowerSweepResult
  return { ok: true, data }
}

/**
 * ICNIRP compliance scalars for the current beam + focus. Same precoder-bearing
 * parameter shape as the live body map. A 409 (no channel / Q pack, or a beam
 * with no per-element precoder such as decohered) is reported as not-precomputed,
 * so the panel greys out the same way the live map does.
 */
export async function fetchCompliance(params: LiveBodyMapParams, signal?: AbortSignal): Promise<ComplianceFetch> {
  const path = `${STUDIO}/compliance`
  const res = await fetchWithRetry(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mesh: params.mesh,
      condition: params.condition,
      array_n: params.arrayN,
      seed: params.seed,
      beam: params.beam,
      focus_mode: params.focusMode,
      focus_xyz: params.focusXyz,
      frequency_ghz: params.frequencyGhz,
      ecbf_budget_frac: params.ecbfBudgetFrac ?? 0.5,
      ...ecbfConstraintBody(params),
      ue_antenna: params.ueAntenna ?? 'dipole',
      ue_idx: params.ueIdx ?? 4,
    }),
    signal,
  })
  if (res.status === 401) {
    handle401()
    throw new ApiError(`POST ${path} failed: 401 Unauthorized`, 401)
  }
  if (res.status === 409) {
    const body = await res.json().catch(() => ({}))
    return {
      ok: false,
      notPrecomputed: true,
      error: typeof body?.error === 'string' ? body.error : 'Compliance metrics not available for this combination',
    }
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'POST', path), res.status)
  const data = (await res.json()) as ComplianceResult
  return { ok: true, data }
}

// ---------------------------------------------------------------------------
// Precoder (transmit radiation pattern)
// ---------------------------------------------------------------------------

export interface PrecoderResult {
  /** False for beams with no per-element precoder (e.g. decohered). */
  available: boolean
  reason?: string
  beam?: string
  /** Elements per row / column of the URA (square here). */
  n_h?: number
  n_v?: number
  /** Panel horizontal / panel-up unit axes in the server (Z-up) frame. */
  axis_h?: Vec3
  axis_v?: Vec3
  /** Inter-element spacing [m] and physical panel carrier [Hz]. */
  spacing_m?: number
  freq_hz?: number
  /** Per-element complex weights, element order k = a*n_h + b (a row, b col). */
  real?: number[]
  imag?: number[]
  provenance?: string
}

export type PrecoderFetch =
  | { ok: true; data: PrecoderResult }
  | { ok: false; notPrecomputed: boolean; error: string }

/**
 * Synthesised precoder x + array geometry for the current beam + focus, so the
 * frontend can draw the realised transmit radiation pattern. Same parameter
 * shape as the live body map. A 409 (missing Q pack for ECBF) is reported as
 * not-precomputed; a beam with no per-element precoder returns available=false.
 */
export async function fetchPrecoder(params: LiveBodyMapParams, signal?: AbortSignal): Promise<PrecoderFetch> {
  const path = `${STUDIO}/precoder`
  const res = await fetchWithRetry(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mesh: params.mesh,
      condition: params.condition,
      array_n: params.arrayN,
      seed: params.seed,
      beam: params.beam,
      focus_mode: params.focusMode,
      focus_xyz: params.focusXyz,
      frequency_ghz: params.frequencyGhz,
      ecbf_budget_frac: params.ecbfBudgetFrac ?? 0.5,
      ...ecbfConstraintBody(params),
      ue_antenna: params.ueAntenna ?? 'dipole',
      ue_idx: params.ueIdx ?? 4,
    }),
    signal,
  })
  if (res.status === 401) {
    handle401()
    throw new ApiError(`POST ${path} failed: 401 Unauthorized`, 401)
  }
  if (res.status === 409) {
    const body = await res.json().catch(() => ({}))
    return {
      ok: false,
      notPrecomputed: true,
      error: typeof body?.error === 'string' ? body.error : 'Precoder not available for this combination',
    }
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'POST', path), res.status)
  const data = (await res.json()) as PrecoderResult
  return { ok: true, data }
}

export async function fetchBodyMap(params: BodyMapParams): Promise<BodyMapFetch> {
  const qs = new URLSearchParams({
    mesh: params.mesh,
    condition: params.condition,
    array_n: String(params.arrayN),
    beam: params.beam,
    quantity: params.quantity,
    frequency_ghz: String(params.frequencyGhz),
    realisation: String(params.realisation),
    statistic: params.statistic ?? 'single',
  })
  const path = `${STUDIO}/bodymap?${qs}`
  const res = await fetchWithRetry(`${BASE}${path}`)
  if (res.status === 401) {
    handle401()
    throw new ApiError(`GET ${path} failed: 401 Unauthorized`, 401)
  }
  if (res.status === 409) {
    const body = await res.json().catch(() => ({}))
    return {
      ok: false,
      notPrecomputed: true,
      error: typeof body?.error === 'string' ? body.error : 'Body map not precomputed for this combination',
    }
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'GET', path), res.status)
  const data = (await res.json()) as BodyMapResult
  return { ok: true, data }
}

// ---------------------------------------------------------------------------
// Phantom geometry
// ---------------------------------------------------------------------------

export async function fetchScene(condition: string, seed: number): Promise<SceneFetch> {
  const qs = new URLSearchParams({ condition, seed: String(seed) })
  const path = `${STUDIO}/scene?${qs}`
  const res = await fetchWithRetry(`${BASE}${path}`)
  if (res.status === 401) {
    handle401()
    throw new ApiError(`GET ${path} failed: 401 Unauthorized`, 401)
  }
  if (res.status === 409) {
    const body = await res.json().catch(() => ({}))
    return {
      ok: false,
      notPrecomputed: true,
      error: typeof body?.error === 'string' ? body.error : 'Scene geometry not precomputed for this combination',
    }
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'GET', path), res.status)
  const data = (await res.json()) as SceneGeometry
  return { ok: true, data }
}

export async function fetchPhantom(mesh: string, ueIdx = 4): Promise<PhantomGeometry> {
  const path = `${STUDIO}/phantom?mesh=${encodeURIComponent(mesh)}&ue_idx=${encodeURIComponent(String(ueIdx))}`
  const res = await fetchWithRetry(`${BASE}${path}`)
  if (res.status === 401) {
    handle401()
    throw new ApiError(`GET ${path} failed: 401 Unauthorized`, 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'GET', path), res.status)

  const stats = parseJsonHeader<PhantomStatsHeader>(res.headers.get('X-Stats'), 'X-Stats')
  const buffer = await res.arrayBuffer()

  // Recover each array from the buffer using offsets from the X-Stats manifest
  // (do not hardcode offsets - they are backend-defined).
  const byName = new Map(stats.arrays.map((a) => [a.name, a]))

  function readFloat(name: string): Float32Array {
    const meta = byName.get(name)
    if (!meta) throw new Error(`Phantom buffer missing float array "${name}"`)
    return new Float32Array(buffer, meta.offset, meta.length)
  }

  function readInt(name: string): Int32Array {
    const meta = byName.get(name)
    if (!meta) throw new Error(`Phantom buffer missing int array "${name}"`)
    return new Int32Array(buffer, meta.offset, meta.length)
  }

  return {
    vertices: readFloat('vertices'),
    faces: readInt('faces'),
    centroids: readFloat('centroids'),
    normals: readFloat('normals'),
    nVertices: stats.n_vertices,
    nFaces: stats.n_faces,
  }
}
