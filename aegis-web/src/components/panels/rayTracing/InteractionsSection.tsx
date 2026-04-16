import { useSceneStore } from '@/stores/scene'
import type { Backend } from './capabilities'
import { capFor } from './capabilities'
import { CheckboxRow } from './Rows'
import { sectionClass } from './styles'

export default function InteractionsSection({ backend }: { backend: Backend }) {
  const rc = useSceneStore(s => s.rtConfig)
  const setRtConfig = useSceneStore(s => s.setRtConfig)

  const cap = (param: string) => capFor(backend, param, { method: rc.method, diffraction: rc.diffraction })

  return (
    <>
      <div className={sectionClass}>Interactions</div>

      <div className="flex flex-col gap-1.5 mt-1">
        <CheckboxRow
          cap={cap('los')}
          label="LOS"
          checked={rc.los}
          onChange={v => setRtConfig({ los: v })}
        />
        <CheckboxRow
          cap={cap('specularReflection')}
          label="Specular reflection"
          checked={rc.specularReflection}
          onChange={v => setRtConfig({ specularReflection: v })}
        />
        <CheckboxRow
          cap={cap('diffuseReflection')}
          label="Diffuse reflection"
          checked={rc.diffuseReflection}
          onChange={v => setRtConfig({ diffuseReflection: v })}
        />
        <CheckboxRow
          cap={cap('refraction')}
          label="Refraction"
          checked={rc.refraction}
          onChange={v => setRtConfig({ refraction: v })}
        />
        <CheckboxRow
          cap={cap('diffraction')}
          label="Diffraction"
          checked={rc.diffraction}
          onChange={v => setRtConfig({ diffraction: v })}
        />
        <CheckboxRow
          cap={cap('edgeDiffraction')}
          label="Edge diffraction"
          checked={rc.edgeDiffraction}
          onChange={v => setRtConfig({ edgeDiffraction: v })}
          indent
        />
        <CheckboxRow
          cap={cap('diffractionLitRegion')}
          label="Diffraction lit region"
          checked={rc.diffractionLitRegion}
          onChange={v => setRtConfig({ diffractionLitRegion: v })}
          indent
        />
      </div>
    </>
  )
}
