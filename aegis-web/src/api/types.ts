import type { ScenePos } from './coordinates'

// -- ViewerConfig sub-types ---------------------------------------------------

export interface LightingConfig {
  ambient: { color: string; intensity: number }
  sun: { color: string; intensity: number; position: [number, number, number]; cast_shadow: boolean }
  fill?: { color: string; intensity: number; position: [number, number, number] }
  hemisphere: { sky_color: string; ground_color: string; intensity: number }
}

export interface RadiationPatternConfig {
  enabled: boolean
  match_physics: boolean
  type: string
  ico_detail: number
  radius: number
  lobe_gamma: number
  dynamic_range_db: number
  opacity: number
  metalness: number
  roughness: number
  wireframe: boolean
  edge_lines: boolean
  edge_color: string
  hub_radius: number
  hub_color: string
  hub_emissive: string
  show_legacy_cone: boolean
  elements: Array<{ offset?: number[]; weight?: number[]; axis?: number[] }>
}

export interface AntennaConfig {
  default_position: [number, number, number] | null
  sphere_radius: number
  sphere_segments: number
  color: string
  emissive_color: string
  cone_radius: number
  cone_height: number
  cone_segments: number
  cone_y_offset: number
  pole_radius: number
  pole_height: number
  pole_segments: number
  pole_color: string
  placement_height_offset: number
  nudge_step: number
  nudge_step_shift: number
  radiation_pattern: RadiationPatternConfig
}

export interface VoxelConfig {
  size_scale: number
  default_size_fallback: number
  material: { roughness: number; metalness: number; flat_shading: boolean }
  material_colors: Record<string, [number, number, number]>
  heightmap_resolution_factor: number
}

export interface DistanceVizConfig {
  line_color: string
  dash_size: number
  gap_size: number
  line_opacity: number
  label_canvas_width: number
  label_canvas_height: number
  label_bg_color: string
  label_text_color: string
  label_font: string
  label_y_offset: number
  label_scale: [number, number, number]
  path_line_color: string
  path_line_opacity: number
}

export interface UIConfig {
  title: string
  panel: Record<string, unknown>
  colors: Record<string, string>
  fonts: Record<string, unknown>
  loading: Record<string, unknown>
  computing: Record<string, unknown>
  legend: Record<string, unknown>
  scenario?: string
  focus_point_marker?: { color: string; marker_radius: number; ring_radius: number }
  optimize_grid?: { dot_radius: number }
  bug_reporter?: { max_width_ratio: number; max_height_ratio: number }
}

export interface FollowCameraConfig {
  default_distance: number
  default_pitch: number
  min_distance: number
  max_distance: number
  smooth_factor: number
  height_offset: number
  orbit_speed: number
}

export interface CoverageMapConfig {
  switch_to_3d_zoom: number
  max_3d_markers: number
  marker_radius_deg: number
}

export interface BasestationsPanelConfig {
  depth: number
  pole_radius: number
  element_dot_radius: number
  show_elements: boolean
  margin: number
  default_color: string
  min_element_radius: number
  max_element_radius: number
}

export interface SystemInfo {
  hostname: string
  platform: string
  cpu_pct: number | null
  cpu_cores: number | null
  ram_pct: number | null
  ram_total_gb: number | null
  gpu: { name: string; vram_total_mb: number; vram_used_mb: number; utilization_pct: number; temperature_c: number } | null
  git_commit?: string | null
}

// -- Scenario types -----------------------------------------------------------

export interface ScenarioWebState {
  freqGhz?: number;
  powerDbm?: number;
  mode?: string;
  antennaPos?: [number, number, number] | null;
  environment?: {
    source: string;
    lat?: number;
    lon?: number;
    locationQuery?: string;
  };
}

export interface ScenarioEntry {
  label: string;
  description: string;
  icon: string;
  hidden?: boolean;
  webState: ScenarioWebState;
}

// -- ViewerConfig -------------------------------------------------------------

export interface BodyConfig {
  default_name: string
  default_color: number
  default_offset: [number, number, number]
  default_rotation_y: number
  wireframe: boolean
  material: { roughness: number; metalness: number; double_sided: boolean }
  phantom_type: string
  phantom_dir: string
  default_phantom: string
  default_pose: string
  animation_speed: number
}

export interface EnvironmentConfig {
  source: string
  location: string | null
  radius: number
  osm: {
    default_building_height: number
    level_height: number
    buildings: boolean
    roads: boolean
    water: boolean
    detail?: boolean
  }
  tiles: { geometric_error: number }
}

export interface RaytracerConfig {
  max_rt_triangles: number
  reflection_loss_per_order: number
  fspl_distance_clamp: number
  default_body_center: [number, number, number]
  default_source: string
  precompute_max_triangles?: number
  inline_mesh_max_triangles?: number
  defaults?: {
    max_depth: number
    max_depth_min: number
    max_depth_max: number
    rays_per_source: number
    rays_per_source_min: number
    rays_per_source_max: number
    max_paths_per_source: number
    chunk_size: number
    chunk_size_max: number
  }
}

export interface ViewerConfig {
  server: { host: string; port: number; debug: boolean; open_browser: boolean }
  scene: { background_color: string; grid: Record<string, unknown>; ground_plane: Record<string, unknown> }
  camera: { fov: number; near: number; far: number; initial_position: [number, number, number]; controls: Record<string, unknown>; follow?: FollowCameraConfig }
  renderer: { tone_mapping: string; shadows_enabled: boolean; antialias: boolean; shadow_map_type?: string }
  lighting: LightingConfig
  antenna: AntennaConfig
  voxels: VoxelConfig
  body: BodyConfig
  environment: EnvironmentConfig
  raytracer: RaytracerConfig
  dosimetry: {
    fidelity_levels: { value: number; label: string }[]
    max_order_options?: { value: number; label: string }[]
    compliance_threshold: number
    freq_hz: number
    default_power_dbm: number
    default_max_order: number
    skin_model: string
    exposure_scenario: string
    dynamic_range_db: number
    default_level: number
    display_mode: string
    power_input: { min: number; max: number; step: number }
    stochastic: { preset_dir: string; default_preset: string; default_seed: number }
    convex_body_area_factor: number
    level0_D_max: number
  }
  colormap: {
    name: string
    stops: [number, number, number, number][]
    legend: { bar_width: number; bar_height: number; gradient_css: string }
  }
  distance_viz: DistanceVizConfig
  interaction: { click_max_drag_px: number; debounce_ms: number; recompute_interval_ms: number; compute_timeout_ms?: number }
  physics: {
    gravity: number; walk_accel: number; max_walk_speed: number
    ground_friction: number; air_friction: number; jump_impulse: number
    rotation_accel: number; max_rotation_speed: number; rotation_friction: number
    sprint_multiplier: number; max_step_height: number; ground_snap: number; dt_clamp: number
    facing_smooth: number
  }
  ui: UIConfig
  coverage_map?: CoverageMapConfig
  basestations?: { panel: BasestationsPanelConfig; [k: string]: unknown }
  active_scenario?: string
  active_scenario_description?: string
  scenarios?: Record<string, ScenarioEntry>
}

export interface Capabilities {
  bodies: string[]
  gltf_bodies: string[]
  body_name: string
  skin_models: { id: string; label: string }[]
  levels: number[]
  has_voxels: boolean
  has_env_mesh: boolean
  has_differt: boolean
  has_sionna: boolean
  voxel_rt_available: boolean
  has_tiles: boolean
  n_tiles: number
  scenes: Array<string | { name: string; path: string }>
  body_meta: BodyMeta | null
  voxel_meta: VoxelMeta | null
  has_location_loader: boolean
  has_api_key: boolean
  has_coverage: boolean
  google_api_key: string
  google_map_id: string
  cesium_ion_token: string
  body_placement: [number, number, number] | null
  body_device_offsets: Record<string, [number, number, number]>
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
  margin_db: number | null
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

export interface ExposureDistribution {
  mean: number
  median: number
  p95: number
  p99: number
  illuminated_fraction: number
  illuminated_area_cm2: number | null
  illuminated_mean: number
  illuminated_p50: number
}

export interface DosimetryStats {
  p_abs: number
  p_abs_mw: number
  peak_sab: number
  compliant: boolean | null
  warning?: string | null
  ecbf_warnings?: string[]
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
  compliance: ComplianceInfo | null
  // Exposure Lab: false on the fast first pass before 4 cm^2 averaging is filled.
  spatial_averaged?: boolean
  timings?: ComputeTimings
  peaks?: Record<string, number>
  arrays?: ArrayMeta[]
  tissue_eps_r: number
  tissue_sigma: number
  gpu_backend?: string | null
  cold_start?: boolean
  distribution?: ExposureDistribution
  cluster_viz?: ClusterVizData
}

export interface PathViz {
  vertices: number[][]
  order: number
}

export interface ClusterVizItem {
  fbs: [number, number, number] | null
  lbs: [number, number, number] | null
  power: number
  is_los: boolean
}

export interface SubpathVizItem extends ClusterVizItem {
  cluster: number
}

export interface ClusterVizData {
  clusters: ClusterVizItem[]
  subpaths: SubpathVizItem[]
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

// -- Analysis types -------------------------------------------------------

export interface TissueSpectrum {
  tissue: string
  freqs_hz: number[]
  eps_r: number[]
  sigma: number[]
  T0: number[]
}

// --- MIMO types ---

export type ElementPattern = 'isotropic' | 'patch' | 'short_dipole'

export interface ArrayConfig {
  type: 'upa'
  n_h: number
  n_v: number
  d_h_wavelengths: number
  d_v_wavelengths: number
  position: ScenePos
  broadside: [number, number, number]
  element_pattern: ElementPattern
}

export interface MIMOUserConfig {
  id: string
  phantom: string
  position: ScenePos
  orientation: number
  device_offset: [number, number, number]
}

export interface MIMOComputeRequest {
  array: ArrayConfig
  users: MIMOUserConfig[]
  freq_hz: number
  power_dbm: number
  precoder_type: string
  changed?: {
    type: string
    user_id?: string
  }
}

export interface MIMOComputeResponse {
  user_ids: string[]
  timings: Record<string, number>
  precoder_type: string
  weights_real?: number[][]
  weights_imag?: number[][]
  warning?: string
  ecbf_warnings?: string[]
}

export interface MIMOUserSummary {
  id: string
  phantom: string
  position: [number, number, number]
  p_abs_mw: number
  peak_sab: number
  compliant: boolean
}

export interface MIMOSummary {
  users: MIMOUserSummary[]
  precoder: string
  timings: Record<string, number>
  warning?: string
  ecbf_warnings?: string[]
}

// ScenePos is re-exported for convenience where types.ts is the single import point
export type { ScenePos }

// Coverage globe types

export interface RegionSummary {
  name: string
  label: string
  bbox: [number, number, number, number] | null  // [min_lon, max_lon, min_lat, max_lat]
  count: number
  completeness: number
}

export interface CoverageSitesMeta {
  count: number
  operators: string[]
  technologies: string[]
  region_names: string[]
}

export interface CoverageResponse {
  regions: RegionSummary[]
  sites_meta: CoverageSitesMeta
  sites_b64: string
}
