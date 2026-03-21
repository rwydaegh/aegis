import { describe, it, expect } from 'vitest'
import { toServer, toScene, type ServerPos, type ScenePos } from '../coordinates'

describe('coordinate conversion', () => {
  it('toServer converts Y-up to Z-up', () => {
    const scene: ScenePos = [1, 2, 3]
    const server = toServer(scene)
    expect(server).toEqual([1, -3, 2])
  })

  it('toScene converts Z-up to Y-up', () => {
    const server: ServerPos = [1, 2, 3]
    const scene = toScene(server)
    expect(scene).toEqual([1, 3, -2])
  })

  it('roundtrips correctly', () => {
    const original: ScenePos = [4.5, -1.2, 3.7]
    const roundtripped = toScene(toServer(original))
    expect(roundtripped[0]).toBeCloseTo(original[0])
    expect(roundtripped[1]).toBeCloseTo(original[1])
    expect(roundtripped[2]).toBeCloseTo(original[2])
  })
})
