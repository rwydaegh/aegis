import { describe, it, expect, beforeEach } from 'vitest'
import pako from 'pako'
import {
  serializeShareableState,
  deserializeShareLink,
  applyShareState,
} from '../shareLink'
import { useEnvironmentStore } from '@/stores/environment'
import { useSimulationStore } from '@/stores/simulation'

// Before this test, the share link did not persist environment source or
// location, so loading a shared OSM/3D-Tiles scene on another machine showed
// an empty scene. Lock in the round-trip for envSource/envLat/envLon and the
// companion radius/options fields consumed by fetchOSM / fetchTilesForRT.

function resetEnvStore() {
  useEnvironmentStore.setState({
    source: 'none',
    location: null,
    locationQuery: '',
    locationFormatted: '',
    radius: 200,
    geometricError: 30,
    osmMeshData: null,
    loading: false,
    geocoding: false,
    error: null,
    osmOptions: {
      defaultBuildingHeight: 10,
      levelHeight: 3.0,
      buildings: true,
      roads: true,
      water: true,
      detail: false,
    },
    geocodeCount: 0,
    _abortController: null,
  })
}

describe('shareLink environment round-trip', () => {
  beforeEach(() => {
    resetEnvStore()
    useSimulationStore.getState().clearResults()
  })

  it('omits default environment state from the diff', () => {
    const encoded = serializeShareableState()
    const decoded = deserializeShareLink(encoded)
    expect(decoded.envSource).toBeUndefined()
    expect(decoded.envLat).toBeUndefined()
    expect(decoded.envLon).toBeUndefined()
  })

  it('persists OSM source, location, radius, and osm options', () => {
    const env = useEnvironmentStore.getState()
    env.setSource('osm')
    env.setLocation(51.0543, 3.7174)
    env.setLocationQuery('Ghent, Belgium')
    env.setLocationFormatted('Ghent, Belgium')
    env.setRadius(350)
    env.setOsmOptions({ defaultBuildingHeight: 12, detail: true })

    const encoded = serializeShareableState()
    const decoded = deserializeShareLink(encoded)

    expect(decoded.envSource).toBe('osm')
    expect(decoded.envLat).toBeCloseTo(51.0543)
    expect(decoded.envLon).toBeCloseTo(3.7174)
    expect(decoded.envLocationQuery).toBe('Ghent, Belgium')
    expect(decoded.envRadius).toBe(350)
    expect(decoded.envOsmOptions?.defaultBuildingHeight).toBe(12)
    expect(decoded.envOsmOptions?.detail).toBe(true)
  })

  it('persists 3dtiles source and geometricError', () => {
    const env = useEnvironmentStore.getState()
    env.setSource('3dtiles')
    env.setLocation(37.7749, -122.4194)
    env.setGeometricError(15)

    const encoded = serializeShareableState()
    const decoded = deserializeShareLink(encoded)

    expect(decoded.envSource).toBe('3dtiles')
    expect(decoded.envGeometricError).toBe(15)
  })

  it('applyShareState restores environment source, location, and radius', () => {
    resetEnvStore()
    applyShareState({
      envSource: 'osm',
      envLat: 51.0543,
      envLon: 3.7174,
      envLocationQuery: 'Ghent, Belgium',
      envLocationFormatted: 'Ghent, Belgium',
      envRadius: 300,
    })
    const env = useEnvironmentStore.getState()
    expect(env.source).toBe('osm')
    expect(env.location).toEqual({ lat: 51.0543, lon: 3.7174 })
    expect(env.locationQuery).toBe('Ghent, Belgium')
    expect(env.radius).toBe(300)
  })

  it('ignores unknown envSource values without touching the store', () => {
    resetEnvStore()
    applyShareState({
      envSource: 'evil_source' as unknown as 'none',
      envLat: 1,
      envLon: 2,
    })
    const env = useEnvironmentStore.getState()
    expect(env.source).toBe('none')
    expect(env.location).toBeNull()
  })
})

describe('shareLink diffraction model round-trip', () => {
  beforeEach(() => {
    resetEnvStore()
    useSimulationStore.setState({
      diffractionModel: 'fock',
      diffraction: true,
      curvature: true,
      interBody: 'off',
    })
  })

  it('omits the default fock model and off inter-body from the diff', () => {
    const decoded = deserializeShareLink(serializeShareableState())
    expect(decoded.diffractionModel).toBeUndefined()
    expect(decoded.interBody).toBeUndefined()
  })

  it('persists a non-default diffraction model and inter-body selector', () => {
    useSimulationStore.getState().setDiffractionModel('gelu')
    useSimulationStore.getState().setInterBody('specular1')

    const decoded = deserializeShareLink(serializeShareableState())
    expect(decoded.diffractionModel).toBe('gelu')
    expect(decoded.interBody).toBe('specular1')
  })

  it('applyShareState restores the diffraction model and keeps diffraction derived', () => {
    useSimulationStore.setState({
      diffractionModel: 'fock',
      diffraction: true,
      curvature: true,
    })
    applyShareState({ diffractionModel: 'none' })
    const sim = useSimulationStore.getState()
    expect(sim.diffractionModel).toBe('none')
    expect(sim.diffraction).toBe(false)
  })
})

// Encode a raw object the same way serializeShareableState does (deflateRaw +
// base64url), bypassing the store so we can forge legacy share payloads.
function encodeLegacy(obj: Record<string, unknown>): string {
  const compressed = pako.deflateRaw(new TextEncoder().encode(JSON.stringify(obj)))
  let binary = ''
  for (const b of compressed) binary += String.fromCharCode(b)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

describe('shareLink legacy diffraction bool back-compat', () => {
  beforeEach(() => {
    resetEnvStore()
  })

  it('decodes a legacy diffraction bool and applies it as a model', () => {
    // Old link: explicit top-level bool, no diffractionModel field.
    const decodedOff = deserializeShareLink(encodeLegacy({ diffraction: false }))
    expect((decodedOff as { diffraction?: boolean }).diffraction).toBe(false)
    expect(decodedOff.diffractionModel).toBeUndefined()

    useSimulationStore.setState({ diffractionModel: 'fock', diffraction: true, curvature: true })
    applyShareState(decodedOff)
    expect(useSimulationStore.getState().diffractionModel).toBe('none')

    const decodedOn = deserializeShareLink(encodeLegacy({ diffraction: true }))
    expect((decodedOn as { diffraction?: boolean }).diffraction).toBe(true)
    useSimulationStore.setState({ diffractionModel: 'none', diffraction: false })
    applyShareState(decodedOn)
    expect(useSimulationStore.getState().diffractionModel).toBe('fock')
  })

  it('lets a new link diffractionModel win over a stale legacy bool', () => {
    const decoded = deserializeShareLink(encodeLegacy({ diffraction: false, diffractionModel: 'gelu' }))
    useSimulationStore.setState({ diffractionModel: 'fock', diffraction: true, curvature: true })
    applyShareState(decoded)
    expect(useSimulationStore.getState().diffractionModel).toBe('gelu')
  })
})
