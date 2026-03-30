import { useSimulationStore } from '@/stores/simulation'
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import { useUIStore } from '@/stores/ui'
import type { QuantityKey } from '@/api/types'
import Tex from '@/components/ui/Tex'

function computeMaxPowerDbm(checks: Array<{ ratio: number }>, currentPowerDbm: number): number | null {
  if (checks.length === 0) return null
  const maxRatio = Math.max(...checks.map(c => c.ratio))
  if (maxRatio <= 0) return null
  // P_max = P_ref / maxRatio (linear), convert to dB offset
  return currentPowerDbm - 10 * Math.log10(maxRatio)
}

const LABEL_TEX: Record<string, string> = {
  'S_ab (4 cm^2)': 'S_\\text{ab}\\;(4\\,\\text{cm}^2)',
  'S_ab (1 cm^2)': 'S_\\text{ab}\\;(1\\,\\text{cm}^2)',
  'SAR_wb': '\\text{SAR}_\\text{wb}',
  'S_inc (local)': 'S_\\text{inc}\\;(\\text{local})',
  'S_inc (whole-body)': 'S_\\text{inc}\\;(\\text{wb})',
}

const LABEL_TO_KEY: Record<string, QuantityKey> = {
  'S_ab (4 cm^2)': 'sab_4cm2',
  'S_ab (1 cm^2)': 'sab_1cm2',
  'SAR_wb': 'sar_wb',
  'S_inc (local)': 'sinc_local',
  'S_inc (whole-body)': 'sinc_wb',
}

export default function CompliancePanel() {
  const { stats } = useActiveSimulation()
  const enabledQuantities = useSimulationStore(s => s.enabledQuantities)
  const scenario = useUIStore(s => s.exposureScenario)
  const isComputing = useUIStore(s => s.isComputing)
  if (!stats?.compliance) return null
  const { compliance } = stats

  const visibleChecks = compliance.checks.filter(check => {
    const key = LABEL_TO_KEY[check.label]
    return key ? enabledQuantities.has(key) : true
  })

  return (
    <div
      className={isComputing ? 'shimmer-panel' : ''}
      style={{
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

      {visibleChecks.length === 0 ? (
        <div style={{ color: '#666', fontSize: '11px', fontStyle: 'italic' }}>
          Enable quantities to see compliance checks
        </div>
      ) : visibleChecks.map((check, i) => {
        const color = !check.pass ? '#f87171' : check.ratio > 0.8 ? '#fbbf24' : '#4ade80'
        const status = !check.pass ? 'FAIL' : check.ratio > 0.8 ? 'WARN' : 'PASS'
        const tex = LABEL_TEX[check.label]
        return (
          <div key={i} style={{ marginBottom: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#e0e0e0', gap: '8px', alignItems: 'baseline' }}>
              <span style={{ flex: 1 }}>{tex ? <Tex math={tex} /> : check.label}</span>
              <span style={{ whiteSpace: 'nowrap' }}>{check.value.toFixed(2)} / {check.limit.toFixed(2)} {check.unit}</span>
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

      {compliance.margin_db != null && (() => {
        const powerDbm = useSimulationStore.getState().powerDbm
        const maxPowerDbm = computeMaxPowerDbm(compliance.checks, powerDbm)
        return (
          <div style={{ borderTop: '1px solid #333', paddingTop: '8px', marginTop: '8px', color: '#888' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Margin</span>
              <span style={{ color: compliance.margin_db >= 0 ? '#4ade80' : '#f87171' }}>
                {compliance.margin_db > 0 ? '+' : ''}{compliance.margin_db.toFixed(1)} dB
              </span>
            </div>
            {maxPowerDbm != null && (
              <div
                style={{ display: 'flex', justifyContent: 'space-between', cursor: 'pointer' }}
                title="Click to set TX power to max compliant value"
                onClick={() => useSimulationStore.getState().setPowerDbm(parseFloat(maxPowerDbm.toFixed(1)))}
              >
                <span>Max TX power</span>
                <span style={{ color: '#93c5fd' }}>{maxPowerDbm.toFixed(1)} dBm</span>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Frequency</span>
              <span>{(compliance.freq_hz / 1e9).toFixed(1)} GHz</span>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
