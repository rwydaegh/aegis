import { useEffect, useRef, useState } from 'react'
import { arrayMax } from '@/lib/colormap'
import { useLabStore } from './store'
import { useLabGpuStatus } from './useLabGpuStatus'

// Jet gradient (top = hot) matching jetColor() used by the mesh heatmap.
const JET_GRADIENT_CSS =
  'linear-gradient(to bottom, rgb(128,0,0), rgb(255,0,0), rgb(255,128,0), rgb(255,255,0), rgb(128,255,128), rgb(0,255,255), rgb(0,128,255), rgb(0,0,255), rgb(0,0,128))'

const CARD = {
  background: 'rgba(13, 13, 18, 0.85)',
  border: '1px solid #1e1e26',
  borderRadius: 8,
  color: '#ddd',
} as const

function fmt(value: number | null | undefined, unit = ''): string {
  if (value == null || !isFinite(value)) return '--'
  const a = Math.abs(value)
  if (a !== 0 && (a < 1e-2 || a >= 1e4)) return `${value.toExponential(2)}${unit}`
  return `${value.toPrecision(3)}${unit}`
}

// --- Computing pill: shimmer + elapsed seconds + per-stage breakdown ----------
function ComputingPill() {
  const computing = useLabStore((s) => s.computing)
  const stats = useLabStore((s) => s.stats)
  const [elapsed, setElapsed] = useState(0)
  const [expanded, setExpanded] = useState(false)
  const startRef = useRef(0)
  const seenComputeRef = useRef(false)

  useEffect(() => {
    if (!computing) return
    seenComputeRef.current = true
    startRef.current = performance.now()
    setElapsed(0)
    const id = setInterval(() => setElapsed(performance.now() - startRef.current), 100)
    return () => clearInterval(id)
  }, [computing])

  const t = stats?.timings
  // First compute of a session pays cold caches + numba JIT; flag it so a slow
  // first run does not read as "stuck".
  const coldStart = computing && elapsed > 1500 && t == null

  if (!computing && !t) return null

  return (
    <div
      style={{ ...CARD, padding: '6px 12px', fontSize: 13, minWidth: 150, cursor: t ? 'pointer' : 'default' }}
      onClick={() => t && setExpanded((e) => !e)}
    >
      {computing ? (
        <span className="shimmer-text" style={{ fontWeight: 500 }}>
          {coldStart ? 'Warming up' : 'Computing'} ({(elapsed / 1000).toFixed(1)}s)
          {coldStart && <span style={{ opacity: 0.6, fontSize: 10 }}> first run</span>}
        </span>
      ) : (
        <span style={{ color: '#8fa', display: 'flex', justifyContent: 'space-between', gap: 10 }}>
          <span>Done in {fmt((t?.total_ms ?? 0) / 1000, ' s')}</span>
          <span style={{ opacity: 0.5 }}>{expanded ? '▾' : '▸'}</span>
        </span>
      )}
      {!computing && t && expanded && (
        <div style={{ marginTop: 6, fontSize: 11, color: '#9aa', fontFamily: 'monospace', lineHeight: 1.5 }}>
          {t.pose_body_ms != null && <div>pose body {t.pose_body_ms.toFixed(0)} ms</div>}
          {t.dose_ms != null && <div>dose {t.dose_ms.toFixed(0)} ms</div>}
          {t.payload_bytes != null && <div>payload {(t.payload_bytes / 1024).toFixed(0)} KB</div>}
        </div>
      )}
    </div>
  )
}

// --- GPU status pill: reuses the shared /api/gpu/status endpoint --------------
function GpuPill() {
  const gpu = useLabGpuStatus()
  if (!gpu || !gpu.enabled) return null
  const warm = gpu.warm
  return (
    <div
      style={{
        ...CARD,
        padding: '5px 10px',
        fontSize: 12,
        display: 'flex',
        alignItems: 'center',
        gap: 7,
        color: warm ? '#7ee29a' : '#e2c07e',
      }}
      title={warm ? 'Modal ray-tracing GPU is warm' : 'Modal GPU is asleep (first RT run wakes it, ~30s)'}
    >
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: warm ? '#7ee29a' : '#e2c07e',
          animation: warm ? undefined : 'labPulse 1.6s ease-in-out infinite',
        }}
      />
      {warm ? 'GPU ready' : 'GPU asleep'}
    </div>
  )
}

// --- Color bar + exposure metrics (shown once a result exists) ----------------
function ColorBarMetrics() {
  const sab = useLabStore((s) => s.sab)
  const stats = useLabStore((s) => s.stats)
  const averaging = useLabStore((s) => s.averaging)
  if (!sab || !stats) return null

  const peak = arrayMax(sab)
  const N = 5
  const ticks = Array.from({ length: N }, (_, i) => {
    const frac = i / (N - 1)
    return { label: fmt(peak * (1 - frac)), pct: frac }
  })

  // The 4 cm^2 / ICNIRP verdict is filled by the deferred second pass; show a
  // "computing" state while it runs rather than a stale or fallback value.
  const avgPending = averaging && stats.peak_sab_averaged == null
  const compliant = stats.compliant
  const badge =
    compliant == null
      ? avgPending
        ? { text: 'checking...', color: '#aab', bg: 'rgba(136,136,136,0.15)' }
        : { text: 'n/a', color: '#888', bg: 'rgba(136,136,136,0.15)' }
      : compliant
        ? { text: 'PASS', color: '#7ee29a', bg: 'rgba(126,226,154,0.15)' }
        : { text: 'OVER LIMIT', color: '#e27e7e', bg: 'rgba(226,126,126,0.15)' }

  return (
    <div style={{ ...CARD, padding: 12, width: 188 }}>
      <div style={{ fontSize: 12, color: '#aab', marginBottom: 8 }}>
        Absorbed power density S<sub>ab</sub> (W/m<sup>2</sup>)
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <div style={{ position: 'relative', width: 54, height: 200 }}>
          {ticks.map(({ label, pct }, i) => (
            <span
              key={i}
              style={{
                position: 'absolute',
                right: 0,
                top: pct * 200 - 7,
                fontSize: 11,
                fontFamily: 'monospace',
                color: '#ccd',
                whiteSpace: 'nowrap',
              }}
            >
              {label}
            </span>
          ))}
        </div>
        <div style={{ width: 16, height: 200, borderRadius: 3, background: JET_GRADIENT_CSS, border: '1px solid #2a2a33' }} />
      </div>

      <div style={{ marginTop: 12, fontSize: 12, lineHeight: 1.8 }}>
        <Metric label="Peak Sab" value={fmt(stats.peak_sab, ' W/m²')} />
        {stats.peak_sab_averaged != null ? (
          <Metric label="Peak 4 cm²" value={fmt(stats.peak_sab_averaged, ' W/m²')} />
        ) : avgPending ? (
          <Metric label="Peak 4 cm²" value="computing…" />
        ) : null}
        <Metric label="Absorbed" value={fmt(stats.p_abs_mw, ' mW')} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
          <span style={{ color: '#99a' }}>ICNIRP</span>
          <span style={{ color: badge.color, background: badge.bg, padding: '1px 7px', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
            {badge.text}
          </span>
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
      <span style={{ color: '#99a' }}>{label}</span>
      <span style={{ fontFamily: 'monospace', color: '#dde' }}>{value}</span>
    </div>
  )
}

// Overlay container. Mounted inside the scene column of LabModule.
export default function LabHud() {
  return (
    <>
      <div style={{ position: 'absolute', top: 16, right: 16, zIndex: 10, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
        <GpuPill />
        <ComputingPill />
      </div>
      <div style={{ position: 'absolute', bottom: 16, left: 16, zIndex: 10 }}>
        <ColorBarMetrics />
      </div>
      <style>{'@keyframes labPulse{0%,100%{opacity:0.3}50%{opacity:1}}'}</style>
    </>
  )
}
