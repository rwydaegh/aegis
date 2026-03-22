import { describe, it, expect } from 'vitest'
import { stepPhysics, buildHeightmap, type PhysicsState, type MovementInput, type PhysicsConfig } from '../physics'

const DEFAULT_CONFIG: PhysicsConfig = {
  gravity: 20,
  walk_accel: 50,
  max_walk_speed: 5,
  ground_friction: 12,
  air_friction: 2,
  jump_impulse: 8,
  rotation_accel: 8,
  max_rotation_speed: 3,
  rotation_friction: 10,
  sprint_multiplier: 2,
  max_step_height: 0.4,
  ground_snap: 0.1,
  dt_clamp: 0.05,
  facing_smooth: 8,
}

const NO_INPUT: MovementInput = {
  forward: false, back: false, left: false, right: false,
  rotLeft: false, rotRight: false, jump: false, sprint: false,
}

const FLAT_GROUND = (_x: number, _z: number, _y: number) => 0

function airborneState(): PhysicsState {
  return {
    position: [0, 5, 0],
    velocity: [0, 0, 0],
    rotationY: 0,
    angularVelocity: 0,
    onGround: false,
  }
}

function groundedState(): PhysicsState {
  return {
    position: [0, 0, 0],
    velocity: [0, 0, 0],
    rotationY: 0,
    angularVelocity: 0,
    onGround: true,
  }
}

describe('stepPhysics - gravity', () => {
  it('pulls body downward when airborne', () => {
    const state = airborneState()
    const next = stepPhysics(state, NO_INPUT, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    expect(next.velocity[1]).toBeLessThan(0)
    expect(next.position[1]).toBeLessThan(5)
  })

  it('does not apply gravity below ground', () => {
    // Body on ground, no vertical velocity
    const state = groundedState()
    const next = stepPhysics(state, NO_INPUT, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    expect(next.position[1]).toBeGreaterThanOrEqual(-0.01)
    expect(next.onGround).toBe(true)
  })
})

describe('stepPhysics - jump', () => {
  it('applies jump impulse when grounded and jump pressed', () => {
    const state = groundedState()
    const input: MovementInput = { ...NO_INPUT, jump: true }
    const next = stepPhysics(state, input, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    expect(next.velocity[1]).toBeGreaterThan(0)
  })

  it('does not jump when already airborne', () => {
    const state = airborneState()
    const input: MovementInput = { ...NO_INPUT, jump: true }
    const next = stepPhysics(state, input, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    // No jump impulse added - velocity stays at 0 or decreases due to gravity
    expect(next.velocity[1]).toBeLessThanOrEqual(0)
  })
})

describe('stepPhysics - friction', () => {
  it('decelerates when no input', () => {
    const state: PhysicsState = {
      position: [0, 0, 0],
      velocity: [3, 0, 0],
      rotationY: 0,
      angularVelocity: 0,
      onGround: true,
    }
    const next = stepPhysics(state, NO_INPUT, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    expect(Math.abs(next.velocity[0])).toBeLessThan(3)
  })

  it('applies air friction when airborne', () => {
    const state: PhysicsState = {
      position: [0, 5, 0],
      velocity: [3, 0, 0],
      rotationY: 0,
      angularVelocity: 0,
      onGround: false,
    }
    const next = stepPhysics(state, NO_INPUT, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    // Air friction is less than ground friction, but still decelerates
    expect(Math.abs(next.velocity[0])).toBeLessThan(3)
  })
})

describe('stepPhysics - max speed', () => {
  it('clamps speed to max_walk_speed', () => {
    // Apply forward input for many steps
    let state = groundedState()
    const input: MovementInput = { ...NO_INPUT, forward: true }
    for (let i = 0; i < 100; i++) {
      state = stepPhysics(state, input, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    }
    const speed = Math.sqrt(state.velocity[0] ** 2 + state.velocity[2] ** 2)
    expect(speed).toBeLessThanOrEqual(DEFAULT_CONFIG.max_walk_speed + 0.01)
  })

  it('allows higher speed with sprint', () => {
    let state = groundedState()
    const walkInput: MovementInput = { ...NO_INPUT, forward: true }
    const sprintInput: MovementInput = { ...NO_INPUT, forward: true, sprint: true }

    let walkState = state
    let sprintState = state
    for (let i = 0; i < 100; i++) {
      walkState = stepPhysics(walkState, walkInput, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
      sprintState = stepPhysics(sprintState, sprintInput, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    }
    const walkSpeed = Math.sqrt(walkState.velocity[0] ** 2 + walkState.velocity[2] ** 2)
    const sprintSpeed = Math.sqrt(sprintState.velocity[0] ** 2 + sprintState.velocity[2] ** 2)
    expect(sprintSpeed).toBeGreaterThan(walkSpeed * 1.5)
  })
})

describe('stepPhysics - ground collision', () => {
  it('prevents falling through ground', () => {
    const state: PhysicsState = {
      position: [0, 0.5, 0],
      velocity: [0, -10, 0],
      rotationY: 0,
      angularVelocity: 0,
      onGround: false,
    }
    let current = state
    for (let i = 0; i < 60; i++) {
      current = stepPhysics(current, NO_INPUT, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    }
    expect(current.position[1]).toBeGreaterThanOrEqual(-0.01)
    expect(current.onGround).toBe(true)
  })
})

describe('stepPhysics - step height', () => {
  it('stops at a wall taller than max_step_height', () => {
    // Wall at x=1, ground is 2m high (above max_step_height=0.4)
    const tallWall = (x: number, _z: number, _y: number) => {
      if (x >= 0.9) return 2.0
      return 0
    }
    let state: PhysicsState = {
      position: [0, 0, 0],
      velocity: [3, 0, 0],
      rotationY: 0,
      angularVelocity: 0,
      onGround: true,
    }
    const input: MovementInput = { ...NO_INPUT, forward: true }
    // Move toward wall for many steps
    for (let i = 0; i < 100; i++) {
      state = stepPhysics(state, input, [1, 0], tallWall, DEFAULT_CONFIG, 0.016)
    }
    // Should be stopped before the wall
    expect(state.position[0]).toBeLessThan(1.5)
  })
})

describe('stepPhysics - left/right direction', () => {
  it('D key moves in +X when camera looks down -Z', () => {
    // Camera looking down -Z: cameraDirection = [0, -1]
    // D (right) should move in +X direction
    let state = groundedState()
    const input: MovementInput = { ...NO_INPUT, right: true }
    for (let i = 0; i < 30; i++) {
      state = stepPhysics(state, input, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    }
    expect(state.position[0]).toBeGreaterThan(0) // moved in +X (right)
  })

  it('A key moves in -X when camera looks down -Z', () => {
    // Camera looking down -Z: cameraDirection = [0, -1]
    // A (left) should move in -X direction
    let state = groundedState()
    const input: MovementInput = { ...NO_INPUT, left: true }
    for (let i = 0; i < 30; i++) {
      state = stepPhysics(state, input, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    }
    expect(state.position[0]).toBeLessThan(0) // moved in -X (left)
  })

  it('D key moves in +Z when camera looks down +X', () => {
    // Camera looking down +X: cameraDirection = [1, 0]
    // D (right) should move in +Z direction
    let state = groundedState()
    const input: MovementInput = { ...NO_INPUT, right: true }
    for (let i = 0; i < 30; i++) {
      state = stepPhysics(state, input, [1, 0], FLAT_GROUND, DEFAULT_CONFIG, 0.016)
    }
    expect(state.position[2]).toBeGreaterThan(0) // moved in +Z
  })
})

describe('stepPhysics - fall-through protection', () => {
  it('teleports to y=0 when falling below floor minimum', () => {
    const state: PhysicsState = {
      position: [5, -25, 5],
      velocity: [0, -10, 0],
      rotationY: 0,
      angularVelocity: 0,
      onGround: false,
    }
    const noVoxels = (_x: number, _z: number, _y: number) => -Infinity
    const next = stepPhysics(state, NO_INPUT, [0, -1], noVoxels, DEFAULT_CONFIG, 0.016)
    expect(next.position[1]).toBe(0)
    expect(next.onGround).toBe(true)
  })
})

describe('stepPhysics - dt clamp', () => {
  it('clamps large dt values', () => {
    const state = groundedState()
    // Pass a huge dt - should be clamped
    const next = stepPhysics(state, NO_INPUT, [0, -1], FLAT_GROUND, DEFAULT_CONFIG, 10)
    // Should not fly off to infinity
    expect(Math.abs(next.position[0])).toBeLessThan(100)
    expect(Math.abs(next.position[1])).toBeLessThan(100)
  })
})

describe('buildHeightmap', () => {
  it('returns ground level below all voxels when no voxels above query Y', () => {
    // Single voxel at (0,0,0) with size 1 -> top is at 0.5
    const positions = new Float32Array([0, 0, 0])
    const sizes = new Float32Array([1])
    const lookup = buildHeightmap(positions, sizes, 1)
    // Query above the voxel top: should return voxel top = 0.5
    const y = lookup(0, 0, 2)
    expect(y).toBeCloseTo(0.5, 3)
  })

  it('returns -Infinity when no voxels in cell', () => {
    const positions = new Float32Array([0, 0, 0])
    const sizes = new Float32Array([1])
    const lookup = buildHeightmap(positions, sizes, 1)
    // Query far away from the voxel
    const y = lookup(100, 100, 0)
    expect(y).toBe(-Infinity)
  })

  it('stacks: returns highest voxel top below query Y', () => {
    // Two voxels stacked: lower at y=0 (top=0.5), upper at y=1 (top=1.5)
    const positions = new Float32Array([0, 0, 0, 0, 1, 0])
    const sizes = new Float32Array([1, 1])
    const lookup = buildHeightmap(positions, sizes, 1)
    // Query at y=2: should find highest top below 2 -> 1.5
    const y = lookup(0, 0, 2)
    expect(y).toBeCloseTo(1.5, 3)
    // Query at y=1: should find top at or below 1 -> 0.5
    const y2 = lookup(0, 0, 1)
    expect(y2).toBeCloseTo(0.5, 3)
  })

  it('does not sink through surface when standing exactly on top', () => {
    // 3-voxel thick ground: tops at 0.122, 0.366, 0.610
    const positions = new Float32Array([0, 0, 0, 0, 0.244, 0, 0, 0.488, 0])
    const sizes = new Float32Array([0.244, 0.244, 0.244])
    const lookup = buildHeightmap(positions, sizes, 1)
    // Standing exactly at the top surface (0.610) should return 0.610, not sink
    const y = lookup(0, 0, 0.610)
    expect(y).toBeCloseTo(0.610, 2)
  })

  it('supports bridge: returns ground under bridge, not bridge top', () => {
    // Ground at y=0 (top=0.5), bridge at y=5 (top=5.5)
    const positions = new Float32Array([0, 0, 0, 0, 5, 0])
    const sizes = new Float32Array([1, 1])
    const lookup = buildHeightmap(positions, sizes, 1)
    // Body under bridge at y=1: should return ground (0.5), not bridge (5.5)
    const y = lookup(0, 0, 1)
    expect(y).toBeCloseTo(0.5, 3)
    // Body on bridge at y=5.5: should return bridge top (5.5)
    const y2 = lookup(0, 0, 5.5)
    expect(y2).toBeCloseTo(5.5, 3)
  })
})
