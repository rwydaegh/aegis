import { create } from 'zustand'

export type CameraPreset = 'front' | 'side' | 'top' | 'focus' | 'reset' | null

interface UIStore {
  sidebarOpen: boolean
  wireframe: boolean
  isComputing: boolean
  computeElapsed: number
  locationLoading: boolean
  locationLog: string[]
  statusMessage: string | null
  cameraPreset: CameraPreset

  toggleSidebar: () => void
  toggleWireframe: () => void
  setComputing: (computing: boolean) => void
  setComputeElapsed: (ms: number) => void
  setLocationLoading: (loading: boolean) => void
  appendLocationLog: (msg: string) => void
  clearLocationLog: () => void
  setStatusMessage: (msg: string | null) => void
  setCameraPreset: (preset: CameraPreset) => void
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
}))
