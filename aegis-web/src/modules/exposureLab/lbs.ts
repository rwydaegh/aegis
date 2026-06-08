// Client-side SMPL-X linear blend skinning (LBS).
//
// Mirrors the SMPL-X forward pass with pose blendshapes (posedirs) intentionally
// skipped, so the live preview matches a smplx oracle generated the same way.
// All matrices are flat, row-major. 3x3 -> 9 numbers, 4x4 -> 16 numbers.
//
// Conventions (see SMPL-X / lbs):
//   L_j = [ R_j | (J_j - J_parent) ]          local transform (root: translation = J_0)
//   G_j = G_parent @ L_j                        world transform via FK
//   A_j = G_j @ [ I | -J_j ]                    skinning matrix (removes rest pose)
//   v' = sum_j w_vj (A_j @ [v_rest; 1])[:3]    skinned vertex
//
// Joints >= 22 (hands/jaw/eyes) have no pose entry and use identity rotation.

const POSED_JOINTS = 22 // joints 0..21 have axis-angle pose entries

// Curated manipulable joints, as full-skeleton SMPL-X indices J. The pose slot
// for joint J is pose[3J : 3J+3]. Derived from the standard SMPL-X tree where
// J=0 is the pelvis (global orient) and body joint b occupies J = b + 1.
// Ankles, feet, hands and face joints are intentionally omitted.
export interface CuratedJoint {
  index: number // full-skeleton joint index J
  label: string
}

export const CURATED_JOINTS: CuratedJoint[] = [
  { index: 0, label: 'pelvis (global)' },
  { index: 3, label: 'spine 1' },
  { index: 6, label: 'spine 2' },
  { index: 9, label: 'spine 3' },
  { index: 12, label: 'neck' },
  { index: 15, label: 'head' },
  { index: 13, label: 'left collar' },
  { index: 14, label: 'right collar' },
  { index: 16, label: 'left shoulder' },
  { index: 17, label: 'right shoulder' },
  { index: 18, label: 'left elbow' },
  { index: 19, label: 'right elbow' },
  { index: 20, label: 'left wrist' },
  { index: 21, label: 'right wrist' },
  { index: 1, label: 'left hip' },
  { index: 2, label: 'right hip' },
  { index: 4, label: 'left knee' },
  { index: 5, label: 'right knee' },
]

// Rodrigues: axis-angle (x, y, z) -> row-major 3x3 rotation matrix (9 numbers).
export function axisAngleToMat3(x: number, y: number, z: number): number[] {
  const theta = Math.sqrt(x * x + y * y + z * z)
  if (theta < 1e-12) {
    return [1, 0, 0, 0, 1, 0, 0, 0, 1]
  }
  const kx = x / theta
  const ky = y / theta
  const kz = z / theta
  const s = Math.sin(theta)
  const c = Math.cos(theta)
  const v = 1 - c
  // R = I + sin(t) K + (1 - cos(t)) K^2, K = skew(k)
  return [
    c + kx * kx * v,
    kx * ky * v - kz * s,
    kx * kz * v + ky * s,
    ky * kx * v + kz * s,
    c + ky * ky * v,
    ky * kz * v - kx * s,
    kz * kx * v - ky * s,
    kz * ky * v + kx * s,
    c + kz * kz * v,
  ]
}

// out = a @ b, all row-major 4x4 flat (length 16). out may not alias a or b.
function mul4(out: Float32Array, a: Float32Array | number[], b: Float32Array | number[]): void {
  for (let r = 0; r < 4; r++) {
    for (let col = 0; col < 4; col++) {
      let sum = 0
      for (let k = 0; k < 4; k++) {
        sum += a[r * 4 + k] * b[k * 4 + col]
      }
      out[r * 4 + col] = sum
    }
  }
}

// Compute the world transforms G_j (row-major 4x4), returned as a flat
// Float32Array of length nJoints * 16. G_j = G_parent @ L_j via FK.
export function worldTransforms(
  restJoints: Float32Array | number[],
  parents: number[],
  pose: Float32Array | number[],
): Float32Array {
  const nJoints = parents.length
  const G = new Float32Array(nJoints * 16) // world transforms
  const local = new Float32Array(16)

  for (let j = 0; j < nJoints; j++) {
    const parent = parents[j]
    const jx = restJoints[j * 3]
    const jy = restJoints[j * 3 + 1]
    const jz = restJoints[j * 3 + 2]

    // Rotation: posed joints use Rodrigues, the rest use identity.
    let R: number[]
    if (j < POSED_JOINTS) {
      R = axisAngleToMat3(pose[j * 3], pose[j * 3 + 1], pose[j * 3 + 2])
    } else {
      R = [1, 0, 0, 0, 1, 0, 0, 0, 1]
    }

    // Parent-relative translation (root translates by its own rest position).
    let tx = jx
    let ty = jy
    let tz = jz
    if (parent !== -1) {
      tx -= restJoints[parent * 3]
      ty -= restJoints[parent * 3 + 1]
      tz -= restJoints[parent * 3 + 2]
    }

    // local = [ R | t ]
    local[0] = R[0]
    local[1] = R[1]
    local[2] = R[2]
    local[3] = tx
    local[4] = R[3]
    local[5] = R[4]
    local[6] = R[5]
    local[7] = ty
    local[8] = R[6]
    local[9] = R[7]
    local[10] = R[8]
    local[11] = tz
    local[12] = 0
    local[13] = 0
    local[14] = 0
    local[15] = 1

    const go = j * 16
    if (parent === -1) {
      G.set(local, go)
    } else {
      const parentG = G.subarray(parent * 16, parent * 16 + 16)
      const dst = new Float32Array(16)
      mul4(dst, parentG, local)
      G.set(dst, go)
    }
  }

  return G
}

// Convert the rotation part (upper-left 3x3) of a row-major 4x4 stored at
// `base` into a unit quaternion (x, y, z, w), written into `out` at `outBase`.
function mat4RotToQuat(G: Float32Array, base: number, out: Float32Array, outBase: number): void {
  const m00 = G[base], m01 = G[base + 1], m02 = G[base + 2]
  const m10 = G[base + 4], m11 = G[base + 5], m12 = G[base + 6]
  const m20 = G[base + 8], m21 = G[base + 9], m22 = G[base + 10]
  const trace = m00 + m11 + m22
  let x: number, y: number, z: number, w: number
  if (trace > 0) {
    const s = 0.5 / Math.sqrt(trace + 1)
    w = 0.25 / s
    x = (m21 - m12) * s
    y = (m02 - m20) * s
    z = (m10 - m01) * s
  } else if (m00 > m11 && m00 > m22) {
    const s = 2 * Math.sqrt(1 + m00 - m11 - m22)
    w = (m21 - m12) / s
    x = 0.25 * s
    y = (m01 + m10) / s
    z = (m02 + m20) / s
  } else if (m11 > m22) {
    const s = 2 * Math.sqrt(1 + m11 - m00 - m22)
    w = (m02 - m20) / s
    x = (m01 + m10) / s
    y = 0.25 * s
    z = (m12 + m21) / s
  } else {
    const s = 2 * Math.sqrt(1 + m22 - m00 - m11)
    w = (m10 - m01) / s
    x = (m02 + m20) / s
    y = (m12 + m21) / s
    z = 0.25 * s
  }
  out[outBase] = x
  out[outBase + 1] = y
  out[outBase + 2] = z
  out[outBase + 3] = w
}

// World joint transforms for gizmo placement: each joint's WORLD position (the
// translation of G_j) and WORLD rotation (the rotation of G_j as a quaternion).
export function posedJointTransforms(
  restJoints: Float32Array | number[],
  parents: number[],
  pose: Float32Array | number[],
): { positions: Float32Array; worldQuats: Float32Array } {
  const nJoints = parents.length
  const G = worldTransforms(restJoints, parents, pose)
  const positions = new Float32Array(nJoints * 3)
  const worldQuats = new Float32Array(nJoints * 4)
  for (let j = 0; j < nJoints; j++) {
    const go = j * 16
    positions[j * 3] = G[go + 3]
    positions[j * 3 + 1] = G[go + 7]
    positions[j * 3 + 2] = G[go + 11]
    mat4RotToQuat(G, go, worldQuats, j * 4)
  }
  return { positions, worldQuats }
}

// Build the 55 skinning matrices A_j (row-major 4x4), returned as a flat
// Float32Array of length nJoints * 16, ready for `skin`.
export function forwardKinematics(
  restJoints: Float32Array | number[],
  parents: number[],
  pose: Float32Array | number[],
): Float32Array {
  const nJoints = parents.length
  const G = worldTransforms(restJoints, parents, pose)
  const A = new Float32Array(nJoints * 16) // skinning matrices
  const restInv = new Float32Array(16)

  for (let j = 0; j < nJoints; j++) {
    const jx = restJoints[j * 3]
    const jy = restJoints[j * 3 + 1]
    const jz = restJoints[j * 3 + 2]
    const go = j * 16

    // restInv = [ I | -J_j ]
    restInv[0] = 1
    restInv[1] = 0
    restInv[2] = 0
    restInv[3] = -jx
    restInv[4] = 0
    restInv[5] = 1
    restInv[6] = 0
    restInv[7] = -jy
    restInv[8] = 0
    restInv[9] = 0
    restInv[10] = 1
    restInv[11] = -jz
    restInv[12] = 0
    restInv[13] = 0
    restInv[14] = 0
    restInv[15] = 1

    // A_j = G_j @ restInv
    const Aj = new Float32Array(16)
    mul4(Aj, G.subarray(go, go + 16), restInv)
    A.set(Aj, go)
  }

  return A
}

// Skin vertices: for each vertex v, blend its weighted skinning matrices and
// transform its rest (shaped, no pose blendshapes) position.
//   template: V*3 rest positions
//   weights:  V*nJoints LBS weights (row v = template vertex v)
//   skinningMats: nJoints*16 from forwardKinematics
// Returns V*3 posed positions.
export function skin(
  template: Float32Array,
  weights: Float32Array | number[],
  skinningMats: Float32Array,
  nJoints: number,
): Float32Array {
  const nVerts = template.length / 3
  const out = new Float32Array(nVerts * 3)
  const T = new Float32Array(16) // blended matrix for the current vertex

  for (let v = 0; v < nVerts; v++) {
    T.fill(0)
    const wBase = v * nJoints
    for (let j = 0; j < nJoints; j++) {
      const w = weights[wBase + j]
      if (w === 0) continue
      const mBase = j * 16
      for (let e = 0; e < 16; e++) {
        T[e] += w * skinningMats[mBase + e]
      }
    }

    const vx = template[v * 3]
    const vy = template[v * 3 + 1]
    const vz = template[v * 3 + 2]
    // Homogeneous transform with w = 1 (T is affine, bottom row stays [0,0,0,1]).
    out[v * 3] = T[0] * vx + T[1] * vy + T[2] * vz + T[3]
    out[v * 3 + 1] = T[4] * vx + T[5] * vy + T[6] * vz + T[7]
    out[v * 3 + 2] = T[8] * vx + T[9] * vy + T[10] * vz + T[11]
  }

  return out
}
