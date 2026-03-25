import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useBodyLoader } from '@/hooks/useBodyLoader'
import BodyMeshInstance from './BodyMeshInstance'

export default function BodyMesh() {
  useBodyLoader()

  const geometry = useSceneStore(s => s.bodyGeometry)
  const sabArray = useSimulationStore(s => s.sabArray)
  const sabAveragedArray = useSimulationStore(s => s.sabAveragedArray)
  const sincArray = useSimulationStore(s => s.sincArray)
  const sab1cm2AveragedArray = useSimulationStore(s => s.sab1cm2AveragedArray)
  const stats = useSimulationStore(s => s.stats)
  const compliance = useSimulationStore(s => s.compliance)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const bodyRotationY = useSimulationStore(s => s.bodyRotationY)

  return (
    <BodyMeshInstance
      geometry={geometry}
      sabArray={sabArray}
      sabAveragedArray={sabAveragedArray}
      sincArray={sincArray}
      sab1cm2AveragedArray={sab1cm2AveragedArray}
      stats={stats}
      compliance={compliance}
      position={bodyOffset}
      rotationY={bodyRotationY}
    />
  )
}
