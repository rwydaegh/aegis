import type { ScenePos } from './coordinates'

export interface ViewerConfig {
  server: { host: string; port: number; debug: boolean; open_browser: boolean }
  scene: { background_color: string; grid: Record<string, unknown>; ground_plane: Record<string, unknown> }
  camera: { fov: number; near: number; far: number; initial_position: number[]; controls: Record<string, unknown> }
  renderer: { tone_mapping: string; shadows_enabled: boolean; antialias: boolean }
  lighting: Record<string, unknown>
  antenna: {
    sphere_radius: number; cone_radius: number; cone_height: number
    pole_radius: number; pole_height: number; nudge_step: number; nudge_step_shift: number
    radiation_pattern: {
      enabled: boolean; type: string; ico_detail: number; radius: number
      lobe_gamma: number; dynamic_range_db: number; opacity: number
      hub: { radius: number; color: string }
      edges: { enabled: boolean; color: string; opacity: number }
      elements: { enabled: boolean; radius: number }
    }
  }
  voxels: { size_scale: number; heightmap_resolution_factor: number }
  dosimetry: {
    fidelity_levels: { value: number; label: string }[]
    path_options: { value: number; label: string }[]
    max_order_options: { value: number; label: string }[]
    compliance_threshold: number
  }
  colormap: {
    name: string
    stops: [number, number, number, number][]
    legend: { bar_width: number; bar_height: number; gradient_css: string }
  }
  distance_viz: Record<string, unknown>
  interaction: { click_max_drag_px: number; debounce_ms: number; recompute_interval_ms: number }
  physics: {
    gravity: number; walk_accel: number; max_walk_speed: number
    ground_friction: number; air_friction: number; jump_impulse: number
    rotation_accel: number; max_rotation_speed: number; rotation_friction: number
    sprint_multiplier: number; max_step_height: number; ground_snap: number; dt_clamp: number
    facing_smooth: number
  }
  ui: Record<string, unknown>
  [key: string]: unknown
}

export interface Capabilities {
  bodies: string[]
  tissues: string[]
  levels: number[]
  has_voxels: boolean
  has_differt: boolean
  has_sionna: boolean
  voxel_rt_available: boolean
  has_tiles: boolean
  n_tiles: number
  scenes: string[]
  body_meta: BodyMeta | null
  voxel_meta: VoxelMeta | null
  has_location_loader: boolean
  has_api_key: boolean
  body_placement: [number, number, number] | null
}

export interface BodyMeta {
  n_triangles: number
  n_vertices: number
  total_area_cm2: number
  name: string
}

export interface VoxelMeta {
  n_voxels: number
  materials: string[]
  material_colors: Record<string, [number, number, number]>
  voxel_size: number
}

export interface DosimetryStats {
  p_abs: number
  p_abs_mw: number
  peak_sab: number
  compliant: boolean
  n_illuminated: number
  n_triangles: number
  level: number
  S_inc: number
  distance_m: number
  T0: number
  n_rt_paths?: number
  path_viz?: PathViz[]
}

export interface PathViz {
  vertices: number[][]
  order: number
}

export interface LevelInfo {
  level: number
  name: string
  description: string
}

export interface TissuePreset {
  id: string
  name: string
  eps_r: number
  sigma: number
  freq_hz: number
}

export interface BodyBinary {
  positions: Float32Array
  normals: Float32Array
}

export interface VoxelBinary {
  positions: Float32Array
  sizes: Float32Array
  colors: Uint8Array
  materialIndices: Uint8Array
  meta: VoxelMeta
}

// ScenePos is re-exported for convenience where types.ts is the single import point
export type { ScenePos }
