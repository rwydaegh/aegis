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

export interface SliceParams {
  condition: string
  arrayN: number
  seed: number
  beam: string
  focusMode: StudioFocusMode
  focusXyz: Vec3
  frequencyGhz: number
  plane: SlicePlane
  quantity: StudioFieldQuantity
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
// Body map
// ---------------------------------------------------------------------------

export interface BodyMapParams {
  condition: string
  arrayN: number
  beam: string
  quantity: string
  frequencyGhz: number
  /** Realisation index (the seed / ensemble member). */
  realisation: number
}

export interface BodyMapResult {
  /** Per-triangle values, length 8000, aligned to phantom faces. */
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
  })
  if (params.topK != null) qs.set('top_k', String(params.topK))
  return getJson<RaysResponse>(`${STUDIO}/rays?${qs}`)
}

// ---------------------------------------------------------------------------
// Slice
// ---------------------------------------------------------------------------

function slicePayload(params: SliceParams) {
  return {
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

export async function fetchBodyMap(params: BodyMapParams): Promise<BodyMapFetch> {
  const qs = new URLSearchParams({
    condition: params.condition,
    array_n: String(params.arrayN),
    beam: params.beam,
    quantity: params.quantity,
    frequency_ghz: String(params.frequencyGhz),
    realisation: String(params.realisation),
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

export async function fetchPhantom(mesh: string): Promise<PhantomGeometry> {
  const path = `${STUDIO}/phantom?mesh=${encodeURIComponent(mesh)}`
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
