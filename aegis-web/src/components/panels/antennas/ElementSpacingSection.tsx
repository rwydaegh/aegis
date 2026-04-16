import { useAntennaStore, type AntennaArrayConfig, type AntennaConfig } from '@/stores/antenna'
import { useSimulationStore } from '@/stores/simulation'
import { NumInput } from './NumInput'
import { inputClass, labelClass, sectionClass } from './constants'

export function ElementSpacingSection({ selected }: { selected: AntennaConfig }) {
  const updateAntenna = useAntennaStore(s => s.updateAntenna)
  const freqGhz = useSimulationStore(s => s.freqGhz)
  const lambda_m = 3e8 / (freqGhz * 1e9)

  const updateArrayConfig = (partial: Partial<AntennaArrayConfig>) => {
    updateAntenna(selected.id, { arrayConfig: { ...selected.arrayConfig, ...partial } })
  }

  return (
    <div>
      <p className={sectionClass}>Element spacing</p>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className={labelClass}>d_h (wavelengths)</label>
          <NumInput
            className={inputClass}
            value={selected.arrayConfig.d_h_wavelengths}
            min={0.1} max={2.0} step={0.1}
            onChange={v => updateArrayConfig({ d_h_wavelengths: v })}
          />
        </div>
        <div>
          <label className={labelClass}>d_v (wavelengths)</label>
          <NumInput
            className={inputClass}
            value={selected.arrayConfig.d_v_wavelengths}
            min={0.1} max={2.0} step={0.1}
            onChange={v => updateArrayConfig({ d_v_wavelengths: v })}
          />
        </div>
      </div>
      <p className="text-[9px] text-muted-foreground/60 mt-1">
        {(selected.arrayConfig.d_h_wavelengths * lambda_m * 1000).toFixed(1)} mm x{' '}
        {(selected.arrayConfig.d_v_wavelengths * lambda_m * 1000).toFixed(1)} mm at{' '}
        {freqGhz} GHz
      </p>
    </div>
  )
}
