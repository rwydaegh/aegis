import type { ViewerConfig, Capabilities, BodyMeta, VoxelMeta, DosimetryStats, LevelInfo } from './types'
import { parseBodyBinary, parseVoxelBinary, parseSabBinary, parseSceneBinary } from './binary'
import { toServer, type ScenePos } from './coordinates'

const BASE = ''

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

async function getBinary(path: string): Promise<Response> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}`)
  return res
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
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
    signal,
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status} ${res.statusText}`)

  const statsHeader = res.headers.get('X-Stats')
  if (!statsHeader) throw new Error(`POST ${path}: missing X-Stats header`)
  const stats: DosimetryStats = JSON.parse(statsHeader)

  const buffer = await res.arrayBuffer()

  const arrays: Record<string, Float32Array> = {}
  if (stats.arrays && stats.arrays.length > 0) {
    for (const meta of stats.arrays) {
      const byteOffset = meta.offset
      const byteLength = meta.length * 4
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

export async function fetchHealth(): Promise<{ status: string; version: string }> {
  return getJson<{ status: string; version: string }>('/api/health')
}

export async function fetchSystemInfo(): Promise<{ hostname: string; platform: string; gpu: unknown }> {
  return getJson<{ hostname: string; platform: string; gpu: unknown }>('/api/system')
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

export async function fetchHullMesh(): Promise<{
  vertices: Float32Array
  indices: Int32Array
  meta: { n_vertices: number; n_triangles: number }
}> {
  const res = await getBinary('/api/voxels/hull-mesh')

  const metaHeader = res.headers.get('X-Meta')
  if (!metaHeader) throw new Error('GET /api/voxels/hull-mesh: missing X-Meta header')
  const meta: { n_vertices: number; n_triangles: number } = JSON.parse(metaHeader)

  const buffer = await res.arrayBuffer()
  const { vertices, indices } = parseSceneBinary(buffer, meta.n_vertices, meta.n_triangles, false)

  return { vertices, indices, meta }
}

export async function fetchTileFile(filename: string): Promise<ArrayBuffer> {
  const res = await getBinary(`/api/tiles/${encodeURIComponent(filename)}`)
  return res.arrayBuffer()
}

// ---------------------------------------------------------------------------
// POST endpoints
// ---------------------------------------------------------------------------

export async function switchBody(name: string): Promise<{ ok: boolean; meta: BodyMeta }> {
  return postJson<{ ok: boolean; meta: BodyMeta }>('/api/body/switch', { name })
}

export async function loadSceneGeometry(scenePath: string): Promise<{
  vertices: Float32Array
  indices: Int32Array
  faceColors: Float32Array | null
  meta: { n_vertices: number; n_triangles: number; has_face_colors: boolean }
}> {
  const res = await fetch(`${BASE}/api/scene/load`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: scenePath }),
  })
  if (!res.ok) throw new Error(`POST /api/scene/load failed: ${res.status} ${res.statusText}`)

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

export async function computeVoxelRT(
  params: ComputeParams & { maxOrder: number },
  signal?: AbortSignal,
): Promise<ComputeResult> {
  return computeEndpoint(
    '/api/compute/voxel-rt',
    { ...computePayload(params), max_order: params.maxOrder },
    signal,
  )
}

export async function computeRT(
  params: ComputeParams & { scenePath: string; maxOrder: number },
  signal?: AbortSignal,
): Promise<ComputeResult> {
  return computeEndpoint(
    '/api/compute/rt',
    { ...computePayload(params), scene_path: params.scenePath, max_order: params.maxOrder },
    signal,
  )
}

export async function computeSionnaRT(
  params: ComputeParams & { scenePath: string },
  signal?: AbortSignal,
): Promise<ComputeResult> {
  return computeEndpoint(
    '/api/compute/sionna-rt',
    { ...computePayload(params), scene_path: params.scenePath },
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
  const res = await fetch(`${BASE}/api/location/cancel`, { method: 'POST' })
  if (!res.ok) throw new Error(`POST /api/location/cancel failed: ${res.status} ${res.statusText}`)
}
