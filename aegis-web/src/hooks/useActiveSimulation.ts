import { useSimulationStore } from '@/stores/simulation'
import { useMIMOStore } from '@/stores/mimo'
import { useSceneStore } from '@/stores/scene'
import type { ScenePos } from '@/api/coordinates'
import type { DosimetryStats, ComplianceInfo } from '@/api/types'
import type { BufferGeometry } from 'three'

export interface ActiveSimulation {
  sabArray: Float32Array | null
  sabAveragedArray: Float32Array | null
  sincArray: Float32Array | null
  sab1cm2AveragedArray: Float32Array | null
  stats: DosimetryStats | null
  compliance: ComplianceInfo | null
  bodyGeometry: BufferGeometry | null
  bodyOffset: ScenePos
  bodyRotationY: number
}

export function useActiveSimulation(): ActiveSimulation {
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const focusedUserId = useMIMOStore(s => s.focusedUserId)
  const focusedUser = useMIMOStore(s =>
    s.focusedUserId ? s.users.get(s.focusedUserId) ?? null : null
  )

  // Single-user fallback values (always called for hooks rules)
  const singleSab = useSimulationStore(s => s.sabArray)
  const singleSabAvg = useSimulationStore(s => s.sabAveragedArray)
  const singleSinc = useSimulationStore(s => s.sincArray)
  const singleSab1cm2 = useSimulationStore(s => s.sab1cm2AveragedArray)
  const singleStats = useSimulationStore(s => s.stats)
  const singleCompliance = useSimulationStore(s => s.compliance)
  const singleGeometry = useSceneStore(s => s.bodyGeometry)
  const singleOffset = useSimulationStore(s => s.bodyOffset)
  const singleRotation = useSimulationStore(s => s.bodyRotationY)

  if (mimoEnabled && focusedUser) {
    return {
      sabArray: focusedUser.sabArray,
      sabAveragedArray: null,
      sincArray: null,
      sab1cm2AveragedArray: null,
      stats: focusedUser.stats,
      compliance: focusedUser.stats?.compliance ?? null,
      bodyGeometry: focusedUser.bodyGeometry,
      bodyOffset: focusedUser.position,
      bodyRotationY: focusedUser.orientation,
    }
  }

  return {
    sabArray: singleSab,
    sabAveragedArray: singleSabAvg,
    sincArray: singleSinc,
    sab1cm2AveragedArray: singleSab1cm2,
    stats: singleStats,
    compliance: singleCompliance,
    bodyGeometry: singleGeometry,
    bodyOffset: singleOffset,
    bodyRotationY: singleRotation,
  }
}
