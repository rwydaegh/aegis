import type { DosimetryStats } from '@/api/types'
import {
  ApiError,
  fetchWithRetry,
  handle401,
  parseJsonHeader,
  type ComputeResult,
} from '@/api/client'
import { parseSabBinary } from '@/api/binary'

const BASE = ''

// ---------------------------------------------------------------------------
// Shared types (imported by the lab store)
// ---------------------------------------------------------------------------

export interface LabPattern {
  id: string
  label: string
  freqs_mhz: number[]
  synthetic: boolean
}

export interface LabRig {
  n_vertices: number
  n_joints: number
  template: number[]
  faces: number[]
  lbs_weights: number[]
  rest_joints: number[]
  parents: number[]
}

export interface LabNearSource {
  kind: 'near'
  pattern_id: string
  position: [number, number, number]
  yaw: number
  pitch: number
  roll: number
}

export interface LabFarSource {
  kind: 'far'
  theta_inc: number
  phi_inc: number
  pol_angle: number
}

export type LabSource = LabNearSource | LabFarSource

export interface LabPhysics {
  diffraction_model: 'none' | 'gelu' | 'fock'
  self_shadow: boolean
  fresnel: boolean
  curvature: boolean
  polarisation: boolean
}

export interface ComputeDoseParams {
  gender: 'neutral' | 'male' | 'female'
  betas: number[]
  pose?: number[]
  preset?: string | null
  freq_mhz: number
  power_w: number
  physics: LabPhysics
  source: LabSource
}

export interface PoseBodyParams {
  gender: 'neutral' | 'male' | 'female'
  betas?: number[]
  pose?: number[]
  preset?: string | null
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

async function getJson<T>(path: string): Promise<T> {
  const res = await fetchWithRetry(`${BASE}${path}`)
  if (res.status === 401) {
    handle401()
    throw new ApiError(`GET ${path} failed: 401 Unauthorized`, 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'GET', path), res.status)
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Near-field patterns
// ---------------------------------------------------------------------------

export async function getNfPatterns(): Promise<LabPattern[]> {
  const data = await getJson<{ patterns: LabPattern[] }>('/api/lab/nf-patterns')
  return data.patterns
}

export interface PatternLobe {
  theta: number[]
  phi: number[]
  r: number[][]
}

export async function getPatternLobe(
  id: string,
  freqMhz?: number,
  nTheta?: number,
  nPhi?: number,
): Promise<PatternLobe> {
  const qs = new URLSearchParams({ id })
  if (freqMhz != null) qs.set('freq_mhz', String(freqMhz))
  if (nTheta != null) qs.set('n_theta', String(nTheta))
  if (nPhi != null) qs.set('n_phi', String(nPhi))
  return getJson<PatternLobe>(`/api/lab/pattern_lobe?${qs}`)
}

// ---------------------------------------------------------------------------
// Pose presets
// ---------------------------------------------------------------------------

export async function getPresets(): Promise<Record<string, number[]>> {
  return getJson<Record<string, number[]>>('/api/lab/presets')
}

// ---------------------------------------------------------------------------
// Parametric rig and posing
// ---------------------------------------------------------------------------

export async function getRig(
  gender: 'neutral' | 'male' | 'female',
  betas?: number[],
): Promise<LabRig> {
  const qs = new URLSearchParams({ gender })
  if (betas && betas.length > 0) qs.set('betas', betas.join(','))
  return getJson<LabRig>(`/api/lab/rig?${qs}`)
}

export async function poseBody(
  params: PoseBodyParams,
): Promise<{ positions: Float32Array; normals: Float32Array; vertexHash: number }> {
  const res = await fetchWithRetry(`${BASE}/api/parametric-body`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (res.status === 401) {
    handle401()
    throw new ApiError('POST /api/parametric-body failed: 401 Unauthorized', 401)
  }
  if (!res.ok) throw new ApiError(await extractErrorMessage(res, 'POST', '/api/parametric-body'), res.status)

  const meta = parseJsonHeader<{ n_vertices: number; vertex_hash: number }>(
    res.headers.get('X-Meta'),
    'X-Meta',
  )

  const buffer = await res.arrayBuffer()
  const floats = new Float32Array(buffer)
  const n = meta.n_vertices
  const positions = new Float32Array(floats.subarray(0, n * 3))
  const normals = new Float32Array(floats.subarray(n * 3, n * 6))

  return { positions, normals, vertexHash: meta.vertex_hash }
}

// ---------------------------------------------------------------------------
// Dose compute
// ---------------------------------------------------------------------------

export async function computeDose(
  params: ComputeDoseParams,
  signal?: AbortSignal,
): Promise<ComputeResult> {
  const path = '/api/lab/compute'
  const res = await fetchWithRetry(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...params, quantities: ['sab', 'sab_4cm2'] }),
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
