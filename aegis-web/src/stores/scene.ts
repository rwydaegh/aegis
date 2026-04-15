import { create } from 'zustand'
import type { ViewerConfig, Capabilities, VoxelMeta, PathViz } from '@/api/types'
import type { BufferGeometry } from 'three'
import { useUIStore } from '@/stores/ui'

export interface RtStoreConfig {
  method: 'exhaustive' | 'sbr' | 'hybrid'
  raysPerSource: number
  maxPathsPerSource: number
  chunkSize: number | null
  los: boolean
  specularReflection: boolean
  diffuseReflection: boolean
  refraction: boolean
  diffraction: boolean
  edgeDiffraction: boolean
  diffractionLitRegion: boolean
  reflectionLoss: number
  syntheticArray: boolean
  seed: number
}

const DEFAULT_RT_CONFIG: RtStoreConfig = {
  method: 'exhaustive',
  raysPerSource: 1_000_000,
  maxPathsPerSource: 1_000_000,
  chunkSize: null,
  los: true,
  specularReflection: true,
  diffuseReflection: false,
  refraction: true,
  diffraction: false,
  edgeDiffraction: false,
  diffractionLitRegion: true,
  reflectionLoss: 0.5,
  syntheticArray: true,
  seed: 42,
}

interface SceneStore {
  // Config (loaded at startup)
  viewerConfig: ViewerConfig | null
  capabilities: Capabilities | null

  // Body mesh
  bodyName: string
  bodyGeometry: BufferGeometry | null

  // Animation state (for glTF phantoms)
  animationClip: string
  animationPlaying: boolean
  phantomType: 'stl' | 'gltf'

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
  hullMeshStatus: 'idle' | 'computing' | 'ready' | 'error'

  // Sionna scenes
  scenes: { name: string; path: string }[]
  sceneGeometry: {
    vertices: Float32Array
    indices: Int32Array
    faceColors: Float32Array | null
  } | null
  sceneGeometryVisible: boolean

  // Scene element visibility
  bodyMeshVisible: boolean
  groundPlaneVisible: boolean
  gridVisible: boolean
  complianceRingVisible: boolean

  // GLB tiles
  glbTiles: string[]

  // Display config (shareable)
  colormapName: string
  sunIntensity: number
  ambientIntensity: number
  cameraFov: number

  // Ray tracing
  pathSource: 'synthetic' | 'stochastic' | 'rt'
  rtSource: 'sionna' | 'differt'
  rtMaxOrder: number
  rtPaths: PathViz[] | null
  hasDiffert: boolean
  loadedScenePath: string
  rtConfig: RtStoreConfig

  // Actions
  setViewerConfig: (config: ViewerConfig) => void
  setCapabilities: (caps: Capabilities) => void
  setBodyName: (name: string) => void
  setBodyGeometry: (geom: BufferGeometry | null) => void
  setAnimationClip: (clip: string) => void
  setAnimationPlaying: (playing: boolean) => void
  setPhantomType: (type: 'stl' | 'gltf') => void
  setVoxelData: (data: SceneStore['voxelData']) => void
  setVoxelHeightmap: (fn: SceneStore['voxelHeightmap']) => void
  toggleLayer: (material: string) => void
  setEnvDisplayMode: (mode: SceneStore['envDisplayMode']) => void
  setHullMeshStatus: (status: SceneStore['hullMeshStatus']) => void
  setScenes: (scenes: SceneStore['scenes']) => void
  setSceneGeometry: (geom: SceneStore['sceneGeometry']) => void
  toggleSceneGeometryVisible: () => void
  toggleBodyMeshVisible: () => void
  toggleGroundPlaneVisible: () => void
  toggleGridVisible: () => void
  toggleComplianceRingVisible: () => void
  setBodyMeshVisible: (v: boolean) => void
  setGroundPlaneVisible: (v: boolean) => void
  setGridVisible: (v: boolean) => void
  setComplianceRingVisible: (v: boolean) => void
  setSceneGeometryVisible: (v: boolean) => void
  setGlbTiles: (tiles: string[]) => void
  setPathSource: (source: SceneStore['pathSource']) => void
  setRtSource: (source: 'sionna' | 'differt') => void
  setRtMaxOrder: (order: number) => void
  setRtPaths: (paths: PathViz[] | null) => void
  setLoadedScenePath: (path: string) => void
  setRtConfig: (partial: Partial<RtStoreConfig>) => void
  setColormapName: (name: string) => void
  setSunIntensity: (v: number) => void
  setAmbientIntensity: (v: number) => void
  setCameraFov: (v: number) => void
  clearScene: () => void
}

export const useSceneStore = create<SceneStore>((set, get) => ({
  viewerConfig: null,
  capabilities: null,
  bodyName: '',
  bodyGeometry: null,
  animationClip: 'idle',
  animationPlaying: false,
  phantomType: 'stl',
  voxelData: null,
  voxelHeightmap: null,
  layerVisibility: {},
  colormapName: 'inferno',
  sunIntensity: 1.2,
  ambientIntensity: 0.6,
  cameraFov: 55,
  envDisplayMode: 'cubes',
  hullMeshStatus: 'idle',
  scenes: [],
  sceneGeometry: null,
  sceneGeometryVisible: true,
  bodyMeshVisible: true,
  groundPlaneVisible: true,
  gridVisible: false,
  complianceRingVisible: true,
  glbTiles: [],
  pathSource: 'synthetic',
  rtSource: 'sionna',
  rtMaxOrder: 2,
  rtPaths: null,
  hasDiffert: false,
  loadedScenePath: '',
  rtConfig: { ...DEFAULT_RT_CONFIG },
  setViewerConfig: (config) => set({ viewerConfig: config }),
  setCapabilities: (caps) => set({ capabilities: caps }),
  setBodyName: (name) => set({ bodyName: name }),
  setBodyGeometry: (geom) => {
    get().bodyGeometry?.dispose()
    set({ bodyGeometry: geom })
  },
  setAnimationClip: (clip) => set({ animationClip: clip }),
  setAnimationPlaying: (playing) => set({ animationPlaying: playing }),
  setPhantomType: (type) => set({ phantomType: type }),
  setVoxelData: (data) => set({ voxelData: data }),
  setVoxelHeightmap: (fn) => set({ voxelHeightmap: fn }),
  toggleLayer: (material) =>
    set((state) => ({
      layerVisibility: {
        ...state.layerVisibility,
        [material]: !state.layerVisibility[material],
      },
    })),
  setEnvDisplayMode: (mode) => set({ envDisplayMode: mode, ...(mode !== 'hull' ? { hullMeshStatus: 'idle' as const } : {}) }),
  setHullMeshStatus: (status) => set({ hullMeshStatus: status }),
  setScenes: (scenes) => set({ scenes }),
  setSceneGeometry: (geom) => set({ sceneGeometry: geom }),
  toggleSceneGeometryVisible: () => set((state) => ({ sceneGeometryVisible: !state.sceneGeometryVisible })),
  toggleBodyMeshVisible: () => set((state) => ({ bodyMeshVisible: !state.bodyMeshVisible })),
  toggleGroundPlaneVisible: () => set((state) => ({ groundPlaneVisible: !state.groundPlaneVisible })),
  toggleGridVisible: () => set((state) => ({ gridVisible: !state.gridVisible })),
  toggleComplianceRingVisible: () => set((state) => ({ complianceRingVisible: !state.complianceRingVisible })),
  setBodyMeshVisible: (v) => set({ bodyMeshVisible: v }),
  setGroundPlaneVisible: (v) => set({ groundPlaneVisible: v }),
  setGridVisible: (v) => set({ gridVisible: v }),
  setComplianceRingVisible: (v) => set({ complianceRingVisible: v }),
  setSceneGeometryVisible: (v) => set({ sceneGeometryVisible: v }),
  setGlbTiles: (tiles) => set({ glbTiles: tiles }),
  setPathSource: (source) => {
    set({ pathSource: source, ...(source !== 'rt' ? { rtPaths: null } : {}) })
    // Clear stale RT timing and cold-start flag from the status bar
    useUIStore.getState().setLastComputeTiming(null)
    useUIStore.getState().setComputeColdStart(false)
  },
  setRtSource: (source) => set({ rtSource: source }),
  setRtMaxOrder: (order) => set({ rtMaxOrder: order }),
  setRtPaths: (paths) => set({ rtPaths: paths }),
  setLoadedScenePath: (path) => set({ loadedScenePath: path }),
  setRtConfig: (partial) => set((state) => ({ rtConfig: { ...state.rtConfig, ...partial } })),
  setColormapName: (name) => set({ colormapName: name }),
  setSunIntensity: (v) => set({ sunIntensity: v }),
  setAmbientIntensity: (v) => set({ ambientIntensity: v }),
  setCameraFov: (v) => set({ cameraFov: v }),
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
