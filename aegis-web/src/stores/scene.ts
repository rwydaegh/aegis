import { create } from 'zustand'
import type { ViewerConfig, Capabilities, VoxelMeta, PathViz } from '@/api/types'
import type { BufferGeometry } from 'three'

interface SceneStore {
  // Config (loaded at startup)
  viewerConfig: ViewerConfig | null
  capabilities: Capabilities | null

  // Body mesh
  bodyName: string
  bodyGeometry: BufferGeometry | null

  // Voxels
  voxelData: {
    positions: Float32Array
    sizes: Float32Array
    colors: Uint8Array
    materialIndices: Uint8Array
    meta: VoxelMeta
  } | null
  voxelHeightmap: ((x: number, z: number, bodyY: number) => number) | null
  layerVisibility: Record<string, boolean>
  envDisplayMode: 'cubes' | 'hull' | 'tiles'

  // Sionna scenes
  scenePaths: string[]
  sceneGeometry: {
    vertices: Float32Array
    indices: Int32Array
    faceColors: Float32Array | null
  } | null

  // GLB tiles
  glbTiles: string[]

  // Ray tracing
  rtEnabled: boolean
  rtSource: 'voxel' | 'sionna'
  rtMaxOrder: number
  rtPaths: PathViz[] | null
  hasDiffert: boolean

  // Actions
  setViewerConfig: (config: ViewerConfig) => void
  setCapabilities: (caps: Capabilities) => void
  setBodyName: (name: string) => void
  setBodyGeometry: (geom: BufferGeometry | null) => void
  setVoxelData: (data: SceneStore['voxelData']) => void
  setVoxelHeightmap: (fn: SceneStore['voxelHeightmap']) => void
  toggleLayer: (material: string) => void
  setEnvDisplayMode: (mode: SceneStore['envDisplayMode']) => void
  setScenePaths: (paths: string[]) => void
  setSceneGeometry: (geom: SceneStore['sceneGeometry']) => void
  setGlbTiles: (tiles: string[]) => void
  setRtEnabled: (enabled: boolean) => void
  setRtSource: (source: SceneStore['rtSource']) => void
  setRtMaxOrder: (order: number) => void
  setRtPaths: (paths: PathViz[] | null) => void
}

export const useSceneStore = create<SceneStore>((set, get) => ({
  viewerConfig: null,
  capabilities: null,
  bodyName: '',
  bodyGeometry: null,
  voxelData: null,
  voxelHeightmap: null,
  layerVisibility: {},
  envDisplayMode: 'cubes',
  scenePaths: [],
  sceneGeometry: null,
  glbTiles: [],
  rtEnabled: false,
  rtSource: 'voxel',
  rtMaxOrder: 2,
  rtPaths: null,
  hasDiffert: false,
  setViewerConfig: (config) => set({ viewerConfig: config }),
  setCapabilities: (caps) => set({ capabilities: caps }),
  setBodyName: (name) => set({ bodyName: name }),
  setBodyGeometry: (geom) => set({ bodyGeometry: geom }),
  setVoxelData: (data) => set({ voxelData: data }),
  setVoxelHeightmap: (fn) => set({ voxelHeightmap: fn }),
  toggleLayer: (material) =>
    set((state) => ({
      layerVisibility: {
        ...state.layerVisibility,
        [material]: !state.layerVisibility[material],
      },
    })),
  setEnvDisplayMode: (mode) => set({ envDisplayMode: mode }),
  setScenePaths: (paths) => set({ scenePaths: paths }),
  setSceneGeometry: (geom) => set({ sceneGeometry: geom }),
  setGlbTiles: (tiles) => set({ glbTiles: tiles }),
  setRtEnabled: (enabled) => set({ rtEnabled: enabled }),
  setRtSource: (source) => set({ rtSource: source }),
  setRtMaxOrder: (order) => set({ rtMaxOrder: order }),
  setRtPaths: (paths) => set({ rtPaths: paths }),
}))
