import { useState, useEffect } from 'react'
import { fetchSystemInfo } from '@/api/client'

// ---------------------------------------------------------------------------
// Server info hook
// ---------------------------------------------------------------------------

interface ServerInfo {
  hostname: string
  cpuPct: number | null
  cpuCores: number | null
  ramPct: number | null
  ramTotalGb: number | null
  gpuPct: number | null
  gpuName: string | null
}

function shortenGpuName(name: string): string {
  // "NVIDIA RTX A4000" -> "A4000", "NVIDIA GeForce RTX 4090" -> "4090"
  return name
    .replace(/NVIDIA\s*/i, '')
    .replace(/GeForce\s*/i, '')
    .replace(/RTX\s*/i, '')
    .replace(/Quadro\s*/i, '')
    .trim()
}

function useServerInfo(): ServerInfo | null {
  const [info, setInfo] = useState<ServerInfo | null>(null)

  useEffect(() => {
    const poll = () => {
      fetchSystemInfo()
        .then(data => {
          const d = data as any
          setInfo({
            hostname: data.hostname,
            cpuPct: d.cpu_pct ?? null,
            cpuCores: d.cpu_cores ?? null,
            ramPct: d.ram_pct ?? null,
            ramTotalGb: d.ram_total_gb ?? null,
            gpuPct: d.gpu?.utilization_pct ?? null,
            gpuName: d.gpu?.name ? shortenGpuName(d.gpu.name) : null,
          })
        })
        .catch(() => {})
    }
    poll()
    const interval = setInterval(poll, 5000)
    return () => clearInterval(interval)
  }, [])

  return info
}

// ---------------------------------------------------------------------------
// Server info badge
// ---------------------------------------------------------------------------

export default function ServerInfoBadge() {
  const info = useServerInfo()
  if (!info) return null

  const items: Array<{ label: string; pct: number; spec: string }> = []

  if (info.cpuPct != null) {
    const spec = info.cpuCores ? `${info.cpuCores} cores` : ''
    items.push({ label: 'CPU', pct: info.cpuPct, spec })
  }
  if (info.ramPct != null) {
    const spec = info.ramTotalGb ? `${info.ramTotalGb} GB` : ''
    items.push({ label: 'RAM', pct: info.ramPct, spec })
  }
  if (info.gpuPct != null) {
    items.push({ label: 'GPU', pct: info.gpuPct, spec: info.gpuName ?? '' })
  }

  return (
    <div className="absolute bottom-3 right-3 pointer-events-none">
      <div className="flex items-center gap-3">
        {items.map(({ label, pct, spec }) => (
          <span key={label} className="text-[10px] text-muted-foreground/70 font-mono select-none">
            {label} {pct}%{spec && ` (${spec})`}
          </span>
        ))}
      </div>
    </div>
  )
}
