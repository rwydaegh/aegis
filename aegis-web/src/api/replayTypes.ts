/**
 * Replay artifact schema.
 *
 * A headless experiment run (no viz, at speed) writes one of these JSON
 * files. The Replay tab reads it and lets you scrub the run. The artifact
 * is the only contract between the compute side (paper repo, self-contained)
 * and the viewer (this app). All positions are in the server Z-up convention
 * (metres); the viewer applies `toScene` to render them Y-up.
 */

export type Vec3 = [number, number, number]

export interface ReplayBox {
  center: Vec3
  /** Full extents [sx, sy, sz] in server coords (not half-extents). */
  size: Vec3
  /** Rotation about the server z (vertical) axis, radians. */
  yaw_rad?: number
  kind?: 'scatterer' | 'blocker' | 'wall' | string
}

/** The real city geometry as an indexed triangle mesh: the exact surfaces the
 *  ray tracer bounces off (OSM footprints extruded with parsed roofs), not
 *  bounding boxes. Vertices are server Z-up (ENU). */
export interface ReplaySceneMesh {
  vertices: Vec3[]
  triangles: [number, number, number][]
}

export interface ReplaySceneSpec {
  /** Room extent as a wireframe box. center defaults to origin if omitted. */
  room?: { center?: Vec3; size: Vec3 }
  /** Real ray-traced city geometry. Rendered in place of building boxes. */
  mesh?: ReplaySceneMesh
  /** Scatterer/blocker boxes shared across all frames (single-realization artifacts). */
  boxes?: ReplayBox[]
  /** NLOS blocker, rendered only on frames whose condition contains NLOS. */
  blocker?: ReplayBox | null
  ground?: { size: number }
}

/** One scene realization: a distinct scatterer layout (e.g. a different seed). */
export interface ReplayRealization {
  seed: number
  boxes: ReplayBox[]
}

export interface ReplayArraySpec {
  position: Vec3
  /** Optional explicit element positions (server coords). */
  elements?: Vec3[]
  /** Broadside direction (server unit vector). Panel broad face points along it. */
  normal?: Vec3
  n_h?: number
  n_v?: number
  M?: number
  /** Marker panel extents in metres (exaggerated for visibility). */
  panel_w?: number
  panel_h?: number
  tilt_deg?: number
}

export interface ReplayBodyMesh {
  /** Absolute vertex positions, server coords. */
  vertices: Vec3[]
  /** Triangle vertex indices into `vertices`. */
  faces: [number, number, number][]
}

export interface ReplayPath {
  vertices: Vec3[]
  /** Bounce order: 0 = LOS, 1 = single reflection, etc. */
  order?: number
  power?: number
}

export interface ReplayFrame {
  ue_index: number
  condition: string
  precoder: string
  /** Index into artifact.realizations (which scatterer layout this frame used). */
  realization?: number
  pareto_point?: number | null
  /** Translation (server coords) applied to the canonical body mesh this frame. */
  body_pos?: Vec3
  paths?: ReplayPath[]
  /** Absorbed power density. Length == body.vertices.length (per-vertex) or
   *  body.faces.length (per-face; the viewer expands to the three soup verts). */
  sab?: number[]
  /** Scalar readouts shown in the panel (p_abs, signal, eta, ...). */
  scalars?: Record<string, number>
}

export interface ReplayArtifact {
  meta?: Record<string, unknown>
  scene: ReplaySceneSpec
  /** Per-realization scatterer layouts; frames index in via frame.realization. */
  realizations?: ReplayRealization[]
  array?: ReplayArraySpec
  body?: ReplayBodyMesh
  ues?: Vec3[]
  frames: ReplayFrame[]
}

/** Frame selection constraints, as used by deep-links and panel selectors. */
export type FrameQuery = Partial<Pick<ReplayFrame, 'ue_index' | 'condition' | 'precoder' | 'realization'>>

/** Index of the first frame matching all given constraints, or -1. */
export function findFrameIndex(frames: ReplayFrame[], want: FrameQuery): number {
  return frames.findIndex(
    (f) =>
      (want.ue_index === undefined || f.ue_index === want.ue_index) &&
      (want.condition === undefined || f.condition === want.condition) &&
      (want.precoder === undefined || f.precoder === want.precoder) &&
      (want.realization === undefined || f.realization === want.realization),
  )
}

/** Parse ?realization=&ue=&condition=&precoder= from a query string into a FrameQuery. */
export function parseFrameQuery(search: string): FrameQuery {
  const p = new URLSearchParams(search)
  const want: FrameQuery = {}
  if (p.has('realization')) want.realization = Number(p.get('realization'))
  if (p.has('ue')) want.ue_index = Number(p.get('ue'))
  if (p.has('condition')) want.condition = p.get('condition') as string
  if (p.has('precoder')) want.precoder = p.get('precoder') as string
  return want
}

/** Minimal structural validation. Returns an error string, or null if ok. */
export function validateArtifact(obj: unknown): string | null {
  if (typeof obj !== 'object' || obj === null) return 'Artifact is not an object'
  const a = obj as Partial<ReplayArtifact>
  if (!a.scene || typeof a.scene !== 'object') return 'Missing "scene"'
  if (a.scene.boxes !== undefined && !Array.isArray(a.scene.boxes)) return 'scene.boxes must be an array'
  if (a.realizations !== undefined && !Array.isArray(a.realizations)) return 'realizations must be an array'
  if (!Array.isArray(a.frames)) return 'Missing "frames" array'
  if (a.frames.length === 0) return 'frames is empty'
  if (a.body && !Array.isArray(a.body.vertices)) return 'body.vertices must be an array'
  return null
}
