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
  scenes: { name: string; path: string }[]
  sceneGeometry: {
    vertices: Float32Array
    indices: Int32Array
    faceColors: Float32Array | null
  } | null
  sceneGeometryVisible: boolean

  // GLB tiles
  glbTiles: string[]

  // Ray tracing
  pathSource: 'synthetic' | 'stochastic' | 'rt'
  rtSource: 'voxel' | 'differt' | 'sionna'
  rtMaxOrder: number
  rtPaths: PathViz[] | null
  hasDiffert: boolean
  loadedScenePath: string

  // RT config - path solving
  rtMethod: 'exhaustive' | 'sbr' | 'hybrid'
  rtRaysPerSource: number
  rtMaxPathsPerSource: number

  // RT config - interactions
  rtLos: boolean
  rtSpecularReflection: boolean
  rtDiffuseReflection: boolean
  rtRefraction: boolean
  rtDiffraction: boolean
  rtEdgeDiffraction: boolean
  rtDiffractionLitRegion: boolean

  // RT config - solver-specific
  rtReflectionLoss: number
  rtSyntheticArray: boolean
  rtSeed: number

  // Actions
  setViewerConfig: (config: ViewerConfig) => void
  setCapabilities: (caps: Capabilities) => void
  setBodyName: (name: string) => void
  setBodyGeometry: (geom: BufferGeometry | null) => void
  setVoxelData: (data: SceneStore['voxelData']) => void
  setVoxelHeightmap: (fn: SceneStore['voxelHeightmap']) => void
  toggleLayer: (material: string) => void
  setEnvDisplayMode: (mode: SceneStore['envDisplayMode']) => void
  setScenes: (scenes: SceneStore['scenes']) => void
  setSceneGeometry: (geom: SceneStore['sceneGeometry']) => void
  toggleSceneGeometryVisible: () => void
  setGlbTiles: (tiles: string[]) => void
  setPathSource: (source: SceneStore['pathSource']) => void
  setRtSource: (source: SceneStore['rtSource']) => void
  setRtMaxOrder: (order: number) => void
  setRtPaths: (paths: PathViz[] | null) => void
  setLoadedScenePath: (path: string) => void
  clearScene: () => void
}

export const useSceneStore = create<SceneStore>((set) => ({
  viewerConfig: null,
  capabilities: null,
  bodyName: '',
  bodyGeometry: null,
  voxelData: null,
  voxelHeightmap: null,
  layerVisibility: {},
  envDisplayMode: 'cubes',
  scenes: [],
  sceneGeometry: null,
  sceneGeometryVisible: true,
  glbTiles: [],
  pathSource: 'synthetic',
  rtSource: 'differt',
  rtMaxOrder: 3,
  rtPaths: null,
  hasDiffert: false,
  loadedScenePath: '',
  rtMethod: 'exhaustive',
  rtRaysPerSource: 1_000_000,
  rtMaxPathsPerSource: 1_000_000,
  rtLos: true,
  rtSpecularReflection: true,
  rtDiffuseReflection: false,
  rtRefraction: true,
  rtDiffraction: false,
  rtEdgeDiffraction: false,
  rtDiffractionLitRegion: true,
  rtReflectionLoss: 0.5,
  rtSyntheticArray: true,
  rtSeed: 42,
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
  setScenes: (scenes) => set({ scenes }),
  setSceneGeometry: (geom) => set({ sceneGeometry: geom }),
  toggleSceneGeometryVisible: () => set((state) => ({ sceneGeometryVisible: !state.sceneGeometryVisible })),
  setGlbTiles: (tiles) => set({ glbTiles: tiles }),
  setPathSource: (source) => set({ pathSource: source, ...(source !== 'rt' ? { rtPaths: null } : {}) }),
  setRtSource: (source) => set({ rtSource: source }),
  setRtMaxOrder: (order) => set({ rtMaxOrder: order }),
  setRtPaths: (paths) => set({ rtPaths: paths }),
  setLoadedScenePath: (path) => set({ loadedScenePath: path }),
  clearScene: () => set({
    voxelData: null,
    voxelHeightmap: null,
    layerVisibility: {},
    sceneGeometry: null,
    sceneGeometryVisible: true,
    glbTiles: [],
    rtPaths: null,
    loadedScenePath: '',
  }),
}))
