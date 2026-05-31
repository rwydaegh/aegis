import { create } from 'zustand'
import type { ReplayArtifact, ReplayFrame } from '@/api/replayTypes'

interface ReplayStore {
  /** When true, SceneRoot renders the replay scene instead of the live app. */
  active: boolean
  artifact: ReplayArtifact | null
  frameIndex: number
  error: string | null

  setActive: (a: boolean) => void
  loadArtifact: (a: ReplayArtifact) => void
  clear: () => void
  setFrameIndex: (i: number) => void
  setError: (e: string | null) => void
}

export const useReplayStore = create<ReplayStore>((set, get) => ({
  active: false,
  artifact: null,
  frameIndex: 0,
  error: null,

  setActive: (a) => set({ active: a }),
  loadArtifact: (a) => set({ artifact: a, frameIndex: 0, active: true, error: null }),
  clear: () => set({ artifact: null, frameIndex: 0, active: false, error: null }),
  setFrameIndex: (i) => {
    const a = get().artifact
    if (!a) return
    const n = a.frames.length
    set({ frameIndex: Math.max(0, Math.min(n - 1, i)) })
  },
  setError: (e) => set({ error: e }),
}))

/** Current frame, or null. */
export function currentFrame(): ReplayFrame | null {
  const { artifact, frameIndex } = useReplayStore.getState()
  return artifact?.frames[frameIndex] ?? null
}
