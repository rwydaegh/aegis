export interface PhysicsState {
  position: [number, number, number]
  velocity: [number, number, number]
  rotationY: number
  angularVelocity: number
  onGround: boolean
}

export interface MovementInput {
  forward: boolean
  back: boolean
  left: boolean
  right: boolean
  rotLeft: boolean
  rotRight: boolean
  jump: boolean
  sprint: boolean
}

export interface PhysicsConfig {
  gravity: number
  walk_accel: number
  max_walk_speed: number
  ground_friction: number
  air_friction: number
  jump_impulse: number
  rotation_accel: number
  max_rotation_speed: number
  rotation_friction: number
  sprint_multiplier: number
  max_step_height: number
  ground_snap: number
  dt_clamp: number
  facing_smooth: number
}

function stepAngular(
  input: MovementInput, rotY: number, angVel: number, config: PhysicsConfig, dt: number,
): { rotY: number; angVel: number } {
  if (input.rotLeft) angVel += config.rotation_accel * dt
  if (input.rotRight) angVel -= config.rotation_accel * dt
  const rotFriction = config.rotation_friction * dt
  if (Math.abs(angVel) <= rotFriction) {
    angVel = 0
  } else {
    angVel -= Math.sign(angVel) * rotFriction
  }
  angVel = Math.max(-config.max_rotation_speed, Math.min(config.max_rotation_speed, angVel))
  return { rotY: rotY + angVel * dt, angVel }
}

function buildMoveDirection(
  input: MovementInput, cameraDirection: [number, number],
): { moveX: number; moveZ: number } {
  const [camX, camZ] = cameraDirection
  const camLen = Math.sqrt(camX * camX + camZ * camZ)
  const fwdX = camLen > 0.0001 ? camX / camLen : 0
  const fwdZ = camLen > 0.0001 ? camZ / camLen : 0
  // Right = forward rotated 90 deg CW in XZ
  const rightX = -fwdZ
  const rightZ = fwdX

  let moveX = 0
  let moveZ = 0
  if (input.forward) { moveX += fwdX; moveZ += fwdZ }
  if (input.back) { moveX -= fwdX; moveZ -= fwdZ }
  if (input.right) { moveX += rightX; moveZ += rightZ }
  if (input.left) { moveX -= rightX; moveZ -= rightZ }

  const moveLen = Math.sqrt(moveX * moveX + moveZ * moveZ)
  if (moveLen > 0.0001) {
    moveX /= moveLen
    moveZ /= moveLen
  }
  return { moveX, moveZ }
}

function stepLateral(
  input: MovementInput, vx: number, vz: number, cameraDirection: [number, number],
  onGround: boolean, config: PhysicsConfig, dt: number,
): { vx: number; vz: number } {
  const { moveX, moveZ } = buildMoveDirection(input, cameraDirection)
  const maxSpeed = config.max_walk_speed * (input.sprint ? config.sprint_multiplier : 1)
  const friction = onGround ? config.ground_friction : config.air_friction

  vx += moveX * config.walk_accel * dt
  vz += moveZ * config.walk_accel * dt

  const lateralSpeed = Math.sqrt(vx * vx + vz * vz)
  if (lateralSpeed > 0) {
    const frictionDelta = friction * dt
    if (lateralSpeed <= frictionDelta) {
      vx = 0
      vz = 0
    } else {
      const scale = (lateralSpeed - frictionDelta) / lateralSpeed
      vx *= scale
      vz *= scale
    }
  }

  const speed = Math.sqrt(vx * vx + vz * vz)
  if (speed > maxSpeed) {
    vx = (vx / speed) * maxSpeed
    vz = (vz / speed) * maxSpeed
  }
  return { vx, vz }
}

function stepVertical(
  input: MovementInput, vy: number, onGround: boolean, config: PhysicsConfig, dt: number,
): { vy: number; onGround: boolean } {
  if (onGround && input.jump) {
    return { vy: config.jump_impulse, onGround: false }
  }
  if (!onGround) {
    vy -= config.gravity * dt
  }
  return { vy, onGround }
}

function integratePositionWithWalls(
  px: number, py: number, pz: number,
  vx: number, vz: number,
  getGroundY: (x: number, z: number, refY: number) => number,
  config: PhysicsConfig, dt: number,
): { px: number; pz: number; vx: number; vz: number } {
  const newPx = px + vx * dt
  if (getGroundY(newPx, pz, py) - py > config.max_step_height) {
    vx = 0
  } else {
    px = newPx
  }

  const newPz = pz + vz * dt
  if (getGroundY(px, newPz, py) - py > config.max_step_height) {
    vz = 0
  } else {
    pz = newPz
  }
  return { px, pz, vx, vz }
}

function resolveGroundCollision(
  px: number, py: number, pz: number, vy: number,
  getGroundY: (x: number, z: number, refY: number) => number,
  config: PhysicsConfig,
): { py: number; vy: number; onGround: boolean } {
  const groundY = getGroundY(px, pz, py)
  if (py <= groundY + config.ground_snap && vy <= 0) {
    return { py: groundY, vy: 0, onGround: true }
  }
  return { py, vy, onGround: py <= groundY + config.ground_snap }
}

function autoStepUp(
  px: number, py: number, pz: number, onGround: boolean,
  getGroundY: (x: number, z: number, refY: number) => number,
  config: PhysicsConfig,
): number {
  if (!onGround) return py
  const probeY = py + config.max_step_height + 0.02
  const higherGround = getGroundY(px, pz, probeY)
  if (higherGround > py + 0.01 && higherGround - py <= config.max_step_height) {
    return higherGround
  }
  return py
}

const FALL_FLOOR_MIN = -20

function applyFallProtection(py: number, vy: number, onGround: boolean): { py: number; vy: number; onGround: boolean } {
  if (py < FALL_FLOOR_MIN) return { py: 0, vy: 0, onGround: true }
  return { py, vy, onGround }
}

function smoothFacing(
  vx: number, vz: number, rotY: number, config: PhysicsConfig, dt: number,
): number {
  const movingSpeed = Math.sqrt(vx * vx + vz * vz)
  if (movingSpeed <= 0.1) return rotY
  const targetRotY = Math.atan2(vx, vz)
  let diff = targetRotY - rotY
  while (diff > Math.PI) diff -= 2 * Math.PI
  while (diff < -Math.PI) diff += 2 * Math.PI
  return rotY + diff * Math.min(1, config.facing_smooth * dt)
}

/**
 * Pure function: takes state + input, returns new state.
 * Camera direction is the flattened XZ forward vector from the camera.
 * getGroundY returns the ground height at a given XZ position.
 */
export function stepPhysics(
  state: PhysicsState,
  input: MovementInput,
  cameraDirection: [number, number],
  getGroundY: (x: number, z: number, refY: number) => number,
  config: PhysicsConfig,
  dt: number,
): PhysicsState {
  dt = Math.min(dt, config.dt_clamp)
  let [px, py, pz] = state.position
  let [vx, vy, vz] = state.velocity

  const ang = stepAngular(input, state.rotationY, state.angularVelocity, config, dt)
  let rotY = ang.rotY
  const angVel = ang.angVel

  const lat = stepLateral(input, vx, vz, cameraDirection, state.onGround, config, dt)
  vx = lat.vx
  vz = lat.vz

  const vert = stepVertical(input, vy, state.onGround, config, dt)
  vy = vert.vy
  let onGround = vert.onGround

  const integrated = integratePositionWithWalls(px, py, pz, vx, vz, getGroundY, config, dt)
  px = integrated.px
  pz = integrated.pz
  vx = integrated.vx
  vz = integrated.vz
  py += vy * dt

  const collided = resolveGroundCollision(px, py, pz, vy, getGroundY, config)
  py = collided.py
  vy = collided.vy
  onGround = collided.onGround

  py = autoStepUp(px, py, pz, onGround, getGroundY, config)

  const fall = applyFallProtection(py, vy, onGround)
  py = fall.py
  vy = fall.vy
  onGround = fall.onGround

  rotY = smoothFacing(vx, vz, rotY, config, dt)

  return {
    position: [px, py, pz],
    velocity: [vx, vy, vz],
    rotationY: rotY,
    angularVelocity: angVel,
    onGround,
  }
}

/**
 * Build a heightmap lookup table from voxel data.
 * Returns a function that looks up ground height.
 */
export function buildHeightmap(
  positions: Float32Array,
  sizes: Float32Array,
  resolutionFactor: number
): (x: number, z: number, refY: number) => number {
  const voxelCount = positions.length / 3

  if (voxelCount === 0) {
    return (_x: number, _z: number, _refY: number) => -Infinity
  }

  // Determine cell size from the first voxel size
  const cellSize = sizes[0] * resolutionFactor

  // Build grid: map from "cx,cz" -> sorted array of voxel top Y values
  const grid = new Map<string, number[]>()

  for (let i = 0; i < voxelCount; i++) {
    const vx = positions[i * 3 + 0]
    const vy = positions[i * 3 + 1]
    const vz = positions[i * 3 + 2]
    const sz = sizes[i]
    const topY = vy + sz / 2

    const cx = Math.floor(vx / cellSize)
    const cz = Math.floor(vz / cellSize)
    const key = `${cx},${cz}`

    if (!grid.has(key)) {
      grid.set(key, [])
    }
    grid.get(key)!.push(topY)
  }

  // Sort each cell's tops ascending
  for (const tops of grid.values()) {
    tops.sort((a, b) => a - b)
  }

  return (x: number, z: number, refY: number): number => {
    const cx = Math.floor(x / cellSize)
    const cz = Math.floor(z / cellSize)
    const key = `${cx},${cz}`
    const tops = grid.get(key)
    if (!tops || tops.length === 0) return -Infinity

    // Find the highest voxel top at or below the body's feet.
    // Using <= with a small epsilon handles floating-point imprecision
    // and prevents the body from sinking through the surface it stands on.
    // This also supports bridges: if the body is below a bridge, only
    // surfaces at or below the body are considered.
    const EPS = 0.01
    let best = -Infinity
    for (const top of tops) {
      if (top <= refY + EPS && top > best) {
        best = top
      }
    }

    // If nothing is at or below refY, body is below all voxels in this cell.
    // Return the lowest top so the body gets pushed up onto the surface.
    if (best === -Infinity) {
      return tops[0]
    }

    return best
  }
}
