import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import type { QuantityKey } from '@/api/types'
import Tex from '@/components/ui/Tex'
import type { ReactNode } from 'react'

interface QtyRow {
  key: QuantityKey
  label: ReactNode
  spatial: boolean
}

const BASIC_RESTRICTION: QtyRow[] = [
  { key: 'sab_4cm2', label: <Tex math={'S_{\\text{ab}}\\,(4\\,\\text{cm}^2)'} />, spatial: true },
  { key: 'sab_1cm2', label: <Tex math={'S_{\\text{ab}}\\,(1\\,\\text{cm}^2)'} />, spatial: true },
  { key: 'sar_wb', label: <Tex math={'\\text{SAR}_{\\text{wb}}'} />, spatial: false },
]

const REFERENCE_LEVEL: QtyRow[] = [
  { key: 'sinc_local', label: <Tex math={'S_{\\text{inc}}\\,(\\text{local})'} />, spatial: true },
  { key: 'sinc_wb', label: <Tex math={'S_{\\text{inc}}\\,(\\text{wb})'} />, spatial: false },
]

export default function QuantitiesPanel() {
  const enabledQuantities = useSimulationStore(s => s.enabledQuantities)
  const displayQuantity = useSimulationStore(s => s.displayQuantity)
  const toggleQuantity = useSimulationStore(s => s.toggleQuantity)
  const setDisplayQuantity = useSimulationStore(s => s.setDisplayQuantity)
  const ratioMode = useUIStore(s => s.ratioMode)
  const setRatioMode = useUIStore(s => s.setRatioMode)
  const freqGhz = useSimulationStore(s => s.freqGhz)

  const isActive = (key: QuantityKey) => displayQuantity === key
  const isEnabled = (key: QuantityKey) => enabledQuantities.has(key)

  function renderRow(row: QtyRow) {
    const enabled = isEnabled(row.key)
    const active = isActive(row.key)
    const disabled = row.key === 'sab_1cm2' && freqGhz <= 30
    const canDisplay = row.spatial && enabled && !disabled

    const rowClass = 'flex items-center gap-1.5 py-1 px-1.5 rounded cursor-pointer transition-colors '
      + (active ? 'bg-primary/15 border-l-2 border-primary ' : 'border-l-2 border-transparent ')
      + (disabled ? 'opacity-30 pointer-events-none' : !enabled ? 'opacity-50' : '')

    return (
      <div
        key={row.key}
        className={rowClass}
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
        <span className="flex-1">{row.label}</span>
        {active && <span className="text-[10px] text-primary">{'▸'}</span>}
      </div>
    )
  }

  const sabCardClass = 'flex items-center justify-between px-2 py-1.5 rounded cursor-pointer transition-colors '
    + (displayQuantity === 'sab'
      ? 'bg-primary/15 border-l-2 border-primary'
      : 'bg-muted/30 border-l-2 border-transparent hover:bg-muted/50')

  const ratioBtnClass = 'text-[11px] px-2.5 py-0.5 rounded border transition-colors cursor-pointer '
    + (ratioMode && displayQuantity !== 'sab'
      ? 'border-primary/40 bg-primary/15 text-primary'
      : 'border-border bg-muted/50 text-foreground hover:bg-muted')
    + (displayQuantity === 'sab' ? ' opacity-40 cursor-not-allowed' : '')

  return (
    <div className="space-y-2">
      <div
        className={sabCardClass}
        onClick={() => setDisplayQuantity('sab')}
      >
        <span className="text-xs font-medium"><Tex math={'S_{\\text{ab}}'} /></span>
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
          className={ratioBtnClass}
          title={displayQuantity === 'sab' ? 'Ratio mode not available for un-averaged Sab' : 'Toggle ratio to ICNIRP limit'}
        >
          {ratioMode && displayQuantity !== 'sab' ? 'On' : 'Off'}
        </button>
      </div>
    </div>
  )
}
