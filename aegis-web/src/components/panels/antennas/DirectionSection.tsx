import { useAntennaStore, type AntennaConfig } from '@/stores/antenna'
import { NumInput } from './NumInput'
import { inputClass, labelClass, sectionClass } from './constants'

export function DirectionSection({ selected }: { selected: AntennaConfig }) {
  const updateAntenna = useAntennaStore(s => s.updateAntenna)

  const [bx, by, bz] = selected.arrayConfig.broadside
  const horLen = Math.sqrt(bx * bx + bz * bz)
  const azDeg = Math.atan2(bx, -bz) * (180 / Math.PI)
  const tiltDeg = Math.atan2(-by, horLen) * (180 / Math.PI)

  const setBroadside = (newBs: [number, number, number]) => {
    updateAntenna(selected.id, {
      focusPoint: null,
      arrayConfig: { ...selected.arrayConfig, broadside: newBs },
    })
  }

  return (
    <div>
      <p className={sectionClass}>Direction</p>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className={labelClass}>Azimuth</label>
          <NumInput
            className={inputClass}
            value={Math.round(azDeg * 10) / 10}
            min={-180}
            max={180}
            step={5}
            onChange={v => {
              const azRad = v * Math.PI / 180
              const tiltRad = tiltDeg * Math.PI / 180
              const cosTilt = Math.cos(tiltRad)
              setBroadside([
                Math.sin(azRad) * cosTilt,
                -Math.sin(tiltRad),
                -Math.cos(azRad) * cosTilt,
              ])
            }}
          />
          <span className="text-[10px] text-muted-foreground mt-0.5 block">deg</span>
        </div>
        <div>
          <label className={labelClass}>Tilt</label>
          <NumInput
            className={inputClass}
            value={Math.round(tiltDeg * 10) / 10}
            min={-90}
            max={90}
            step={1}
            onChange={v => {
              const azRad = azDeg * Math.PI / 180
              const tiltRad = v * Math.PI / 180
              const cosTilt = Math.cos(tiltRad)
              setBroadside([
                Math.sin(azRad) * cosTilt,
                -Math.sin(tiltRad),
                -Math.cos(azRad) * cosTilt,
              ])
            }}
          />
          <span className="text-[10px] text-muted-foreground mt-0.5 block">deg (+down)</span>
        </div>
      </div>
    </div>
  )
}
