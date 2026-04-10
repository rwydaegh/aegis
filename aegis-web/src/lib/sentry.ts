import * as Sentry from '@sentry/react'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useSceneStore } from '@/stores/scene'
import { useMIMOStore } from '@/stores/mimo'

export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined
  if (!dsn) return

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    // Only send errors, no performance/session tracking
    tracesSampleRate: 0,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,

    ignoreErrors: [
      // WebGL context failures are environmental (user GPU/browser), not actionable
      /Error creating WebGL context/,
      /WebGL context could not be created/,
    ],

    beforeSend(event) {
      // Attach full simulation state as context on every error
      try {
        const sim = useSimulationStore.getState()
        const ui = useUIStore.getState()
        const scene = useSceneStore.getState()
        const mimo = useMIMOStore.getState()

        event.contexts = {
          ...event.contexts,
          simulation: {
            mode: sim.mode,
            freqGhz: sim.freqGhz,
            powerDbm: sim.powerDbm,
            fresnel: sim.fresnel,
            polarisation: sim.polarisation,
            curvature: sim.curvature,
            diffraction: sim.diffraction,
            skinModel: sim.skinModel,
            antennaPos: sim.antennaPos,
            bodyOffset: sim.bodyOffset,
            bodyRotationY: sim.bodyRotationY,
            stochasticSeed: sim.stochasticSeed,
          },
          ui: {
            sidebarMode: ui.sidebarMode,
            cameraMode: ui.cameraMode,
            legendScale: ui.legendScale,
            wireframe: ui.wireframe,
            ratioMode: ui.ratioMode,
            exposureScenario: ui.exposureScenario,
          },
          scene: {
            activeScenario: scene.viewerConfig?.active_scenario ?? null,
            pathSource: scene.pathSource,
          },
          mimo: {
            enabled: mimo.enabled,
            precoderType: mimo.precoderType,
            userCount: mimo.users.size,
            focusedUserId: mimo.focusedUserId,
          },
        }
      } catch {
        // If store access fails, still send the error
      }
      return event
    },
  })
}
