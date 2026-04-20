import { useSceneStore } from '@/stores/scene'

export function useIsRtBlocked(): boolean {
  const pathSource = useSceneStore(s => s.pathSource)
  const rtSource = useSceneStore(s => s.rtSource)
  const loadedScenePath = useSceneStore(s => s.loadedScenePath)
  const caps = useSceneStore(s => s.capabilities)

  if (pathSource !== 'rt') return false
  const hasGeometry = Boolean(loadedScenePath) || Boolean(caps?.has_voxels) || Boolean(caps?.has_env_mesh)
  if (hasGeometry) return false
  // Sionna accepts the same fallbacks as DiffeRT here
  return rtSource === 'differt' || rtSource === 'sionna'
}

export default function RtBlockedBanner() {
  const blocked = useIsRtBlocked()
  if (!blocked) return null

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-auto rounded-md border border-amber-500/40 bg-amber-500/15 px-3 py-2
        shadow-lg backdrop-blur-sm text-xs font-mono text-amber-300 max-w-md"
    >
      <div className="flex items-start gap-2">
        <svg
          className="w-3.5 h-3.5 mt-0.5 shrink-0"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M8 1.5 15 14H1L8 1.5Z" />
          <path d="M8 6v4" />
          <path d="M8 12v.01" />
        </svg>
        <div>
          <div className="font-semibold">Ray tracing is blocked</div>
          <div className="opacity-80 mt-0.5">
            No environment geometry loaded. Frequency, power, and other inputs will be ignored
            until you load OSM buildings, 3D Tiles, or a scene file, or disable ray tracing.
          </div>
        </div>
      </div>
    </div>
  )
}
