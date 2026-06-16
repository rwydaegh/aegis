// Receive (UE) antenna pattern magnitude |C_R(k)|^2, evaluated in the server
// (Z-up) frame the backend uses. These mirror exactly the analytic forms in
// aegis/hotspot/antenna.py (make_rx_response / AntennaPattern.synthetic) so the
// 3D lobe drawn in the scene matches the C_R the precoder is actually built
// from. Shapes are returned un-normalised (relative to their own peak); the
// renderer normalises to the peak, so the constant prefactors are irrelevant.
//
// Convention: theta is measured from +z (the antenna axis), so for a unit
// arrival direction k = (kx, ky, kz), cos(theta) = kz.

export type RxAntennaKind = 'isotropic' | 'vertical' | 'dipole' | 'patch'

// cos^n exponent for the synthetic patch directivity (antenna.py default n=4).
const PATCH_N = 4

// |C_R(k)|^2 for a UNIT direction (kx, ky, kz) in the antenna (Z-up) frame. All
// four patterns are azimuthally symmetric about the +z axis, so only kz enters;
// kx and ky are kept in the signature so callers pass a full direction vector.
export function rxGain(kind: string, _kx: number, _ky: number, kz: number): number {
  switch (kind) {
    case 'isotropic':
    case 'vertical':
      // Both are unit-gain references (|C_R|^2 = 1 in every direction). Vertical
      // carries theta-hat polarisation but the same magnitude, so the lobe is a
      // sphere identical to isotropic.
      return 1
    case 'dipole': {
      // Half-wave dipole: d_theta = [cos(pi/2 cos a) / sin a]^2, axis along z.
      const sin2 = Math.max(1 - kz * kz, 0)
      if (sin2 < 1e-12) return 0
      const num = Math.cos(0.5 * Math.PI * kz)
      return (num * num) / sin2
    }
    case 'patch': {
      // Forward cos^n lobe pointing along +z; zero in the back hemisphere.
      const front = kz
      if (front <= 0) return 0
      return front ** PATCH_N
    }
    default:
      return 1
  }
}

// Peak |C_R|^2 over the sphere (all four kinds normalise to a peak of 1, but
// compute it honestly so tests catch any future pattern that does not).
export function rxPeakGain(kind: string): number {
  switch (kind) {
    case 'dipole':
      return rxGain(kind, 1, 0, 0) // broadside, a = 90 deg
    case 'patch':
      return rxGain(kind, 0, 0, 1) // boresight, +z
    default:
      return 1
  }
}
