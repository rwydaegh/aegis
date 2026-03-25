import type {
  ArrayConfig,
  MIMOUserConfig,
  MIMOComputeRequest,
  MIMOComputeResponse,
  MIMOSummary,
  DosimetryStats,
} from './types'
import { toServer } from './coordinates'

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
  const res = await fetch('/api/mimo/compute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok) throw new Error(`MIMO compute failed: ${res.status}`)
  return res.json()
}

/** Fetch a single user's sab result as binary. */
export async function fetchMIMOResult(
  userId: string,
  signal?: AbortSignal,
): Promise<{ sab: Float32Array; stats: DosimetryStats }> {
  const resp = await fetch(`/api/mimo/result/${userId}`, { signal })
  if (!resp.ok) throw new Error(`MIMO result fetch failed: ${resp.status}`)
  const statsHeader = resp.headers.get('X-Stats')
  const stats: DosimetryStats = statsHeader ? JSON.parse(statsHeader) : {}
  const buf = await resp.arrayBuffer()
  const sab = new Float32Array(buf)
  return { sab, stats }
}

/** Fetch summary stats for all users. */
export async function fetchMIMOSummary(
  signal?: AbortSignal,
): Promise<MIMOSummary> {
  const resp = await fetch('/api/mimo/summary', { signal })
  if (!resp.ok) throw new Error(`MIMO summary fetch failed: ${resp.status}`)
  return resp.json()
}
