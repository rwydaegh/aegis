import { create } from 'zustand'

export type CameraPreset = 'front' | 'side' | 'top' | 'focus' | 'reset' | null
export type LegendScale = 'linear' | 'dB'

interface UIStore {
  sidebarOpen: boolean
  wireframe: boolean
  isComputing: boolean
  computeElapsed: number
  locationLoading: boolean
  locationLog: string[]
  statusMessage: string | null
  cameraPreset: CameraPreset
  legendScale: LegendScale

  toggleSidebar: () => void
  toggleWireframe: () => void
  setComputing: (computing: boolean) => void
  setComputeElapsed: (ms: number) => void
  setLocationLoading: (loading: boolean) => void
  appendLocationLog: (msg: string) => void
  clearLocationLog: () => void
  setStatusMessage: (msg: string | null) => void
  setCameraPreset: (preset: CameraPreset) => void
  toggleLegendScale: () => void
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
  legendScale: 'linear',
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
  toggleLegendScale: () => set((state) => ({
    legendScale: state.legendScale === 'linear' ? 'dB' : 'linear',
  })),
}))
