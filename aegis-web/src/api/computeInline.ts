import type { ComputeResult } from './client'
import type { PosedMeshData } from '@/hooks/usePoseExtract'
import { packMeshBinary } from '@/hooks/usePoseExtract'
import { parseSabBinary } from './binary'

/**
 * Send a posed mesh binary to the compute endpoint and parse the response.
 * Uses octet-stream with params in X-Compute-Params header.
 */
export async function computeWithInlineMesh(
  meshData: PosedMeshData,
  params: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<ComputeResult> {
  const binary = packMeshBinary(meshData)
  const allParams = { ...params, n_triangles: meshData.nTriangles }

  const res = await fetch('/api/compute', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/octet-stream',
      'X-Compute-Params': JSON.stringify(allParams),
    },
    body: binary,
    signal,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error((err as Record<string, string>).error || res.statusText)
  }

  // Parse response: binary sab + X-Stats header (same format as computeEndpoint)
  const statsRaw = res.headers.get('X-Stats')
  const stats = statsRaw ? JSON.parse(statsRaw) : {}

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
