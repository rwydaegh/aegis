import { fetchWithRetry, type RtConfig } from '@/api/client'

const BASE = ''

export interface OptimizeRequest {
  mode: string
  max_iters?: number
  // MIMO peak
  G_tilde_real?: number[][][]
  G_tilde_imag?: number[][][]
  x_init_real?: number[]
  x_init_imag?: number[]
  p_max?: number
  signal_threshold?: number
  // Tilt/power
  antenna_direction?: number[]
  tilt_init_deg?: number
  power_init_dbm?: number
  icnirp_limit?: number
  // Placement
  center?: number[]
  grid_size?: number
  grid_spacing?: number
  constraint_axis?: string
  constraint_value?: number
  body_name?: string
  body_offset?: number[]
  body_rotation_y?: number
  power_dbm?: number
  skin_model?: string
  freq_hz?: number
  dosimetry_mode?: string
  fresnel?: boolean
  polarisation?: boolean
  curvature?: boolean
  diffraction?: boolean
  scene_path?: string
  rt_config?: RtConfig
}

export interface SSEEvent {
  iter?: number
  mode?: string
  objective?: number
  grad_norm?: number
  sab_b64?: string
  params?: Record<string, unknown>
  stats?: Record<string, unknown>
  converged?: boolean
  done?: boolean
  cancelled?: boolean
  error?: boolean
  message?: string
  progress?: number
  is_best?: boolean
  reason?: string
  total_iters?: number
  total_time_s?: number
  best?: Record<string, unknown>
  constraint_satisfied?: boolean
}

/**
 * Start an optimization run via SSE streaming.
 * Returns an async generator that yields parsed SSE events.
 * Pass an AbortSignal to cancel.
 */
export async function* streamOptimization(
  request: OptimizeRequest,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent> {
  const res = await fetchWithRetry(`${BASE}/api/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Optimize request failed: ${res.status} ${text}`)
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event: SSEEvent = JSON.parse(line.slice(6))
            yield event
          } catch {
            // skip malformed lines
          }
        }
      }
    }

    if (buffer.startsWith('data: ')) {
      try {
        yield JSON.parse(buffer.slice(6))
      } catch {
        // ignore
      }
    }
  } finally {
    reader.cancel().catch(() => {})
  }
}

export async function cancelOptimization(): Promise<void> {
  await fetchWithRetry(`${BASE}/api/optimize/cancel`, { method: 'POST' })
}

/** Decode a base64-encoded float32 SAB array. */
export function decodeSabB64(b64: string): Float32Array {
  const binary = atob(b64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return new Float32Array(bytes.buffer)
}
