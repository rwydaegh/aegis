import { describe, it, expect } from 'vitest'
import fixture from './lbs_fixture.json'
import { forwardKinematics, skin } from '../lbs'

describe('client SMPL-X LBS', () => {
  it('matches smplx (no pose blendshapes) within tolerance', () => {
    const J = fixture.parents.length
    const mats = forwardKinematics(fixture.rest_joints, fixture.parents, fixture.pose)
    const v = skin(
      new Float32Array(fixture.template),
      new Float32Array(fixture.weights),
      mats,
      J,
    )
    let maxErr = 0
    for (let i = 0; i < v.length; i++) {
      maxErr = Math.max(maxErr, Math.abs(v[i] - fixture.expected[i]))
    }
    expect(maxErr).toBeLessThan(2e-3) // metres; both sides are pure LBS so this should be tight
  })
})
