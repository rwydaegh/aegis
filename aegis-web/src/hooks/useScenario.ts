import { useCallback } from 'react';
import { useSimulationStore } from '../stores/simulation';
import { useSceneStore } from '../stores/scene';
import { useEnvironmentStore } from '../stores/environment';
import { useUIStore } from '../stores/ui';
import { useCoverageStore } from '../stores/coverage';
import type { ScenarioEntry } from '../api/types';

export function useScenario() {
  const viewerConfig = useSceneStore((s) => s.viewerConfig);

  const scenarios: Record<string, ScenarioEntry> = viewerConfig?.scenarios ?? {};

  const loadScenario = useCallback(
    async (name: string) => {
      const scenario = scenarios[name];
      if (!scenario) return;

      const { webState } = scenario;
      const sim = useSimulationStore.getState();
      const scene = useSceneStore.getState();
      const env = useEnvironmentStore.getState();
      const ui = useUIStore.getState();

      // 1. Reset - prevent stale data leaking between scenarios
      sim.clearResults();
      scene.clearScene();

      // 2. Apply instant state
      if (webState.freqGhz != null) sim.setFreqGhz(webState.freqGhz);
      if (webState.powerDbm != null) sim.setPowerDbm(webState.powerDbm);
      if (webState.mode != null) sim.setMode(webState.mode as any);
      if ('antennaPos' in webState) sim.setAntennaPos(webState.antennaPos ?? null);

      if (webState.environment) {
        env.setSource(webState.environment.source as any);
        if (webState.environment.lat != null && webState.environment.lon != null) {
          env.setLocation(webState.environment.lat, webState.environment.lon);
        }
        if (webState.environment.locationQuery) {
          env.setLocationFormatted(webState.environment.locationQuery);
        }
      }

      // 3. Coverage globe: enable overlay and fetch data
      if (name === 'coverage_globe') {
        useCoverageStore.getState().setEnabled(true)
        useCoverageStore.getState().fetch()
      } else {
        useCoverageStore.getState().setEnabled(false)
      }

      // 4. Set UI state
      ui.setActiveScenario(name);
      ui.setWelcomeDismissed(true);

      // 4. Trigger environment fetch if needed
      if (
        webState.environment &&
        webState.environment.source === 'osm' &&
        webState.environment.lat != null
      ) {
        ui.setScenarioLoading(true);
        try {
          await env.fetchOSM();
        } catch {
          // Toast handled inside fetchOSM; we just stop loading
        } finally {
          ui.setScenarioLoading(false);
        }
      }

      // 5. Auto-compute: NOT needed. useDosimetry has a reactive useEffect
      // that fires when antennaPos changes. Setting antennaPos above
      // triggers the debounced compute pipeline automatically.

      // 6. Update URL
      if (name === 'empty') {
        const url = new URL(window.location.href);
        url.searchParams.delete('scenario');
        history.replaceState(null, '', url.toString());
      } else {
        const url = new URL(window.location.href);
        url.searchParams.set('scenario', name);
        history.replaceState(null, '', url.toString());
      }
    },
    [scenarios],
  );

  const visibleScenarios = Object.entries(scenarios).filter(
    ([, s]) => !s.hidden,
  );
  const hiddenScenarios = Object.entries(scenarios).filter(
    ([, s]) => s.hidden,
  );

  return { scenarios, visibleScenarios, hiddenScenarios, loadScenario };
}
