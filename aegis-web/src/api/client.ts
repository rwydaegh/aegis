import type { ViewerConfig, Capabilities, BodyMeta, VoxelMeta, DosimetryStats, SystemInfo, TissueSpectrum } from './types'
import { parseBodyBinary, parseVoxelBinary, parseSabBinary, parseSceneBinary } from './binary'
import { toServer, type ScenePos } from './coordinates'
import type { DiffractionModel, InterBody } from '@/stores/simulation'

const BASE = ''

// ---------------------------------------------------------------------------
// ApiError - preserves HTTP status for caller-side filtering
// ---------------------------------------------------------------------------

/** Error thrown by API helpers when the server returns a non-OK status. */
export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Returns true for client errors (4xx) that represent user mistakes, not bugs. */
export function isClientError(err: unknown): boolean {
  return err instanceof ApiError && err.status >= 400 && err.status < 500
}

// ---------------------------------------------------------------------------
// Transient error retry
// ---------------------------------------------------------------------------

const TRANSIENT_STATUSES = new Set([429, 502, 503, 504])
const MAX_RETRIES = 2

/** Detect transient network errors (mobile connection drops, offline, etc.). */
export function isNetworkError(err: unknown): boolean {
  if (err instanceof TypeError && /failed to fetch|network/i.test(err.message)) return true
  if (err instanceof DOMException && err.name === 'AbortError') return false
  if (err instanceof Error && /failed to fetch|networkerror|load failed/i.test(err.message)) return true
  return false
}

/** Wrap fetch with automatic retry on transient HTTP errors and network failures. */
export async function fetchWithRetry(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  let lastResponse: Response | undefined
  let lastError: unknown
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    if (attempt > 0 && init?.signal?.aborted) break
    try {
      const res = await fetch(input, init)
      if (!TRANSIENT_STATUSES.has(res.status)) return res
      lastResponse = res
    } catch (err) {
      // Network error (server unreachable, connection reset, etc.)
      lastError = err
      if (attempt >= MAX_RETRIES) break
    }
    if (attempt < MAX_RETRIES) {
      const retryAfter = lastResponse?.headers.get('Retry-After')
      const parsed = retryAfter ? parseInt(retryAfter, 10) : NaN
      const baseDelayMs = Number.isFinite(parsed) ? Math.min(parsed * 1000, 5000) : (attempt + 1) * 1000
      // Add +/-10% jitter to prevent thundering herd on concurrent retries
      const jitter = baseDelayMs * (0.9 + Math.random() * 0.2)
      await new Promise((r) => setTimeout(r, jitter))
    }
  }
  if (lastResponse) return lastResponse
  throw lastError
}

// ---------------------------------------------------------------------------
// 401 handling - imported lazily to avoid circular dependency
// ---------------------------------------------------------------------------

export function handle401(): void {
  // Lazy import to avoid circular dependency (useAuth imports from api/auth, not client.ts)
  import('@/hooks/useAuth').then(({ useAuth }) => {
    useAuth.getState().logout()
  })
}

/** Throw ApiError and trigger logout if the response is 401. No-op otherwise. */
export function throwIf401(res: Response, method: string, path: string): void {
  if (res.status === 401) {
    handle401()
    throw new ApiError(`${method} ${path} failed: 401 Unauthorized`, 401)
  }
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
    throw new ApiError(`GET ${path} failed: 401 Unauthorized`, 401)
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

async function getBinary(path: string, signal?: AbortSignal): Promise<Response> {
  const res = await fetchWithRetry(`${BASE}${path}`, signal ? { signal } : undefined)
  if (res.status === 401) {
    handle401()
    throw new ApiError(`GET ${path} failed: 401 Unauthorized`, 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'GET', path), res.status)
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
    throw new ApiError(`POST ${path} failed: 401 Unauthorized`, 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'POST', path), res.status)

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

export async function fetchTileList(): Promise<{ tiles: string[]; transform: number[] | null }> {
  return getJson<{ tiles: string[]; transform: number[] | null }>('/api/tiles')
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
  signal?: AbortSignal,
): Promise<{ binary: { positions: Float32Array; normals: Float32Array }; meta: BodyMeta }> {
  const url = name ? `/api/body?name=${encodeURIComponent(name)}` : '/api/body'
  const res = await getBinary(url, signal)

  const meta = parseJsonHeader<BodyMeta>(res.headers.get('X-Meta'), 'X-Meta')

  const buffer = await res.arrayBuffer()
  const binary = parseBodyBinary(buffer, meta.n_vertices)

  return { binary, meta }
}

export async function fetchVoxels(signal?: AbortSignal): Promise<{
  binary: { positions: Float32Array; sizes: Float32Array; colors: Uint8Array; materialIndices: Uint8Array }
  meta: VoxelMeta
}> {
  const res = await getBinary('/api/voxels', signal)

  const meta = parseJsonHeader<VoxelMeta>(res.headers.get('X-Meta'), 'X-Meta')

  const buffer = await res.arrayBuffer()
  const binary = parseVoxelBinary(buffer, meta.n_voxels)

  return { binary, meta }
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
    throw new ApiError('POST /api/scene/load failed: 401 Unauthorized', 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'POST', '/api/scene/load'), res.status)

  const meta = parseJsonHeader<{ n_vertices: number; n_triangles: number; has_face_colors: boolean }>(res.headers.get('X-Meta'), 'X-Meta')

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
  if (res.status === 401) {
    handle401()
    throw new ApiError('GET /api/voxels/hull-mesh failed: 401 Unauthorized', 401)
  }
  if (!res.ok) throw new ApiError(`Hull mesh fetch failed: ${res.status}`, res.status)
  const meta = parseJsonHeader<{ n_vertices: number; n_triangles: number; has_face_colors: boolean }>(res.headers.get('X-Meta'), 'X-Meta')
  const buffer = await res.arrayBuffer()
  const { vertices, indices, faceColors } = parseSceneBinary(
    buffer, meta.n_vertices, meta.n_triangles, meta.has_face_colors
  )
  return { vertices, indices, faceColors }
}

// ---------------------------------------------------------------------------
// Compute endpoints
// ---------------------------------------------------------------------------

export interface AntennaParam {
  position: ScenePos
  power_dbm: number
  array_config: {
    n_h: number
    n_v: number
    d_h_wavelengths: number
    d_v_wavelengths: number
    broadside: [number, number, number]
    element_pattern: string
  }
}

export interface ComputeParams {
  antennaPos: ScenePos
  bodyOffset: ScenePos
  bodyRotationY: number
  mode: string
  fresnel: boolean
  polarisation: boolean
  curvature: boolean
  diffractionModel: DiffractionModel
  interBody: InterBody
  powerDbm: number
  skinModel: string
  freqGhz: number
  stochastic?: boolean
  stochasticPreset?: string
  stochasticOverrides?: Record<string, number>
  stochasticSeed?: number
  quantities: string[]
  exposureScenario: string
  bodyName?: string
  antennas?: AntennaParam[]
  exposureMode?: string
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
    diffraction_model: params.diffractionModel,
    inter_body: params.interBody,
    power_dbm: params.powerDbm,
    skin_model: params.skinModel,
    freq_hz: params.freqGhz * 1e9,
    quantities: params.quantities,
    exposure_scenario: params.exposureScenario,
    exposure_mode: params.exposureMode ?? 'theoretical',
    ...(params.bodyName ? { body_name: params.bodyName } : {}),
    ...(params.stochastic ? {
      stochastic: true,
      stochastic_preset: params.stochasticPreset,
      stochastic_overrides: params.stochasticOverrides,
      stochastic_seed: params.stochasticSeed,
    } : {}),
    ...(params.antennas && params.antennas.length > 0 ? {
      antennas: params.antennas.map(a => ({
        ...a,
        position: toServer(a.position),
        array_config: {
          ...a.array_config,
          broadside: toServer(a.array_config.broadside as [number, number, number]),
        },
      })),
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

export async function computeSionnaEnvRT(
  params: ComputeParams & { rtConfig: RtConfig },
  signal?: AbortSignal,
): Promise<ComputeResult> {
  return computeEndpoint(
    '/api/compute/sionna-env-rt',
    { ...computePayload(params), rt_config: params.rtConfig },
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
// LSP heatmap
// ---------------------------------------------------------------------------

export interface LSPHeatmapParams {
  preset: string
  freq_ghz: number
  antenna_pos: [number, number, number]
  lsp_name: string
  bounds: [number, number, number, number]
  resolution: number
  seed: number
}

export interface LSPHeatmapResult {
  data: number[][]
  bounds: [number, number, number, number]
  lsp_name: string
  vmin: number
  vmax: number
  resolution: number
}

export async function fetchLSPHeatmap(params: LSPHeatmapParams): Promise<LSPHeatmapResult> {
  return postJson<LSPHeatmapResult>('/api/lsp-heatmap', params)
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
  margin_db: (number | null)[]
  per_check_margin_db: {
    sab_4cm2: (number | null)[]
    sab_1cm2: (number | null)[]
    sar_wb: (number | null)[]
    sinc_local: (number | null)[]
    sinc_whole_body: (number | null)[]
  }
  compliant: boolean[]
}

export async function fetchPowerSweep(params: {
  sab_4cm2?: number
  freq_hz: number
  ref_power_dbm: number
  scenario?: string
  sinc_local?: number
  sab_1cm2?: number
  sar_wb?: number
  sinc_wb?: number
}): Promise<PowerSweepResult> {
  const qs = new URLSearchParams({
    freq_hz: String(params.freq_hz),
    ref_power_dbm: String(params.ref_power_dbm),
    scenario: params.scenario ?? 'general_public',
  })
  if (params.sab_4cm2 != null) qs.set('sab_4cm2', String(params.sab_4cm2))
  if (params.sinc_local != null) qs.set('sinc_local', String(params.sinc_local))
  if (params.sab_1cm2 != null) qs.set('sab_1cm2', String(params.sab_1cm2))
  if (params.sar_wb != null) qs.set('sar_wb', String(params.sar_wb))
  if (params.sinc_wb != null) qs.set('sinc_wb', String(params.sinc_wb))
  return getJson<PowerSweepResult>(`/api/compliance/power-sweep?${qs}`)
}

export interface PathContribution {
  index: number
  contribution_w_m2: number | null
  fraction: number | null
  cumulative: number | null
  k_hat: [number, number, number]
  power_w_m2: number | null
  is_los: boolean
}

export interface PathImportanceEntry {
  index: number
  importance_w: number | null
  fraction: number | null
  is_los: boolean
}

export interface PathContributionsResult {
  triangle_index: number | null
  sab_total: number | null
  paths: PathContribution[]
  importance: {
    top: PathImportanceEntry[]
    p_abs_total: number | null
    n_paths: number
  }
  n_paths: number
  n_los: number
  n_nlos: number
}

export async function fetchPathContributions(params?: {
  top_k?: number
  triangle_index?: number
}): Promise<PathContributionsResult> {
  const qs = new URLSearchParams()
  if (params?.top_k != null) qs.set('top_k', String(params.top_k))
  if (params?.triangle_index != null) qs.set('triangle_index', String(params.triangle_index))
  const suffix = qs.toString() ? `?${qs}` : ''
  return getJson<PathContributionsResult>(`/api/analyze/path-contributions${suffix}`)
}

export async function fetchDosimetryCsv(): Promise<Blob> {
  const res = await fetchWithRetry(`${BASE}/api/export/dosimetry-csv`)
  if (res.status === 401) {
    handle401()
    throw new ApiError('GET /api/export/dosimetry-csv failed: 401 Unauthorized', 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'GET', '/api/export/dosimetry-csv'), res.status)
  return res.blob()
}

export async function fetchDosimetryJson(): Promise<Blob> {
  const res = await fetchWithRetry(`${BASE}/api/export/dosimetry-json`)
  if (res.status === 401) {
    handle401()
    throw new ApiError('GET /api/export/dosimetry-json failed: 401 Unauthorized', 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'GET', '/api/export/dosimetry-json'), res.status)
  return res.blob()
}

export async function fetchDosimetryNpz(): Promise<Blob> {
  const res = await fetchWithRetry(`${BASE}/api/export/dosimetry-npz`)
  if (res.status === 401) {
    handle401()
    throw new ApiError('GET /api/export/dosimetry-npz failed: 401 Unauthorized', 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'GET', '/api/export/dosimetry-npz'), res.status)
  return res.blob()
}

export interface HeatmapResult {
  freq_ghz: number[]
  power_dbm: number[]
  margin_db: number[][]
  compliant: boolean[][]
  p_max_dbm_per_freq: number[]
  n_freq: number
  n_power: number
}

export async function fetchComplianceHeatmap(params: {
  sab_4cm2?: number
  sab_1cm2?: number
  freq_hz: number
  ref_power_dbm: number
  scenario?: string
  sinc_local?: number
}): Promise<HeatmapResult> {
  const qs = new URLSearchParams({
    freq_hz: String(params.freq_hz),
    ref_power_dbm: String(params.ref_power_dbm),
    scenario: params.scenario ?? 'general_public',
  })
  if (params.sab_4cm2 != null) qs.set('sab_4cm2', String(params.sab_4cm2))
  if (params.sab_1cm2 != null) qs.set('sab_1cm2', String(params.sab_1cm2))
  if (params.sinc_local != null) qs.set('sinc_local', String(params.sinc_local))
  return getJson<HeatmapResult>(`/api/compliance/heatmap?${qs}`)
}

export async function fetchFrequencySweep(params: {
  sab_4cm2?: number
  scenario?: string
  sinc_local?: number
  sab_1cm2?: number
  sar_wb?: number
  sinc_wb?: number
}): Promise<FrequencySweepResult> {
  const qs = new URLSearchParams({
    scenario: params.scenario ?? 'general_public',
  })
  if (params.sab_4cm2 != null) qs.set('sab_4cm2', String(params.sab_4cm2))
  if (params.sinc_local != null) qs.set('sinc_local', String(params.sinc_local))
  if (params.sab_1cm2 != null) qs.set('sab_1cm2', String(params.sab_1cm2))
  if (params.sar_wb != null) qs.set('sar_wb', String(params.sar_wb))
  if (params.sinc_wb != null) qs.set('sinc_wb', String(params.sinc_wb))
  return getJson<FrequencySweepResult>(`/api/compliance/frequency-sweep?${qs}`)
}

export interface SpatialComplianceResult {
  lats: number[]
  lons: number[]
  margin_db: number[][]
  compliant: boolean[][]
  sinc_w_m2: number[][]
  n_lat: number
  n_lon: number
  scenario: string
  freq_hz_dominant: number
  T0: number
  n_stations: number
}

export async function fetchSpatialCompliance(params: {
  bbox?: [number, number, number, number]
  resolution?: number
  scenario?: string
  receiver_height_m?: number
}): Promise<SpatialComplianceResult> {
  return postJson<SpatialComplianceResult>('/api/compliance/spatial', params)
}

