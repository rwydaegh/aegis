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
  skin_models: { id: string; label: string }[]
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

export interface ComplianceCheck {
  label: string
  value: number
  limit: number
  unit: string
  pass: boolean
  ratio: number
}

export interface ComplianceInfo {
  overall_pass: boolean
  margin_db: number | null
  scenario: 'general_public' | 'occupational'
  freq_hz: number
  checks: ComplianceCheck[]
}

export type QuantityKey = 'sab' | 'sab_4cm2' | 'sab_1cm2' | 'sar_wb' | 'sinc_local' | 'sinc_wb'

export interface ArrayMeta {
  key: string
  offset: number
  length: number
}

export interface ComputeTimings {
  body_transform_ms: number
  kernel_ms: number
  avg_build_G_4cm2_ms: number
  avg_matvec_4cm2_ms: number
  engine_compute_ms: number
  compliance_stats_ms: number
  total_ms: number
  route_total_ms: number
  [key: string]: number
}

export interface DosimetryStats {
  p_abs: number
  p_abs_mw: number
  peak_sab: number
  compliant: boolean
  n_illuminated: number
  n_triangles: number
  level: number
  mode?: string
  corrections?: string[]
  S_inc: number
  distance_m: number
  T0: number
  n_rt_paths?: number
  path_viz?: PathViz[]
  peak_sab_averaged: number | null
  compliance: ComplianceInfo
  timings?: ComputeTimings
  peaks?: Record<string, number>
  arrays?: ArrayMeta[]
  tissue_eps_r: number
  tissue_sigma: number
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
