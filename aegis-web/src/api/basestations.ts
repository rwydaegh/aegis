import { postJson, fetchWithRetry, parseJsonHeader } from './client'
import type { DosimetryStats } from './types'
import type { Archetype } from '@/utils/classifyAntenna'

export interface BaseStationData {
  site_code: string
  antenna_label: string
  operator: string
  technology: string
  latitude: number
  longitude: number
  height_m: number
  eirp_dbm: number
  gain_dbi: number
  freq_mhz: number
  azimuth_deg: number
  total_tilt_deg: number
  has_pattern: boolean
  horizontal_beamwidth_deg: number
  vertical_beamwidth_deg: number
  // Classification fields from backend
  archetype: Archetype
  n_h: number
  n_v: number
  panel_width_m: number
  panel_height_m: number
}

interface LoadResponse {
  count: number
  basestations: BaseStationData[]
}

interface LoadParams {
  location?: string
  lat?: number
  lon?: number
  radius_m?: number
  operator?: string
  technology?: string
}

export async function loadBasestations(params: LoadParams): Promise<LoadResponse> {
  return postJson<LoadResponse>('/api/basestations/load', params)
}

export async function listBasestations(): Promise<LoadResponse> {
  const res = await fetchWithRetry('/api/basestations/list')
  if (!res.ok) {
    let msg = `GET /api/basestations/list failed: ${res.status} ${res.statusText}`
    try { const data = await res.json(); if (data?.error) msg = data.error } catch {}
    throw new Error(msg)
  }
  return res.json() as Promise<LoadResponse>
}

interface ComputeParams {
  indices?: number[]
  mode?: string
  body_offset?: [number, number, number]
  body_rotation_y?: number
  quantities?: string[]
  skin_model?: string
  freq_hz?: number
  use_beamforming?: boolean | 'auto'
  exposure_mode?: string
}

export interface ComputeResult {
  sab: Float32Array
  stats: DosimetryStats
  arrays: Record<string, Float32Array>
}

export async function computeBasestations(
  params: ComputeParams,
  signal?: AbortSignal,
): Promise<ComputeResult> {
  const res = await fetchWithRetry('/api/basestations/compute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
    signal,
  })
  if (!res.ok) {
    let msg = `POST /api/basestations/compute failed: ${res.status} ${res.statusText}`
    try { const data = await res.json(); if (data?.error) msg = data.error } catch {}
    throw new Error(msg)
  }

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
    arrays['sab'] = new Float32Array(buffer)
  }

  return { sab: arrays['sab'] ?? new Float32Array(buffer), stats, arrays }
}
