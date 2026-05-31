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

export interface ReplaySceneSpec {
  /** Room extent as a wireframe box. center defaults to origin if omitted. */
  room?: { center?: Vec3; size: Vec3 }
  boxes: ReplayBox[]
  ground?: { size: number }
}

export interface ReplayArraySpec {
  position: Vec3
  /** Optional explicit element positions (server coords). */
  elements?: Vec3[]
  n_h?: number
  n_v?: number
  M?: number
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
  pareto_point?: number | null
  paths?: ReplayPath[]
  /** Per body-vertex absorbed power density, length == body.vertices.length. */
  sab?: number[]
  /** Scalar readouts shown in the panel (p_abs, signal, eta, ...). */
  scalars?: Record<string, number>
}

export interface ReplayArtifact {
  meta?: Record<string, unknown>
  scene: ReplaySceneSpec
  array?: ReplayArraySpec
  body?: ReplayBodyMesh
  ues?: Vec3[]
  frames: ReplayFrame[]
}

/** Minimal structural validation. Returns an error string, or null if ok. */
export function validateArtifact(obj: unknown): string | null {
  if (typeof obj !== 'object' || obj === null) return 'Artifact is not an object'
  const a = obj as Partial<ReplayArtifact>
  if (!a.scene || typeof a.scene !== 'object') return 'Missing "scene"'
  if (!Array.isArray(a.scene.boxes)) return 'scene.boxes must be an array'
  if (!Array.isArray(a.frames)) return 'Missing "frames" array'
  if (a.frames.length === 0) return 'frames is empty'
  if (a.body && !Array.isArray(a.body.vertices)) return 'body.vertices must be an array'
  return null
}
