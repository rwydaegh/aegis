import { create } from 'zustand'

export type CameraPreset = 'front' | 'side' | 'top' | 'focus' | 'reset' | null
export type CameraMode = 'orbit' | 'follow'
export type LegendScale = 'linear' | 'dB'
export type DisplayMode = 'raw_sab' | 'avg_sab' | 'sinc' | 'ratio_sab' | 'ratio_sinc'
export type ExposureScenario = 'general_public' | 'occupational'

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
  displayMode: DisplayMode
  exposureScenario: ExposureScenario

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
  setDisplayMode: (mode: DisplayMode) => void
  setExposureScenario: (s: ExposureScenario) => void
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
  displayMode: 'raw_sab',
  exposureScenario: 'general_public',
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
  setDisplayMode: (mode) => set({ displayMode: mode }),
  setExposureScenario: (s) => set({ exposureScenario: s }),
}))
