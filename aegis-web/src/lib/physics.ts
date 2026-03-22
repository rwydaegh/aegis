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
  dt: number
): PhysicsState {
  dt = Math.min(dt, config.dt_clamp)

  let [px, py, pz] = state.position
  let [vx, vy, vz] = state.velocity
  let rotY = state.rotationY
  let angVel = state.angularVelocity
  let onGround = state.onGround

  // --- Angular dynamics ---
  if (input.rotLeft) angVel += config.rotation_accel * dt
  if (input.rotRight) angVel -= config.rotation_accel * dt
  // Friction on angular velocity
  const rotFriction = config.rotation_friction * dt
  if (Math.abs(angVel) <= rotFriction) {
    angVel = 0
  } else {
    angVel -= Math.sign(angVel) * rotFriction
  }
  angVel = Math.max(-config.max_rotation_speed, Math.min(config.max_rotation_speed, angVel))
  rotY += angVel * dt

  // --- Lateral dynamics ---
  // Build move direction in world XZ relative to camera direction
  const [camX, camZ] = cameraDirection
  // Normalize camera direction
  const camLen = Math.sqrt(camX * camX + camZ * camZ)
  let fwdX = 0
  let fwdZ = 0
  if (camLen > 0.0001) {
    fwdX = camX / camLen
    fwdZ = camZ / camLen
  }
  // Right is perpendicular to forward (rotate 90 degrees CW in XZ plane)
  // For camera looking down -Z: fwd=(0,-1), right should be (+1,0) = positive X
  const rightX = -fwdZ
  const rightZ = fwdX

  let moveX = 0
  let moveZ = 0
  if (input.forward) { moveX += fwdX; moveZ += fwdZ }
  if (input.back) { moveX -= fwdX; moveZ -= fwdZ }
  if (input.right) { moveX += rightX; moveZ += rightZ }
  if (input.left) { moveX -= rightX; moveZ -= rightZ }

  // Normalize move direction
  const moveLen = Math.sqrt(moveX * moveX + moveZ * moveZ)
  if (moveLen > 0.0001) {
    moveX /= moveLen
    moveZ /= moveLen
  }

  const accel = config.walk_accel
  const maxSpeed = config.max_walk_speed * (input.sprint ? config.sprint_multiplier : 1)
  const friction = onGround ? config.ground_friction : config.air_friction

  // Apply acceleration
  vx += moveX * accel * dt
  vz += moveZ * accel * dt

  // Apply friction to lateral velocity
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

  // Clamp lateral speed
  const speed = Math.sqrt(vx * vx + vz * vz)
  if (speed > maxSpeed) {
    vx = (vx / speed) * maxSpeed
    vz = (vz / speed) * maxSpeed
  }

  // --- Vertical dynamics ---
  if (onGround && input.jump) {
    vy = config.jump_impulse
    onGround = false
  }

  if (!onGround) {
    vy -= config.gravity * dt
  }

  // --- Integrate position ---
  // Test X movement independently for wall sliding
  const newPxCandidate = px + vx * dt
  const groundYAtNewX = getGroundY(newPxCandidate, pz, py)
  const stepAtX = groundYAtNewX - py
  if (stepAtX > config.max_step_height) {
    // Wall in X direction - cancel X movement
    vx = 0
  } else {
    px = newPxCandidate
  }

  // Test Z movement independently for wall sliding
  const newPzCandidate = pz + vz * dt
  const groundYAtNewZ = getGroundY(px, newPzCandidate, py)
  const stepAtZ = groundYAtNewZ - py
  if (stepAtZ > config.max_step_height) {
    // Wall in Z direction - cancel Z movement
    vz = 0
  } else {
    pz = newPzCandidate
  }

  // Vertical movement
  py += vy * dt

  // --- Ground collision ---
  const groundY = getGroundY(px, pz, py)
  if (py <= groundY + config.ground_snap && vy <= 0) {
    py = groundY
    vy = 0
    onGround = true
  } else if (py > groundY + config.ground_snap) {
    onGround = false
  }

  // --- Fall-through protection ---
  // If the player falls below a minimum Y (no voxels below), teleport to y=0
  const FLOOR_MIN = -20
  if (py < FLOOR_MIN) {
    py = 0
    vy = 0
    onGround = true
  }

  // --- Smooth facing ---
  // Body rotation follows movement direction when moving
  const movingSpeed = Math.sqrt(vx * vx + vz * vz)
  if (movingSpeed > 0.1) {
    const targetRotY = Math.atan2(vx, vz)
    // Shortest angle interpolation
    let diff = targetRotY - rotY
    while (diff > Math.PI) diff -= 2 * Math.PI
    while (diff < -Math.PI) diff += 2 * Math.PI
    rotY += diff * Math.min(1, config.facing_smooth * dt)
  }

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
