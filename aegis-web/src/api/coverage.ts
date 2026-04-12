import type { CoverageResponse } from './types'
import { fetchWithRetry } from './client'

export async function fetchCoverage(): Promise<CoverageResponse> {
  const resp = await fetchWithRetry('/api/basestations/coverage')
  if (!resp.ok) {
    throw new Error(`Coverage fetch failed: ${resp.status}`)
  }
  return resp.json()
}

/** Bytes per site record in the binary coverage format. */
const BYTES_PER_SITE = 12 // lat(f4) + lon(f4) + op(u1) + tech(u1) + region(u1) + count(u1)

/** Decode base64 sites binary into typed arrays. */
export function decodeSitesBinary(
  b64: string,
  count: number,
): {
  latitudes: Float32Array
  longitudes: Float32Array
  opIndices: Uint8Array
  techIndices: Uint8Array
  regionIndices: Uint8Array
  antennaCounts: Uint8Array
} {
  const raw = Uint8Array.from(atob(b64), c => c.charCodeAt(0))
  const expectedBytes = count * BYTES_PER_SITE
  if (raw.byteLength < expectedBytes) {
    throw new Error(
      `Coverage binary truncated: expected ${expectedBytes} bytes for ${count} sites, got ${raw.byteLength}`,
    )
  }

  const latitudes = new Float32Array(count)
  const longitudes = new Float32Array(count)
  const opIndices = new Uint8Array(count)
  const techIndices = new Uint8Array(count)
  const regionIndices = new Uint8Array(count)
  const antennaCounts = new Uint8Array(count)

  const view = new DataView(raw.buffer)
  for (let i = 0; i < count; i++) {
    const offset = i * BYTES_PER_SITE
    latitudes[i] = view.getFloat32(offset, true)
    longitudes[i] = view.getFloat32(offset + 4, true)
    opIndices[i] = raw[offset + 8]
    techIndices[i] = raw[offset + 9]
    regionIndices[i] = raw[offset + 10]
    antennaCounts[i] = raw[offset + 11]
  }

  return { latitudes, longitudes, opIndices, techIndices, regionIndices, antennaCounts }
}
