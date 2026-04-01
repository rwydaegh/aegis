import pako from 'pako'
import { SHARE_DEFAULTS, type ShareState } from './shareDefaults'
import { useSimulationStore } from '../stores/simulation'
import { useSceneStore } from '../stores/scene'
import { useUIStore } from '../stores/ui'
import type { QuantityKey } from '../stores/ui'

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

  return {
    // simulation store
    antennaPos: sim.antennaPos,
    mode: sim.mode,
    fresnel: sim.fresnel,
    polarisation: sim.polarisation,
    curvature: sim.curvature,
    diffraction: sim.diffraction,
    powerDbm: sim.powerDbm,
    skinModel: sim.skinModel,
    freqGhz: sim.freqGhz,
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
    // ui store
    wireframe: ui.wireframe,
    legendScale: ui.legendScale,
    dynamicRangeDb: ui.dynamicRangeDb,
    ratioMode: ui.ratioMode,
    exposureScenario: ui.exposureScenario,
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
    return result as Partial<ShareState>
  } catch {
    console.warn('Failed to parse share link')
    return {}
  }
}

// ---------------------------------------------------------------------------
// Apply / generate
// ---------------------------------------------------------------------------

export function applyShareState(state: Partial<ShareState>): void {
  const sim = useSimulationStore.getState()
  const scene = useSceneStore.getState()
  const ui = useUIStore.getState()

  // --- simulation store ---
  if (state.antennaPos !== undefined) sim.setAntennaPos(state.antennaPos)
  if (state.mode !== undefined) sim.setMode(state.mode as Parameters<typeof sim.setMode>[0])
  if (state.fresnel !== undefined) sim.setFresnel(state.fresnel)
  if (state.polarisation !== undefined) sim.setPolarisation(state.polarisation)
  if (state.curvature !== undefined) sim.setCurvature(state.curvature)
  if (state.diffraction !== undefined) sim.setDiffraction(state.diffraction)
  if (state.powerDbm !== undefined) sim.setPowerDbm(state.powerDbm)
  if (state.skinModel !== undefined) sim.setSkinModel(state.skinModel)
  if (state.freqGhz !== undefined) sim.setFreqGhz(state.freqGhz)
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

  // --- scene store ---
  if (state.bodyName !== undefined) scene.setBodyName(state.bodyName)
  if (state.pathSource !== undefined) scene.setPathSource(state.pathSource as Parameters<typeof scene.setPathSource>[0])
  if (state.rtSource !== undefined) scene.setRtSource(state.rtSource as Parameters<typeof scene.setRtSource>[0])
  if (state.rtMaxOrder !== undefined) scene.setRtMaxOrder(state.rtMaxOrder)
  if (state.rtConfig !== undefined) scene.setRtConfig(state.rtConfig as Parameters<typeof scene.setRtConfig>[0])
  if (state.envDisplayMode !== undefined) scene.setEnvDisplayMode(state.envDisplayMode as Parameters<typeof scene.setEnvDisplayMode>[0])
  // display config
  if (state.colormapName !== undefined) scene.setColormapName(state.colormapName)
  if (state.sunIntensity !== undefined) scene.setSunIntensity(state.sunIntensity)
  if (state.ambientIntensity !== undefined) scene.setAmbientIntensity(state.ambientIntensity)
  if (state.cameraFov !== undefined) scene.setCameraFov(state.cameraFov)

  // --- ui store ---
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

export function generateShareUrl(): string {
  const encoded = serializeShareableState()
  return `${window.location.origin}/#s=${encoded}`
}
