import { useState, useEffect } from 'react'
import { fetchSystemInfo } from '@/api/client'
import type { SystemInfo } from '@/api/types'

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
  return name
    .replace(/NVIDIA\s*/i, '')
    .replace(/GeForce\s*/i, '')
    .replace(/RTX\s*/i, '')
    .replace(/Quadro\s*/i, '')
    .trim()
}

function useServerInfo(): (ServerInfo & { gitCommit: string | null }) | null {
  const [info, setInfo] = useState<(ServerInfo & { gitCommit: string | null }) | null>(null)

  useEffect(() => {
    const poll = () => {
      fetchSystemInfo()
        .then((data: SystemInfo) => {
          setInfo({
            hostname: data.hostname,
            cpuPct: data.cpu_pct ?? null,
            cpuCores: data.cpu_cores ?? null,
            ramPct: data.ram_pct ?? null,
            ramTotalGb: data.ram_total_gb ?? null,
            gpuPct: data.gpu?.utilization_pct ?? null,
            gpuName: data.gpu?.name ? shortenGpuName(data.gpu.name) : null,
            gitCommit: data.git_commit ?? null,
          })
        })
        .catch(() => { /* server info is optional, silently ignore */ })
    }
    poll()
    const interval = setInterval(poll, 5000)
    return () => clearInterval(interval)
  }, [])

  return info
}

export default function ServerInfoBadge() {
  const info = useServerInfo()
  if (!info) return null

  const isCloud = info.gpuName != null
  const label = info.hostname === 'localhost' || info.hostname.startsWith('127.')
    ? 'LOCAL'
    : isCloud ? 'CLOUD' : info.hostname.split('.')[0].toUpperCase()
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
    <div className="pointer-events-none">
      <div className="bg-black/60 backdrop-blur-sm rounded-md border border-white/10 px-2.5 py-1.5 flex items-center gap-3">
        <span className={`text-[10px] font-mono font-medium select-none ${isCloud ? 'text-emerald-400' : 'text-blue-400'}`}>
          {label}{info.gitCommit ? ` ${info.gitCommit.slice(0, 7)}` : ''}
        </span>
        {items.length > 0 && (
          <>
            <span className="w-px h-3 bg-white/20" />
            {items.map(({ label, pct, spec }) => (
              <span key={label} className="text-[10px] text-white/80 font-mono select-none">
                {label} {pct}%{spec && ` (${spec})`}
              </span>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
