import { useState, useEffect } from 'react'
import * as Sentry from '@sentry/react'
import { fetchViewerConfig, fetchCapabilities } from '@/api/client'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useEnvironmentStore } from '@/stores/environment'
import type { ScenePos } from '@/api/coordinates'
import type { ViewerConfig, Capabilities } from '@/api/types'

type ConfigStatus = 'loading' | 'ready' | 'error'

// Scene + body selection derived from capabilities.
function applySceneAndBody(config: ViewerConfig, caps: Capabilities) {
  const initialBody = caps.body_name ?? caps.bodies?.[0] ?? ''
  const gltfSet = new Set(caps.gltf_bodies ?? [])
  useSceneStore.setState({
    viewerConfig: config,
    capabilities: caps,
    bodyName: initialBody,
    phantomType: gltfSet.has(initialBody) ? 'gltf' : 'stl',
  })
}

// Baseline simulation state (mode/fresnel/power/skinModel) plus optional body placement.
function applyInitialSimulation(_config: ViewerConfig, caps: Capabilities) {
  const simState: Record<string, unknown> = {
    mode: 'spatial',
    fresnel: true,
    powerDbm: 43,
    skinModel: 'itis',
  }
  // Auto-place body at the recommended position (if location was loaded).
  // body_placement is already in Y-up (scene) coordinates.
  if (caps.body_placement) {
    simState.bodyOffset = caps.body_placement as ScenePos
  }
  useSimulationStore.setState(simState)
}

// Wire dosimetry/antenna/body keys from the config payload.
function applyDosimetryConfig(config: ViewerConfig, caps: Capabilities) {
  const sim = useSimulationStore.getState()
  const scene = useSceneStore.getState()
  const ui = useUIStore.getState()

  if (config.dosimetry?.freq_hz) {
    sim.setFreqGhz(config.dosimetry.freq_hz / 1e9)
  }
  if (config.dosimetry?.default_power_dbm !== undefined) {
    sim.setPowerDbm(config.dosimetry.default_power_dbm)
  }
  if (config.dosimetry?.exposure_scenario) {
    const scenario = config.dosimetry.exposure_scenario
    if (scenario === 'general_public' || scenario === 'occupational') {
      ui.setExposureScenario(scenario)
    }
  }

  // Round-trip config keys for export/reload
  if (config.antenna?.default_position) {
    sim.setAntennaPos(config.antenna.default_position)
  }
  if (config.dosimetry?.skin_model) {
    sim.setSkinModel(config.dosimetry.skin_model)
  }
  if (config.dosimetry?.dynamic_range_db !== undefined) {
    ui.setDynamicRangeDb(config.dosimetry.dynamic_range_db)
  }
  if (config.dosimetry?.default_max_order !== undefined) {
    scene.setRtMaxOrder(config.dosimetry.default_max_order)
  }
  if (config.body?.default_offset && !caps.body_placement) {
    sim.setBodyOffset(config.body.default_offset)
  }
  if (config.body?.default_rotation_y !== undefined) {
    sim.setBodyRotationY(config.body.default_rotation_y)
  }
  if (config.body?.wireframe === true && !ui.wireframe) {
    ui.toggleWireframe()
  }
  if (config.raytracer?.default_source) {
    const src = config.raytracer.default_source
    if (src === 'sionna' || src === 'differt') {
      scene.setRtSource(src)
    }
  }
}

// Colormap, lighting, camera.
function applyDisplayConfig(config: ViewerConfig) {
  const scene = useSceneStore.getState()
  if (config.colormap?.name) scene.setColormapName(config.colormap.name)
  if (config.lighting?.sun?.intensity !== undefined) scene.setSunIntensity(config.lighting.sun.intensity)
  if (config.lighting?.ambient?.intensity !== undefined) scene.setAmbientIntensity(config.lighting.ambient.intensity)
  if (config.camera?.fov !== undefined) scene.setCameraFov(config.camera.fov)
}

// Hydrate environment store from config.environment.
function applyEnvironmentConfig(config: ViewerConfig) {
  if (!config.environment) return
  const env = config.environment
  const osmCfg = env.osm
  const tilesCfg = env.tiles
  useEnvironmentStore.setState({
    source: (env.source || 'none') as 'none' | 'voxels' | 'osm' | '3dtiles',
    radius: env.radius || 200,
    geometricError: tilesCfg?.geometric_error || 30,
    osmOptions: {
      defaultBuildingHeight: osmCfg?.default_building_height || 10,
      levelHeight: osmCfg?.level_height || 3.0,
      buildings: osmCfg?.buildings ?? true,
      roads: osmCfg?.roads ?? true,
      water: osmCfg?.water ?? true,
      detail: osmCfg?.detail ?? false,
    },
  })
}

// Normalize available scenes list (server returns {name, path} objects or plain strings).
function applyScenesConfig(caps: Capabilities) {
  if (!caps.scenes?.length) return
  const scenes = caps.scenes.map((s) =>
    typeof s === 'string' ? { name: s.split(/[/\\]/).pop()?.replace('.xml', '') ?? s, path: s } : { name: s.name, path: s.path },
  )
  useSceneStore.setState({ scenes })
}

export function useConfig() {
  const [status, setStatus] = useState<ConfigStatus>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchViewerConfig(), fetchCapabilities()])
      .then(([config, caps]) => {
        applySceneAndBody(config, caps)
        applyInitialSimulation(config, caps)
        applyDosimetryConfig(config, caps)
        applyDisplayConfig(config)
        applyEnvironmentConfig(config)
        applyScenesConfig(caps)
        setStatus('ready')
      })
      .catch((err: unknown) => {
        Sentry.captureException(err)
        const message = err instanceof Error ? err.message : 'Unknown error'
        setError(message)
        setStatus('error')
      })
  }, [])

  return { status, error }
}
