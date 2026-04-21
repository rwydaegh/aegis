import { describe, it, expect, beforeEach } from 'vitest'
import { useEnvironmentStore } from '../environment'

function seedMesh() {
  useEnvironmentStore.setState({
    osmMeshData: {
      positions: new Float32Array(9),
      indices: new Uint32Array(3),
      normals: new Float32Array(9),
      materials: new Uint8Array(1),
      meta: {},
    },
  })
}

describe('environment store setSource', () => {
  beforeEach(() => {
    useEnvironmentStore.setState({
      source: 'none',
      osmMeshData: null,
      loading: false,
      error: null,
      _abortController: null,
    })
  })

  it('clears osmMeshData on direct osm -> 3dtiles transition', () => {
    useEnvironmentStore.setState({ source: 'osm' })
    seedMesh()
    useEnvironmentStore.getState().setSource('3dtiles')
    expect(useEnvironmentStore.getState().osmMeshData).toBeNull()
    expect(useEnvironmentStore.getState().source).toBe('3dtiles')
  })

  it('clears osmMeshData on direct 3dtiles -> osm transition', () => {
    useEnvironmentStore.setState({ source: '3dtiles' })
    seedMesh()
    useEnvironmentStore.getState().setSource('osm')
    expect(useEnvironmentStore.getState().osmMeshData).toBeNull()
  })

  it('preserves osmMeshData when switching to a non-mesh source', () => {
    useEnvironmentStore.setState({ source: 'osm' })
    seedMesh()
    useEnvironmentStore.getState().setSource('none')
    expect(useEnvironmentStore.getState().osmMeshData).not.toBeNull()
  })

  it('preserves osmMeshData when coming back from a non-mesh source', () => {
    useEnvironmentStore.setState({ source: 'osm' })
    seedMesh()
    useEnvironmentStore.getState().setSource('voxels')
    useEnvironmentStore.getState().setSource('osm')
    expect(useEnvironmentStore.getState().osmMeshData).not.toBeNull()
  })

  it('preserves osmMeshData when re-selecting the same source', () => {
    useEnvironmentStore.setState({ source: 'osm' })
    seedMesh()
    useEnvironmentStore.getState().setSource('osm')
    expect(useEnvironmentStore.getState().osmMeshData).not.toBeNull()
  })

  it('aborts an in-flight request on source change', () => {
    const controller = new AbortController()
    useEnvironmentStore.setState({ _abortController: controller, source: 'osm' })
    useEnvironmentStore.getState().setSource('3dtiles')
    expect(controller.signal.aborted).toBe(true)
    expect(useEnvironmentStore.getState()._abortController).toBeNull()
  })
})
