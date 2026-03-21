/** Server-side position: Z-up (Python/AEGIS convention) */
export type ServerPos = [x: number, y: number, z: number]

/** Scene-side position: Y-up (Three.js convention) */
export type ScenePos = [x: number, y: number, z: number]

/** Convert Y-up (Three.js) to Z-up (server): [x, y, z] -> [x, -z, y] */
export function toServer(p: ScenePos): ServerPos {
  return [p[0], -p[2], p[1]]
}

/** Convert Z-up (server) to Y-up (Three.js): [x, y, z] -> [x, z, -y] */
export function toScene(p: ServerPos): ScenePos {
  return [p[0], p[2], -p[1]]
}
