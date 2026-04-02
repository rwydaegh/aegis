import { create } from 'zustand'

export type CameraPreset = 'front' | 'side' | 'top' | 'focus' | 'reset' | null
export type CameraMode = 'orbit' | 'follow' | 'globe'
export type LegendScale = 'linear' | 'dB'
export type { QuantityKey } from '@/api/types'
export type ExposureScenario = 'general_public' | 'occupational'

export interface LastComputeTiming {
  totalMs: number
  rtMs: number | null
  kernelMs: number
  averagingMs: number
  complianceMs: number
  networkMs: number
  avgCached: boolean
  gpuBackend: string | null
  coldStart: boolean
}

interface UIStore {
  sidebarOpen: boolean
  wireframe: boolean
  isComputing: boolean
  computeElapsed: number
  locationLoading: boolean
  locationLog: string[]
  statusMessage: string | null
  cameraPreset: CameraPreset
  cameraMode: CameraMode
  legendScale: LegendScale
  dynamicRangeDb: number
  colormapLocked: boolean
  colormapLockedMax: number | null
  ratioMode: boolean
  exposureScenario: ExposureScenario
  lastComputeTiming: LastComputeTiming | null
  gpuWarm: boolean | null
  computeColdStart: boolean
  helpOpen: boolean
  welcomeDismissed: boolean
  activeScenario: string | null
  scenarioLoading: boolean
  cameraOverride: { position: [number, number, number]; target: [number, number, number] } | null

  toggleSidebar: () => void
  toggleWireframe: () => void
  setComputing: (computing: boolean) => void
  setComputeElapsed: (ms: number) => void
  setLocationLoading: (loading: boolean) => void
  appendLocationLog: (msg: string) => void
  clearLocationLog: () => void
  setStatusMessage: (msg: string | null) => void
  setCameraPreset: (preset: CameraPreset) => void
  setCameraMode: (mode: CameraMode) => void
  toggleLegendScale: () => void
  setDynamicRangeDb: (db: number) => void
  toggleColormapLock: () => void
  setColormapLockedMax: (max: number) => void
  setRatioMode: (on: boolean) => void
  setExposureScenario: (s: ExposureScenario) => void
  setLastComputeTiming: (t: LastComputeTiming | null) => void
  setGpuWarm: (warm: boolean | null) => void
  setComputeColdStart: (cold: boolean) => void
  toggleHelp: () => void
  setWelcomeDismissed: (v: boolean) => void
  setActiveScenario: (v: string | null) => void
  setScenarioLoading: (v: boolean) => void
  setCameraOverride: (v: UIStore['cameraOverride']) => void
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: true,
  wireframe: false,
  isComputing: false,
  computeElapsed: 0,
  locationLoading: false,
  locationLog: [],
  statusMessage: null,
  cameraPreset: null,
  cameraMode: 'orbit',
  legendScale: 'linear',
  dynamicRangeDb: 30,
  colormapLocked: false,
  colormapLockedMax: null,
  ratioMode: false,
  exposureScenario: 'general_public',
  lastComputeTiming: null,
  gpuWarm: null,
  computeColdStart: false,
  helpOpen: false,
  welcomeDismissed: false,
  activeScenario: null as string | null,
  scenarioLoading: false,
  cameraOverride: null,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  toggleWireframe: () => set((state) => ({ wireframe: !state.wireframe })),
  setComputing: (computing) => set({ isComputing: computing }),
  setComputeElapsed: (ms) => set({ computeElapsed: ms }),
  setLocationLoading: (loading) => set({ locationLoading: loading }),
  appendLocationLog: (msg) =>
    set((state) => ({ locationLog: [...state.locationLog, msg] })),
  clearLocationLog: () => set({ locationLog: [] }),
  setStatusMessage: (msg) => set({ statusMessage: msg }),
  setCameraPreset: (preset) => set({ cameraPreset: preset }),
  setCameraMode: (mode) => set({ cameraMode: mode }),
  toggleLegendScale: () => set((state) => ({
    legendScale: state.legendScale === 'linear' ? 'dB' : 'linear',
  })),
  setDynamicRangeDb: (db) => set({ dynamicRangeDb: db }),
  toggleColormapLock: () => set((state) => {
    if (state.colormapLocked) {
      return { colormapLocked: false, colormapLockedMax: null }
    }
    return { colormapLocked: true }
  }),
  setColormapLockedMax: (max) => set({ colormapLockedMax: max }),
  setRatioMode: (on) => set({ ratioMode: on }),
  setExposureScenario: (s) => set({ exposureScenario: s }),
  setLastComputeTiming: (t) => set({ lastComputeTiming: t }),
  setGpuWarm: (warm) => set({ gpuWarm: warm }),
  setComputeColdStart: (cold) => set({ computeColdStart: cold }),
  toggleHelp: () => set((state) => ({ helpOpen: !state.helpOpen })),
  setWelcomeDismissed: (v) => set({ welcomeDismissed: v }),
  setActiveScenario: (v) => set({ activeScenario: v }),
  setScenarioLoading: (v) => set({ scenarioLoading: v }),
  setCameraOverride: (v) => set({ cameraOverride: v }),
}))
