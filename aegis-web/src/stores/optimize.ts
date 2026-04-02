import { create } from 'zustand'

export type OptimizeMode = 'placement' | 'tilt_power' | 'mimo_peak'

export interface OptimizeConstraints {
  gridSize?: number
  gridSpacing?: number
  constraintAxis?: 'x' | 'y' | 'z'
  constraintValue?: number
  icnirpLimit?: number
  pMax?: number
  signalThreshold?: number
  maxIters?: number
}

export interface IterationResult {
  iter: number
  objective: number
  gradNorm?: number
  params: Record<string, unknown>
  stats?: Record<string, unknown>
  converged?: boolean
  done?: boolean
  error?: boolean
  message?: string
  progress?: number
  isBest?: boolean
}

interface OptimizeStore {
  mode: OptimizeMode | null
  constraints: OptimizeConstraints
  running: boolean
  currentIter: number
  history: IterationResult[]
  summary: string | null

  setMode: (mode: OptimizeMode | null) => void
  setConstraints: (c: Partial<OptimizeConstraints>) => void
  setRunning: (running: boolean) => void
  onIteration: (result: IterationResult) => void
  onDone: (summary: string) => void
  onError: (message: string) => void
  reset: () => void
}

export const useOptimizeStore = create<OptimizeStore>((set) => ({
  mode: null,
  constraints: {
    gridSize: 5,
    gridSpacing: 2.0,
    icnirpLimit: 20.0,
    pMax: 1.0,
    signalThreshold: 0.0,
    maxIters: 50,
  },
  running: false,
  currentIter: 0,
  history: [],
  summary: null,

  setMode: (mode) => set({ mode, history: [], summary: null, currentIter: 0 }),
  setConstraints: (c) => set((s) => ({ constraints: { ...s.constraints, ...c } })),
  setRunning: (running) => set({ running }),

  onIteration: (result) =>
    set((s) => ({
      currentIter: result.iter,
      history: [...s.history, result],
    })),

  onDone: (summary) => set({ running: false, summary }),
  onError: (message) => set({ running: false, summary: `Error: ${message}` }),
  reset: () =>
    set({ mode: null, running: false, currentIter: 0, history: [], summary: null }),
}))
