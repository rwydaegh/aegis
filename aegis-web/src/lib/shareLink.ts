import pako from 'pako'
import { SHARE_DEFAULTS, type ShareState } from './shareDefaults'
import { useSimulationStore } from '../stores/simulation'
import { useSceneStore } from '../stores/scene'
import { useUIStore } from '../stores/ui'
import type { QuantityKey } from '../stores/ui'
import { useAntennaStore } from '../stores/antenna'
import { useEnvironmentStore, type EnvironmentSource } from '../stores/environment'
import type { ElementPattern } from '../api/types'
import { cameraState } from './cameraState'

// ---------------------------------------------------------------------------
// Base64url helpers (RFC 4648 section 5)
// ---------------------------------------------------------------------------

function toBase64Url(bytes: Uint8Array): string {
  let binary = ''
  for (const b of bytes) binary += String.fromCharCode(b)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function fromBase64Url(str: string): Uint8Array {
  const padded = str.replace(/-/g, '+').replace(/_/g, '/') +
    '='.repeat((4 - str.length % 4) % 4)
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

// ---------------------------------------------------------------------------
// State collection
// ---------------------------------------------------------------------------

// Collect current shareable state from all three stores
export function collectState(): Record<string, unknown> {
  const sim = useSimulationStore.getState()
  const scene = useSceneStore.getState()
  const ui = useUIStore.getState()
  const env = useEnvironmentStore.getState()

  return {
    // environment store
    envSource: env.source,
    envLat: env.location?.lat ?? null,
    envLon: env.location?.lon ?? null,
    envLocationQuery: env.locationQuery,
    envLocationFormatted: env.locationFormatted,
    envRadius: env.radius,
    envGeometricError: env.geometricError,
    envOsmOptions: { ...env.osmOptions },
    // simulation store
    antennaPos: sim.antennaPos,
    mode: sim.mode,
    fresnel: sim.fresnel,
    polarisation: sim.polarisation,
    curvature: sim.curvature,
    diffractionModel: sim.diffractionModel,
    interBody: sim.interBody,
    powerDbm: sim.powerDbm,
    skinModel: sim.skinModel,
    freqGhz: sim.freqGhz,
    exposureMode: sim.exposureMode,
    stochasticPreset: sim.stochasticPreset,
    stochasticSeed: sim.stochasticSeed,
    stochasticOverrides: sim.stochasticOverrides,
    bodyOffset: sim.bodyOffset,
    bodyRotationY: sim.bodyRotationY,
    // enabledQuantities is a Set; convert to sorted array for stable serialization
    enabledQuantities: [...sim.enabledQuantities].sort(),
    displayQuantity: sim.displayQuantity,
    // scene store
    bodyName: scene.bodyName,
    pathSource: scene.pathSource,
    rtSource: scene.rtSource,
    rtMaxOrder: scene.rtMaxOrder,
    rtConfig: { ...scene.rtConfig },
    envDisplayMode: scene.envDisplayMode,
    // display config from scene store
    colormapName: scene.colormapName,
    sunIntensity: scene.sunIntensity,
    ambientIntensity: scene.ambientIntensity,
    cameraFov: scene.cameraFov,
    // scene visibility
    bodyMeshVisible: scene.bodyMeshVisible,
    groundPlaneVisible: scene.groundPlaneVisible,
    gridVisible: scene.gridVisible,
    sceneGeometryVisible: scene.sceneGeometryVisible,
    // camera position (rounded to 3 decimals for compact URLs)
    cameraPosition: cameraState.position.map(v => Math.round(v * 1000) / 1000) as [number, number, number],
    cameraTarget: cameraState.target.map(v => Math.round(v * 1000) / 1000) as [number, number, number],
    // ui store
    wireframe: ui.wireframe,
    legendScale: ui.legendScale,
    dynamicRangeDb: ui.dynamicRangeDb,
    ratioMode: ui.ratioMode,
    exposureScenario: ui.exposureScenario,
    // antenna store (multi-antenna)
    ...collectAntennaState(),
  }
}

function collectAntennaState(): Pick<ShareState, 'antennas' | 'selectedAntennaId'> {
  const antStore = useAntennaStore.getState()
  const antennas = [...antStore.antennas.values()].map(a => ({
    id: a.id,
    name: a.name,
    position: a.position as [number, number, number],
    height: a.height,
    focusPoint: a.focusPoint,
    powerDbm: a.powerDbm,
    arrayConfig: { ...a.arrayConfig },
    enabled: a.enabled,
  }))
  return {
    antennas,
    selectedAntennaId: antStore.selectedId,
  }
}

// Diff current state against defaults; return only changed fields
function diffState(current: Record<string, unknown>): Record<string, unknown> {
  const diff: Record<string, unknown> = {}
  for (const [key, defaultVal] of Object.entries(SHARE_DEFAULTS)) {
    const currentVal = current[key]
    if (JSON.stringify(currentVal) !== JSON.stringify(defaultVal)) {
      diff[key] = currentVal
    }
  }
  return diff
}

// ---------------------------------------------------------------------------
// Serialize / deserialize
// ---------------------------------------------------------------------------

export function serializeShareableState(): string {
  const current = collectState()
  const diff = diffState(current)
  const json = JSON.stringify(diff)
  const compressed = pako.deflateRaw(new TextEncoder().encode(json))
  return toBase64Url(compressed)
}

export function deserializeShareLink(encoded: string): Partial<ShareState> {
  try {
    let json: string
    try {
      // New format: deflated + base64url
      const bytes = fromBase64Url(encoded)
      json = new TextDecoder().decode(pako.inflateRaw(bytes))
    } catch {
      // Backwards compat: old plain base64 format
      json = atob(encoded)
    }
    const parsed = JSON.parse(json) as Record<string, unknown>
    // Only keep known keys to avoid injecting arbitrary store state
    const result: Record<string, unknown> = {}
    for (const key of Object.keys(SHARE_DEFAULTS)) {
      if (key in parsed) {
        result[key] = parsed[key]
      }
    }
    // Back-compat passthrough: legacy links serialized a top-level `diffraction`
    // bool before the model selector existed. It is NOT a primary serialized
    // field (new links use diffractionModel), but it must survive decoding so
    // the apply path can honour an old link's explicit on/off choice.
    if (typeof parsed.diffraction === 'boolean') {
      result.diffraction = parsed.diffraction
    }
    return result as Partial<ShareState>
  } catch {
    console.warn('Failed to parse share link')
    return {}
  }
}

// ---------------------------------------------------------------------------
// Apply / generate
// ---------------------------------------------------------------------------

type SimStore = ReturnType<typeof useSimulationStore.getState>
type SceneStore = ReturnType<typeof useSceneStore.getState>
type UIStore = ReturnType<typeof useUIStore.getState>

function applySimulationState(state: Partial<ShareState>, sim: SimStore): void {
  if (state.antennaPos !== undefined) sim.setAntennaPos(state.antennaPos)
  if (state.mode !== undefined) sim.setMode(state.mode as Parameters<typeof sim.setMode>[0])
  if (state.fresnel !== undefined) sim.setFresnel(state.fresnel)
  if (state.polarisation !== undefined) sim.setPolarisation(state.polarisation)
  if (state.curvature !== undefined) sim.setCurvature(state.curvature)
  if (state.diffractionModel !== undefined) {
    sim.setDiffractionModel(state.diffractionModel as Parameters<typeof sim.setDiffractionModel>[0])
  } else {
    // Back-compat: an old link with no model but an explicit legacy bool. A new
    // link's model always wins (handled by the branch above).
    const legacyDiffraction = (state as { diffraction?: boolean }).diffraction
    if (legacyDiffraction !== undefined) {
      sim.setDiffractionModel(legacyDiffraction ? 'fock' : 'none')
    }
  }
  if (state.interBody !== undefined) {
    sim.setInterBody(state.interBody as Parameters<typeof sim.setInterBody>[0])
  }
  if (state.powerDbm !== undefined) sim.setPowerDbm(state.powerDbm)
  if (state.skinModel !== undefined) sim.setSkinModel(state.skinModel)
  if (state.freqGhz !== undefined) sim.setFreqGhz(state.freqGhz)
  if (state.exposureMode !== undefined) sim.setExposureMode(state.exposureMode as Parameters<typeof sim.setExposureMode>[0])
  if (state.stochasticPreset !== undefined) sim.setStochasticPreset(state.stochasticPreset)
  if (state.stochasticSeed !== undefined) sim.setStochasticSeed(state.stochasticSeed)
  if (state.stochasticOverrides !== undefined) sim.setStochasticOverrides(state.stochasticOverrides)
  if (state.bodyOffset !== undefined) sim.setBodyOffset(state.bodyOffset)
  if (state.bodyRotationY !== undefined) sim.setBodyRotationY(state.bodyRotationY)
  // enabledQuantities comes as array from JSON; convert back to Set
  if (state.enabledQuantities !== undefined) {
    sim.setEnabledQuantities(new Set(state.enabledQuantities as QuantityKey[]))
  }
  if (state.displayQuantity !== undefined) sim.setDisplayQuantity(state.displayQuantity as QuantityKey)
}

function applySceneState(state: Partial<ShareState>, scene: SceneStore): void {
  if (state.bodyName !== undefined) scene.setBodyName(state.bodyName)
  if (state.pathSource !== undefined) scene.setPathSource(state.pathSource as Parameters<typeof scene.setPathSource>[0])
  if (state.rtSource !== undefined) {
    const mapped = state.rtSource === 'voxel' ? 'sionna' : state.rtSource
    scene.setRtSource(mapped as Parameters<typeof scene.setRtSource>[0])
  }
  if (state.rtMaxOrder !== undefined) scene.setRtMaxOrder(state.rtMaxOrder)
  if (state.rtConfig !== undefined) scene.setRtConfig(state.rtConfig as Parameters<typeof scene.setRtConfig>[0])
  if (state.envDisplayMode !== undefined) scene.setEnvDisplayMode(state.envDisplayMode as Parameters<typeof scene.setEnvDisplayMode>[0])
  // display config
  if (state.colormapName !== undefined) scene.setColormapName(state.colormapName)
  if (state.sunIntensity !== undefined) scene.setSunIntensity(state.sunIntensity)
  if (state.ambientIntensity !== undefined) scene.setAmbientIntensity(state.ambientIntensity)
  if (state.cameraFov !== undefined) scene.setCameraFov(state.cameraFov)
  // scene visibility
  if (state.bodyMeshVisible !== undefined) scene.setBodyMeshVisible(state.bodyMeshVisible)
  if (state.groundPlaneVisible !== undefined) scene.setGroundPlaneVisible(state.groundPlaneVisible)
  if (state.gridVisible !== undefined) scene.setGridVisible(state.gridVisible)
  if (state.sceneGeometryVisible !== undefined) scene.setSceneGeometryVisible(state.sceneGeometryVisible)
}

function applyUIState(state: Partial<ShareState>, ui: UIStore): void {
  // camera override (applied by CameraController on mount)
  if (state.cameraPosition !== undefined && state.cameraTarget !== undefined) {
    ui.setCameraOverride({
      position: state.cameraPosition as [number, number, number],
      target: state.cameraTarget as [number, number, number],
    })
  }
  if (state.dynamicRangeDb !== undefined) ui.setDynamicRangeDb(state.dynamicRangeDb)
  if (state.ratioMode !== undefined) ui.setRatioMode(state.ratioMode)
  if (state.exposureScenario !== undefined) {
    ui.setExposureScenario(state.exposureScenario as Parameters<typeof ui.setExposureScenario>[0])
  }
  // wireframe uses toggleWireframe only; apply only if it differs from current
  if (state.wireframe !== undefined && state.wireframe !== ui.wireframe) {
    ui.toggleWireframe()
  }
  // legendScale uses toggleLegendScale only; apply only if it differs from current
  if (state.legendScale !== undefined && state.legendScale !== ui.legendScale) {
    ui.toggleLegendScale()
  }
}

function applyAntennaState(state: Partial<ShareState>): void {
  if (state.antennas === undefined || state.antennas.length === 0) return
  const antStore = useAntennaStore.getState()
  // Clear existing antennas
  for (const id of [...antStore.antennas.keys()]) {
    antStore.removeAntenna(id)
  }
  // Restore each antenna from share state
  for (const a of state.antennas) {
    const id = antStore.addAntenna(a.position)
    antStore.updateAntenna(id, {
      name: a.name,
      height: a.height,
      focusPoint: a.focusPoint,
      powerDbm: a.powerDbm,
      arrayConfig: {
        ...a.arrayConfig,
        element_pattern: a.arrayConfig.element_pattern as ElementPattern,
      },
      enabled: a.enabled,
    })
  }
  // Restore selection by mapping old IDs to new IDs by position in the array
  if (state.selectedAntennaId !== undefined) {
    const newIds = [...useAntennaStore.getState().antennas.keys()]
    const oldIdx = state.antennas.findIndex(a => a.id === state.selectedAntennaId)
    if (oldIdx >= 0 && oldIdx < newIds.length) {
      antStore.selectAntenna(newIds[oldIdx])
    }
  }
}

const VALID_ENV_SOURCES = new Set<EnvironmentSource>([
  'none', 'voxels', 'osm', '3dtiles', 'cesium', 'coverage',
])

function applyEnvironmentState(state: Partial<ShareState>): void {
  if (state.envSource === undefined) return
  const env = useEnvironmentStore.getState()
  const source = state.envSource as EnvironmentSource
  if (!VALID_ENV_SOURCES.has(source)) return

  env.setSource(source)
  if (state.envLat != null && state.envLon != null) {
    env.setLocation(state.envLat, state.envLon)
  }
  if (state.envLocationQuery !== undefined) env.setLocationQuery(state.envLocationQuery)
  if (state.envLocationFormatted !== undefined) env.setLocationFormatted(state.envLocationFormatted)
  if (state.envRadius !== undefined) env.setRadius(state.envRadius)
  if (state.envGeometricError !== undefined) env.setGeometricError(state.envGeometricError)
  if (state.envOsmOptions !== undefined) env.setOsmOptions(state.envOsmOptions)

  // Fire-and-forget the mesh fetch so the scene shows buildings/tiles after
  // hydration. Errors surface via the environment store's error state and toast.
  if (state.envLat != null && state.envLon != null) {
    if (source === 'osm') void env.fetchOSM()
    else if (source === '3dtiles') void env.fetchTilesForRT()
  }
}

export function applyShareState(state: Partial<ShareState>): void {
  applyEnvironmentState(state)
  applySimulationState(state, useSimulationStore.getState())
  applySceneState(state, useSceneStore.getState())
  applyUIState(state, useUIStore.getState())
  applyAntennaState(state)
}

export function generateShareUrl(): string {
  const encoded = serializeShareableState()
  return `${window.location.origin}/#s=${encoded}`
}
