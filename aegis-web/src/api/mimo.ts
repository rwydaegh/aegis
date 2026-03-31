import type {
  ArrayConfig,
  MIMOUserConfig,
  MIMOComputeRequest,
  MIMOComputeResponse,
  MIMOSummary,
  DosimetryStats,
} from './types'
import { toServer } from './coordinates'
import { fetchWithRetry, parseJsonHeader } from './client'

async function extractError(res: Response, label: string): Promise<string> {
  const fallback = `${label}: ${res.status} ${res.statusText}`
  try {
    const data = await res.json()
    if (data && typeof data.error === 'string') return data.error
  } catch { /* not JSON */ }
  return fallback
}

/** Server-side payload (Z-up positions). */
interface MIMOServerPayload {
  array: Omit<ArrayConfig, 'position'> & { position: [number, number, number] }
  users: Array<Omit<MIMOUserConfig, 'position'> & { position: [number, number, number] }>
  freq_hz: number
  power_dbm: number
  precoder_type: string
  changed?: { type: string; user_id?: string }
}

/** Convert scene-coords payload to server-coords payload. */
export function buildMIMOComputePayload(req: MIMOComputeRequest): MIMOServerPayload {
  return {
    array: {
      ...req.array,
      position: toServer(req.array.position),
      broadside: toServer(req.array.broadside),
    },
    users: req.users.map(u => ({
      ...u,
      position: toServer(u.position),
    })),
    freq_hz: req.freq_hz,
    power_dbm: req.power_dbm,
    precoder_type: req.precoder_type,
    ...(req.changed ? { changed: req.changed } : {}),
  }
}

/** Trigger MIMO computation for all users. */
export async function computeMIMO(
  req: MIMOComputeRequest,
  signal?: AbortSignal,
): Promise<MIMOComputeResponse> {
  const payload = buildMIMOComputePayload(req)
  const res = await fetchWithRetry('/api/mimo/compute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok) throw new Error(await extractError(res, 'MIMO compute failed'))
  return res.json()
}

/** Fetch a single user's sab result as binary. */
export async function fetchMIMOResult(
  userId: string,
  signal?: AbortSignal,
): Promise<{ sab: Float32Array; stats: DosimetryStats }> {
  const resp = await fetchWithRetry(`/api/mimo/result/${userId}`, { signal })
  if (!resp.ok) throw new Error(await extractError(resp, 'MIMO result fetch failed'))
  const stats = parseJsonHeader<DosimetryStats>(resp.headers.get('X-Stats'), 'X-Stats')
  const buf = await resp.arrayBuffer()
  const sab = new Float32Array(buf)
  return { sab, stats }
}

/** Fetch summary stats for all users. */
export async function fetchMIMOSummary(
  signal?: AbortSignal,
): Promise<MIMOSummary> {
  const resp = await fetchWithRetry('/api/mimo/summary', { signal })
  if (!resp.ok) throw new Error(await extractError(resp, 'MIMO summary fetch failed'))
  return resp.json()
}
