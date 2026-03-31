import type { ViewerConfig, Capabilities, BodyMeta, VoxelMeta, DosimetryStats, LevelInfo, SystemInfo, ICNIRPLimits, TissueSpectrum } from './types'
import { parseBodyBinary, parseVoxelBinary, parseSabBinary, parseSceneBinary } from './binary'
import { toServer, type ScenePos } from './coordinates'

const BASE = ''

/** Error subclass that carries the HTTP status code from a failed API call. */
export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// ---------------------------------------------------------------------------
// Transient error retry
// ---------------------------------------------------------------------------

const TRANSIENT_STATUSES = new Set([429, 502, 503, 504])
const MAX_RETRIES = 2

/** Wrap fetch with automatic retry on transient HTTP errors (502/503/504). */
export async function fetchWithRetry(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  let lastResponse: Response | undefined
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    if (attempt > 0 && init?.signal?.aborted) break
    const res = await fetch(input, init)
    if (!TRANSIENT_STATUSES.has(res.status)) return res
    lastResponse = res
    if (attempt < MAX_RETRIES) {
      const retryAfter = res.headers.get('Retry-After')
      const delayMs = retryAfter ? Math.min(parseInt(retryAfter, 10) * 1000, 5000) : (attempt + 1) * 1000
      await new Promise((r) => setTimeout(r, delayMs))
    }
  }
  return lastResponse!
}

// ---------------------------------------------------------------------------
// 401 handling - imported lazily to avoid circular dependency
// ---------------------------------------------------------------------------

function handle401(): void {
  // Lazy import to avoid circular dependency (useAuth imports from api/auth, not client.ts)
  import('@/hooks/useAuth').then(({ useAuth }) => {
    useAuth.getState().logout()
  })
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Safely parse a JSON header value, throwing a readable error on failure. */
export function parseJsonHeader<T>(header: string | null, name: string): T {
  if (!header) throw new Error(`Missing ${name} header`)
  try {
    return JSON.parse(header) as T
  } catch {
    throw new Error(`Malformed ${name} header: not valid JSON`)
  }
}

/** Try to extract a human-readable error from the response JSON body. */
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

async function getJson<T>(path: string): Promise<T> {
  const res = await fetchWithRetry(`${BASE}${path}`)
  if (res.status === 401) {
    handle401()
    throw new Error(`GET ${path} failed: 401 Unauthorized`)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'GET', path), res.status)
  return res.json() as Promise<T>
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetchWithRetry(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (res.status === 401) {
    handle401()
    throw new ApiError(`POST ${path} failed: 401 Unauthorized`, 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'POST', path), res.status)
  return res.json() as Promise<T>
}

async function getBinary(path: string): Promise<Response> {
  const res = await fetchWithRetry(`${BASE}${path}`)
  if (res.status === 401) {
    handle401()
    throw new Error(`GET ${path} failed: 401 Unauthorized`)
  }
  if (!res.ok) throw new Error(await extractErrorMessage(res, 'GET', path))
  return res
}

// ---------------------------------------------------------------------------
// Config export
// ---------------------------------------------------------------------------

export function exportConfig(state: Record<string, unknown>): Promise<Record<string, unknown>> {
  return postJson<Record<string, unknown>>('/api/export-config', state)
}

export interface ComputeResult {
  sab: Float32Array
  stats: DosimetryStats
  arrays: Record<string, Float32Array>
}

/** Shared logic for all compute endpoints: POST JSON, receive binary S_ab + X-Stats header. */
async function computeEndpoint(
  path: string,
  params: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<ComputeResult> {
  const res = await fetchWithRetry(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
    signal,
  })
  if (res.status === 401) {
    handle401()
    throw new Error(`POST ${path} failed: 401 Unauthorized`)
  }
  if (!res.ok) throw new Error(await extractErrorMessage(res, 'POST', path))

  const stats = parseJsonHeader<DosimetryStats>(res.headers.get('X-Stats'), 'X-Stats')

  const buffer = await res.arrayBuffer()

  const arrays: Record<string, Float32Array> = {}
  if (stats.arrays && stats.arrays.length > 0) {
    for (const meta of stats.arrays) {
      const byteOffset = meta.offset
      const byteLength = meta.length * 4
      if (byteOffset < 0 || byteLength < 0 || byteOffset + byteLength > buffer.byteLength) {
        throw new Error(
          `Invalid array metadata for "${meta.key}": offset=${byteOffset}, length=${meta.length}, buffer=${buffer.byteLength} bytes`,
        )
      }
      arrays[meta.key] = new Float32Array(buffer.slice(byteOffset, byteOffset + byteLength))
    }
  } else {
    arrays['sab'] = parseSabBinary(buffer)
  }

  return { sab: arrays['sab'] ?? parseSabBinary(buffer), stats, arrays }
}

// ---------------------------------------------------------------------------
// JSON endpoints
// ---------------------------------------------------------------------------

export async function fetchViewerConfig(): Promise<ViewerConfig> {
  return getJson<ViewerConfig>('/api/viewer-config')
}

export async function fetchCapabilities(): Promise<Capabilities> {
  return getJson<Capabilities>('/api/config')
}

export async function fetchSystemInfo(): Promise<SystemInfo> {
  return getJson<SystemInfo>('/api/system')
}

export async function fetchLevels(): Promise<LevelInfo[]> {
  return getJson<LevelInfo[]>('/api/levels')
}

export async function fetchBodyInfo(): Promise<BodyMeta> {
  return getJson<BodyMeta>('/api/body/info')
}

export async function fetchScenes(): Promise<string[]> {
  return getJson<string[]>('/api/scenes')
}

export async function fetchTileList(): Promise<{ tiles: string[]; transform: number[] | null }> {
  return getJson<{ tiles: string[]; transform: number[] | null }>('/api/tiles')
}

export async function fetchComplianceLimits(freqHz: number, scenario: string = 'general_public'): Promise<ICNIRPLimits> {
  return getJson<ICNIRPLimits>(`/api/compliance/limits?freq_hz=${freqHz}&scenario=${scenario}`)
}

export async function fetchComplianceSummary(txPowerDbm?: number): Promise<{ text: string }> {
  const params = txPowerDbm != null ? `?tx_power_dbm=${txPowerDbm}` : ''
  return getJson<{ text: string }>(`/api/compliance/summary${params}`)
}

export async function fetchTissueSpectrum(tissue: string, fMin: number, fMax: number, n: number = 100, skinModel?: string): Promise<TissueSpectrum> {
  const skinParam = skinModel ? `&skin_model=${encodeURIComponent(skinModel)}` : ""
  return getJson<TissueSpectrum>(`/api/tissue/spectrum?tissue=${encodeURIComponent(tissue)}&f_min=${fMin}&f_max=${fMax}&n=${n}${skinParam}`)
}

export interface GpuStatus {
  warm: boolean
  enabled: boolean
  seconds_remaining: number
}

export async function fetchGpuStatus(): Promise<GpuStatus> {
  return getJson<GpuStatus>('/api/gpu/status')
}

// ---------------------------------------------------------------------------
// Binary endpoints
// ---------------------------------------------------------------------------

export async function fetchBody(
  name?: string,
): Promise<{ binary: { positions: Float32Array; normals: Float32Array }; meta: BodyMeta }> {
  const url = name ? `/api/body?name=${encodeURIComponent(name)}` : '/api/body'
  const res = await getBinary(url)

  const metaHeader = res.headers.get('X-Meta')
  if (!metaHeader) throw new Error('GET /api/body: missing X-Meta header')
  const meta: BodyMeta = JSON.parse(metaHeader)

  const buffer = await res.arrayBuffer()
  const binary = parseBodyBinary(buffer, meta.n_vertices)

  return { binary, meta }
}

export async function fetchVoxels(): Promise<{
  binary: { positions: Float32Array; sizes: Float32Array; colors: Uint8Array; materialIndices: Uint8Array }
  meta: VoxelMeta
}> {
  const res = await getBinary('/api/voxels')

  const metaHeader = res.headers.get('X-Meta')
  if (!metaHeader) throw new Error('GET /api/voxels: missing X-Meta header')
  const meta: VoxelMeta = JSON.parse(metaHeader)

  const buffer = await res.arrayBuffer()
  const binary = parseVoxelBinary(buffer, meta.n_voxels)

  return { binary, meta }
}

export async function fetchTileFile(filename: string): Promise<ArrayBuffer> {
  const res = await getBinary(`/api/tiles/${encodeURIComponent(filename)}`)
  return res.arrayBuffer()
}

// ---------------------------------------------------------------------------
// POST endpoints
// ---------------------------------------------------------------------------

export async function loadSceneGeometry(scenePath: string): Promise<{
  vertices: Float32Array
  indices: Int32Array
  faceColors: Float32Array | null
  meta: { n_vertices: number; n_triangles: number; has_face_colors: boolean }
}> {
  const res = await fetchWithRetry(`${BASE}/api/scene/load`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: scenePath }),
  })
  if (res.status === 401) {
    handle401()
    throw new Error('POST /api/scene/load failed: 401 Unauthorized')
  }
  if (!res.ok) throw new Error(await extractErrorMessage(res, 'POST', '/api/scene/load'))

  const metaHeader = res.headers.get('X-Meta')
  if (!metaHeader) throw new Error('POST /api/scene/load: missing X-Meta header')
  const meta: { n_vertices: number; n_triangles: number; has_face_colors: boolean } = JSON.parse(metaHeader)

  const buffer = await res.arrayBuffer()
  const { vertices, indices, faceColors } = parseSceneBinary(
    buffer,
    meta.n_vertices,
    meta.n_triangles,
    meta.has_face_colors,
  )

  return { vertices, indices, faceColors, meta }
}

export async function fetchHullMesh(): Promise<{
  vertices: Float32Array
  indices: Int32Array
  faceColors: Float32Array | null
}> {
  const res = await fetchWithRetry(`${BASE}/api/voxels/hull-mesh`)
  if (!res.ok) throw new Error(`Hull mesh fetch failed: ${res.status}`)
  const meta = JSON.parse(res.headers.get('X-Meta') || '{}')
  const buffer = await res.arrayBuffer()
  const { vertices, indices, faceColors } = parseSceneBinary(
    buffer, meta.n_vertices, meta.n_triangles, meta.has_face_colors
  )
  return { vertices, indices, faceColors }
}

// ---------------------------------------------------------------------------
// Compute endpoints
// ---------------------------------------------------------------------------

export interface ComputeParams {
  antennaPos: ScenePos
  bodyOffset: ScenePos
  bodyRotationY: number
  mode: string
  fresnel: boolean
  polarisation: boolean
  curvature: boolean
  diffraction: boolean
  powerDbm: number
  skinModel: string
  freqGhz: number
  nPaths: number
  stochastic?: boolean
  stochasticPreset?: string
  stochasticOverrides?: Record<string, number>
  stochasticSeed?: number
  quantities: string[]
  exposureScenario: string
  bodyName?: string
}

function computePayload(params: ComputeParams) {
  return {
    antenna_pos: toServer(params.antennaPos),
    body_offset: toServer(params.bodyOffset),
    body_rotation_y: params.bodyRotationY,
    mode: params.mode,
    fresnel: params.fresnel,
    polarisation: params.polarisation,
    curvature: params.curvature,
    diffraction: params.diffraction,
    power_dbm: params.powerDbm,
    skin_model: params.skinModel,
    freq_hz: params.freqGhz * 1e9,
    n_paths: params.nPaths,
    quantities: params.quantities,
    exposure_scenario: params.exposureScenario,
    ...(params.bodyName ? { body_name: params.bodyName } : {}),
    ...(params.stochastic ? {
      stochastic: true,
      stochastic_preset: params.stochasticPreset,
      stochastic_overrides: params.stochasticOverrides,
      stochastic_seed: params.stochasticSeed,
    } : {}),
  }
}

export async function computeDosimetry(
  params: ComputeParams,
  signal?: AbortSignal,
): Promise<ComputeResult> {
  return computeEndpoint('/api/compute', computePayload(params), signal)
}

export interface RtConfig {
  max_depth: number
  method: string
  rays_per_source: number
  max_paths_per_source: number
  chunk_size: number | null
  los: boolean
  specular_reflection: boolean
  diffuse_reflection: boolean
  refraction: boolean
  diffraction: boolean
  edge_diffraction: boolean
  diffraction_lit_region: boolean
  reflection_loss_per_order: number
  synthetic_array: boolean
  seed: number
}

export async function computeVoxelRT(
  params: ComputeParams & { rtConfig: RtConfig },
  signal?: AbortSignal,
): Promise<ComputeResult> {
  return computeEndpoint(
    '/api/compute/voxel-rt',
    { ...computePayload(params), rt_config: params.rtConfig },
    signal,
  )
}

export async function computeRT(
  params: ComputeParams & { scenePath: string; rtConfig: RtConfig },
  signal?: AbortSignal,
): Promise<ComputeResult> {
  return computeEndpoint(
    '/api/compute/rt',
    { ...computePayload(params), scene_path: params.scenePath, rt_config: params.rtConfig },
    signal,
  )
}

export async function computeSionnaRT(
  params: ComputeParams & { scenePath: string; rtConfig: RtConfig },
  signal?: AbortSignal,
): Promise<ComputeResult> {
  return computeEndpoint(
    '/api/compute/sionna-rt',
    { ...computePayload(params), scene_path: params.scenePath, rt_config: params.rtConfig },
    signal,
  )
}

// ---------------------------------------------------------------------------
// SSE endpoint
// ---------------------------------------------------------------------------

export function loadLocation(location: string, radius: number, voxelSize: number, force: boolean): EventSource {
  const params = new URLSearchParams({
    location,
    radius: String(radius),
    voxel_size: String(voxelSize),
    force: String(force),
  })
  return new EventSource(`${BASE}/api/location/load?${params.toString()}`)
}

export async function cancelLocation(): Promise<void> {
  const res = await fetchWithRetry(`${BASE}/api/location/cancel`, { method: 'POST' })
  if (!res.ok) throw new Error(await extractErrorMessage(res, 'POST', '/api/location/cancel'))
}

// ---------------------------------------------------------------------------
// Compliance analysis endpoints
// ---------------------------------------------------------------------------

export interface PowerSweepResult {
  power_dbm: number[]
  margin_db: number[]
  compliant: boolean[]
  p_max_compliant_w: number
  p_max_compliant_dbm: number | null
}

export interface FrequencySweepResult {
  freq_ghz: number[]
  margin_db: number[]
  compliant: boolean[]
}

export async function fetchPowerSweep(params: {
  sab_4cm2: number
  freq_hz: number
  ref_power_dbm: number
  scenario?: string
  sinc_local?: number
  sab_1cm2?: number
  sar_wb?: number
  sinc_wb?: number
}): Promise<PowerSweepResult> {
  const qs = new URLSearchParams({
    sab_4cm2: String(params.sab_4cm2),
    freq_hz: String(params.freq_hz),
    ref_power_dbm: String(params.ref_power_dbm),
    scenario: params.scenario ?? 'general_public',
  })
  if (params.sinc_local != null) qs.set('sinc_local', String(params.sinc_local))
  if (params.sab_1cm2 != null) qs.set('sab_1cm2', String(params.sab_1cm2))
  if (params.sar_wb != null) qs.set('sar_wb', String(params.sar_wb))
  if (params.sinc_wb != null) qs.set('sinc_wb', String(params.sinc_wb))
  return getJson<PowerSweepResult>(`/api/compliance/power-sweep?${qs}`)
}

export async function fetchDosimetryCsv(): Promise<Blob> {
  const res = await fetchWithRetry(`${BASE}/api/export/dosimetry-csv`)
  if (res.status === 401) {
    handle401()
    throw new Error('GET /api/export/dosimetry-csv failed: 401 Unauthorized')
  }
  if (!res.ok) throw new Error(await extractErrorMessage(res, 'GET', '/api/export/dosimetry-csv'))
  return res.blob()
}

export async function fetchFrequencySweep(params: {
  sab_4cm2: number
  scenario?: string
  sinc_local?: number
  sab_1cm2?: number
  sar_wb?: number
  sinc_wb?: number
}): Promise<FrequencySweepResult> {
  const qs = new URLSearchParams({
    sab_4cm2: String(params.sab_4cm2),
    scenario: params.scenario ?? 'general_public',
  })
  if (params.sinc_local != null) qs.set('sinc_local', String(params.sinc_local))
  if (params.sab_1cm2 != null) qs.set('sab_1cm2', String(params.sab_1cm2))
  if (params.sar_wb != null) qs.set('sar_wb', String(params.sar_wb))
  if (params.sinc_wb != null) qs.set('sinc_wb', String(params.sinc_wb))
  return getJson<FrequencySweepResult>(`/api/compliance/frequency-sweep?${qs}`)
}

