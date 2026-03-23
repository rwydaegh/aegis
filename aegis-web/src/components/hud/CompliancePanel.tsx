import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import Tex from '@/components/ui/Tex'

const LABEL_TEX: Record<string, string> = {
  'S_ab (4 cm^2)': 'S_\\text{ab}\\;(4\\,\\text{cm}^2)',
  'S_ab (1 cm^2)': 'S_\\text{ab}\\;(1\\,\\text{cm}^2)',
  'SAR_wb': '\\text{SAR}_\\text{wb}',
  'S_inc (local)': 'S_\\text{inc}\\;(\\text{local})',
  'S_inc (whole-body)': 'S_\\text{inc}\\;(\\text{wb})',
}

function checkToQuantityKey(label: string): string | null {
  if (label.includes('4 cm')) return 'sab_4cm2'
  if (label.includes('1 cm')) return 'sab_1cm2'
  if (label.includes('SAR')) return 'sar_wb'
  if (label.includes('S_inc') && label.includes('local')) return 'sinc_local'
  if (label.includes('S_inc') && label.includes('whole')) return 'sinc_wb'
  return null
}

export default function CompliancePanel() {
  const stats = useSimulationStore(s => s.stats)
  const scenario = useUIStore(s => s.exposureScenario)
  const enabledQuantities = useSimulationStore(s => s.enabledQuantities)

  if (!stats?.compliance) return null
  const { compliance } = stats

  const visibleChecks = compliance.checks.filter(check => {
    const key = checkToQuantityKey(check.label)
    return key === null || enabledQuantities.has(key as import('@/api/types').QuantityKey)
  })

  if (visibleChecks.length === 0) return null

  return (
    <div style={{
      background: 'rgba(0,0,0,0.7)',
      padding: '12px',
      borderRadius: '8px',
      fontFamily: 'monospace',
      fontSize: '12px',
      minWidth: '280px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ color: '#888', fontSize: '10px', letterSpacing: '1px' }}>
          COMPLIANCE (ICNIRP 2020)
        </span>
        <span style={{ color: '#93c5fd', fontSize: '10px' }}>
          {scenario === 'general_public' ? 'General Public' : 'Occupational'}
        </span>
      </div>

      {visibleChecks.map((check, i) => {
        const color = !check.pass ? '#f87171' : check.ratio > 0.8 ? '#fbbf24' : '#4ade80'
        const status = !check.pass ? 'FAIL' : check.ratio > 0.8 ? 'WARN' : 'PASS'
        const tex = LABEL_TEX[check.label]
        return (
          <div key={i} style={{ marginBottom: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#e0e0e0', gap: '8px', alignItems: 'baseline' }}>
              <span style={{ flex: 1 }}>{tex ? <Tex math={tex} /> : check.label}</span>
              <span style={{ whiteSpace: 'nowrap' }}>{check.value.toFixed(1)} / {check.limit.toFixed(1)} {check.unit}</span>
              <span style={{ color, fontWeight: 'bold', minWidth: '35px', textAlign: 'right' }}>{status}</span>
            </div>
            <div style={{ background: '#333', borderRadius: '2px', height: '3px', marginTop: '2px' }}>
              <div style={{
                background: color,
                width: `${Math.min(check.ratio * 100, 100)}%`,
                height: '100%',
                borderRadius: '2px',
              }} />
            </div>
          </div>
        )
      })}

      {compliance.margin_db != null && (
        <div style={{ borderTop: '1px solid #333', paddingTop: '8px', marginTop: '8px', color: '#888' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Margin</span>
            <span style={{ color: compliance.margin_db >= 0 ? '#4ade80' : '#f87171' }}>
              {compliance.margin_db > 0 ? '+' : ''}{compliance.margin_db.toFixed(1)} dB
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Frequency</span>
            <span>{(compliance.freq_hz / 1e9).toFixed(1)} GHz</span>
          </div>
        </div>
      )}
    </div>
  )
}
