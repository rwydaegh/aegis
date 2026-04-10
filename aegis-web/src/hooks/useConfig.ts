import { useState, useEffect } from 'react'
import * as Sentry from '@sentry/react'
import { fetchViewerConfig, fetchCapabilities } from '@/api/client'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useEnvironmentStore } from '@/stores/environment'
import type { ScenePos } from '@/api/coordinates'

type ConfigStatus = 'loading' | 'ready' | 'error'

export function useConfig() {
  const [status, setStatus] = useState<ConfigStatus>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchViewerConfig(), fetchCapabilities()])
      .then(([config, caps]) => {
        const initialBody = caps.body_name ?? caps.bodies?.[0] ?? ''
        const gltfSet = new Set(caps.gltf_bodies ?? [])
        useSceneStore.setState({
          viewerConfig: config,
          capabilities: caps,
          bodyName: initialBody,
          phantomType: gltfSet.has(initialBody) ? 'gltf' : 'stl',
        })

        const simState: Record<string, unknown> = {
          mode: 'spatial',
          fresnel: true,
          powerDbm: 60,
          skinModel: 'itis',
        }

        // Auto-place body at the recommended position (if location was loaded)
        // body_placement is already in Y-up (scene) coordinates
        if (caps.body_placement) {
          simState.bodyOffset = caps.body_placement as ScenePos
        }

        useSimulationStore.setState(simState)

        // Wire config keys from DEFAULTS that are not already wired above
        const sim = useSimulationStore.getState()
        const scene = useSceneStore.getState()
        const ui = useUIStore.getState()
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const cfg = config as any

        if (cfg.dosimetry?.freq_hz) {
          sim.setFreqGhz(cfg.dosimetry.freq_hz / 1e9)
        }
        if (cfg.dosimetry?.default_power_dbm !== undefined) {
          sim.setPowerDbm(cfg.dosimetry.default_power_dbm)
        }
        if (cfg.dosimetry?.exposure_scenario) {
          const scenario = cfg.dosimetry.exposure_scenario
          if (scenario === 'general_public' || scenario === 'occupational') {
            ui.setExposureScenario(scenario)
          }
        }

        // Round-trip config keys for export/reload
        if (cfg.antenna?.default_position) {
          sim.setAntennaPos(cfg.antenna.default_position)
        }
        if (cfg.dosimetry?.skin_model) {
          sim.setSkinModel(cfg.dosimetry.skin_model)
        }
        if (cfg.dosimetry?.dynamic_range_db !== undefined) {
          ui.setDynamicRangeDb(cfg.dosimetry.dynamic_range_db)
        }
        if (cfg.dosimetry?.default_max_order !== undefined) {
          scene.setRtMaxOrder(cfg.dosimetry.default_max_order)
        }
        if (cfg.body?.default_offset) {
          sim.setBodyOffset(cfg.body.default_offset)
        }
        if (cfg.body?.default_rotation_y !== undefined) {
          sim.setBodyRotationY(cfg.body.default_rotation_y)
        }
        if (cfg.body?.wireframe === true && !ui.wireframe) {
          ui.toggleWireframe()
        }
        if (cfg.raytracer?.default_source) {
          scene.setRtSource(cfg.raytracer.default_source)
        }

        // Display config
        if (cfg.colormap?.name) scene.setColormapName(cfg.colormap.name)
        if (cfg.lighting?.sun?.intensity !== undefined) scene.setSunIntensity(cfg.lighting.sun.intensity)
        if (cfg.lighting?.ambient?.intensity !== undefined) scene.setAmbientIntensity(cfg.lighting.ambient.intensity)
        if (cfg.camera?.fov !== undefined) scene.setCameraFov(cfg.camera.fov)

        // Hydrate environment store from config
        if (cfg.environment) {
          const env = cfg.environment
          const osmCfg = env.osm
          const tilesCfg = env.tiles
          useEnvironmentStore.setState({
            source: (env.source || 'none') as 'none' | 'voxels' | 'osm' | '3dtiles',
            location: env.location || null,
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


        // Load available scenes (server returns {name, path} objects)
        if (caps.scenes?.length > 0) {
          const scenes = caps.scenes.map((s) =>
            typeof s === 'string' ? { name: s.split(/[/\\]/).pop()?.replace('.xml', '') ?? s, path: s } : { name: s.name, path: s.path }
          )
          useSceneStore.setState({ scenes })
        }

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
