import { describe, it, expect } from 'vitest'
import { parseBodyBinary, parseVoxelBinary, parseSabBinary } from '../binary'

describe('parseBodyBinary', () => {
  it('parses positions and normals with Z-up to Y-up swap', () => {
    const pos = new Float32Array([1, 2, 3, 4, 5, 6])
    const nrm = new Float32Array([0, 0, 1, 0, 0, 1])
    const buffer = new ArrayBuffer(pos.byteLength + nrm.byteLength)
    new Float32Array(buffer, 0, 6).set(pos)
    new Float32Array(buffer, pos.byteLength, 6).set(nrm)

    const result = parseBodyBinary(buffer, 2)
    expect(result.positions[0]).toBe(1)   // x
    expect(result.positions[1]).toBe(3)   // z -> y
    expect(result.positions[2]).toBe(-2)  // -y -> z
  })
})

describe('parseSabBinary', () => {
  it('parses float32 array', () => {
    const data = new Float32Array([0.5, 1.2, 0.0, 3.7])
    const result = parseSabBinary(data.buffer)
    expect(result.length).toBe(4)
    expect(result[0]).toBeCloseTo(0.5)
    expect(result[3]).toBeCloseTo(3.7)
  })
})
