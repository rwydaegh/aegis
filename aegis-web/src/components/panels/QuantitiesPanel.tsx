import { useEffect } from 'react'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import type { QuantityKey } from '@/api/types'

interface QtyRow {
  key: QuantityKey
  label: string
  unit: string
  spatial: boolean
}

const BASIC_RESTRICTION: QtyRow[] = [
  { key: 'sab_4cm2', label: 'S_ab (4 cm²)', unit: 'W/m²', spatial: true },
  { key: 'sab_1cm2', label: 'S_ab (1 cm²)', unit: 'W/m²', spatial: true },
  { key: 'sar_wb', label: 'SAR_wb', unit: 'W/kg', spatial: false },
]

const REFERENCE_LEVEL: QtyRow[] = [
  { key: 'sinc_local', label: 'S_inc local', unit: 'W/m²', spatial: true },
  { key: 'sinc_wb', label: 'S_inc wb', unit: 'W/m²', spatial: false },
]

export default function QuantitiesPanel() {
  const enabledQuantities = useSimulationStore(s => s.enabledQuantities)
  const displayQuantity = useSimulationStore(s => s.displayQuantity)
  const toggleQuantity = useSimulationStore(s => s.toggleQuantity)
  const setDisplayQuantity = useSimulationStore(s => s.setDisplayQuantity)
  const ratioMode = useUIStore(s => s.ratioMode)
  const setRatioMode = useUIStore(s => s.setRatioMode)
  const freqGhz = useSimulationStore(s => s.freqGhz)
  const compliance = useSimulationStore(s => s.stats?.compliance)

  const isActive = (key: QuantityKey) => displayQuantity === key
  const isEnabled = (key: QuantityKey) => enabledQuantities.has(key)

  useEffect(() => {
    if (displayQuantity === 'sab_1cm2' && freqGhz <= 30) {
      setDisplayQuantity('sab')
    }
  }, [freqGhz, displayQuantity, setDisplayQuantity])

  function getLimit(key: QuantityKey): string | null {
    if (!compliance?.checks) return null
    const labelMap: Record<string, string> = {
      sab_4cm2: '4 cm',
      sab_1cm2: '1 cm',
      sar_wb: 'SAR',
      sinc_local: 'S_inc',
      sinc_wb: 'whole',
    }
    const search = labelMap[key]
    if (!search) return null
    const check = compliance.checks.find(c => c.label.includes(search))
    if (!check) return null
    return
  }

  function renderRow(row: QtyRow) {
    const enabled = isEnabled(row.key)
    const active = isActive(row.key)
    const disabled = row.key === 'sab_1cm2' && freqGhz <= 30
    const canDisplay = row.spatial && enabled && !disabled
    const limit = getLimit(row.key)

    return (
      <div
        key={row.key}
        className={}
        onClick={() => canDisplay && setDisplayQuantity(row.key)}
        title={disabled ? 'Only available above 30 GHz' : row.spatial ? 'Click to display on mesh' : 'Scalar quantity (no mesh display)'}
      >
        <input
          type="checkbox"
          checked={enabled && !disabled}
          disabled={disabled}
          onChange={(e) => { e.stopPropagation(); toggleQuantity(row.key) }}
          className="accent-primary w-3.5 h-3.5 cursor-pointer"
        />
        <span className="text-xs flex-1 truncate">{row.label}</span>
        {limit && <span className="text-[10px] text-muted-foreground ml-auto whitespace-nowrap">{limit}</span>}
        {active && <span className="text-[10px] text-primary">{'▸'}</span>}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div
        className={}
        onClick={() => setDisplayQuantity('sab')}
      >
        <span className="text-xs font-medium">S<sub>ab</sub></span>
        {displayQuantity === 'sab' && <span className="text-[10px] text-primary">{'▸'} displayed</span>}
      </div>

      <div className="flex gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-1 pb-1 border-b border-border">
            Basic restriction
          </div>
          {BASIC_RESTRICTION.map(renderRow)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-1 pb-1 border-b border-border">
            Reference level
          </div>
          {REFERENCE_LEVEL.map(renderRow)}
        </div>
      </div>

      <div className="flex items-center justify-between pt-1 border-t border-border">
        <span className="text-xs text-muted-foreground">Ratio mode</span>
        <button
          onClick={() => setRatioMode(!ratioMode)}
          disabled={displayQuantity === 'sab'}
          className={}
          title={displayQuantity === 'sab' ? 'Ratio mode not available for un-averaged S_ab' : 'Toggle ratio to ICNIRP limit'}
        >
          {ratioMode && displayQuantity !== 'sab' ? 'On' : 'Off'}
        </button>
      </div>
    </div>
  )
}
