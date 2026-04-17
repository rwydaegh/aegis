import { useCallback, useMemo } from 'react';
import { useSimulationStore, type DosimetryMode } from '../stores/simulation';
import { useSceneStore } from '../stores/scene';
import { useEnvironmentStore, type EnvironmentSource } from '../stores/environment';
import { useUIStore } from '../stores/ui';
import { useCoverageStore } from '../stores/coverage';
import type { ScenarioEntry } from '../api/types';

const VALID_MODES = new Set<DosimetryMode>(['bound', 'aggregate', 'spatial']);
const VALID_SOURCES = new Set<EnvironmentSource>(['none', 'voxels', 'osm', '3dtiles', 'cesium', 'coverage']);

type ScenarioWebState = ScenarioEntry['webState'];
type EnvSpec = NonNullable<ScenarioWebState['environment']>;

function applySimulationState(webState: ScenarioWebState): void {
  const sim = useSimulationStore.getState();
  if (webState.freqGhz != null) sim.setFreqGhz(webState.freqGhz);
  if (webState.powerDbm != null) sim.setPowerDbm(webState.powerDbm);
  if (webState.mode != null && VALID_MODES.has(webState.mode as DosimetryMode)) {
    sim.setMode(webState.mode as DosimetryMode);
  }
  if ('antennaPos' in webState) sim.setAntennaPos(webState.antennaPos ?? null);
}

function applyEnvironmentState(env: EnvSpec): void {
  const store = useEnvironmentStore.getState();
  if (VALID_SOURCES.has(env.source as EnvironmentSource)) {
    store.setSource(env.source as EnvironmentSource);
  }
  if (env.lat != null && env.lon != null) {
    store.setLocation(env.lat, env.lon);
  }
  if (env.locationQuery) {
    store.setLocationFormatted(env.locationQuery);
  }
}

function applyCoverageForScenario(name: string): void {
  const coverage = useCoverageStore.getState();
  if (name === 'coverage_globe') {
    coverage.setEnabled(true);
    coverage.fetch();
  } else {
    coverage.setEnabled(false);
  }
}

async function fetchEnvironmentIfNeeded(env: EnvSpec): Promise<void> {
  if (env.lat == null) return;
  if (env.source !== 'osm' && env.source !== '3dtiles') return;
  const ui = useUIStore.getState();
  const store = useEnvironmentStore.getState();
  ui.setScenarioLoading(true);
  try {
    if (env.source === 'osm') await store.fetchOSM();
    else await store.fetchTilesForRT();
  } catch {
    // Toast handled inside fetch*; we just stop loading
  } finally {
    ui.setScenarioLoading(false);
  }
}

function updateScenarioUrl(name: string): void {
  const url = new URL(window.location.href);
  if (name === 'empty') {
    url.searchParams.delete('scenario');
  } else {
    url.searchParams.set('scenario', name);
  }
  history.replaceState(null, '', url.toString());
}

export function useScenario() {
  const viewerConfig = useSceneStore((s) => s.viewerConfig);

  const scenarios: Record<string, ScenarioEntry> = useMemo(
    () => viewerConfig?.scenarios ?? {},
    [viewerConfig?.scenarios],
  );

  const loadScenario = useCallback(
    async (name: string) => {
      const scenario = scenarios[name];
      if (!scenario) return;

      const { webState } = scenario;

      // 1. Reset - prevent stale data leaking between scenarios
      useSimulationStore.getState().clearResults();
      useSceneStore.getState().clearScene();

      // 2. Apply instant state
      applySimulationState(webState);
      if (webState.environment) applyEnvironmentState(webState.environment);
      applyCoverageForScenario(name);

      // 3. UI state
      const ui = useUIStore.getState();
      ui.setActiveScenario(name);
      ui.setWelcomeDismissed(true);

      // 4. Environment fetch (OSM / 3dtiles)
      if (webState.environment) await fetchEnvironmentIfNeeded(webState.environment);

      // 5. Auto-compute handled by useDosimetry's reactive useEffect.

      // 6. URL
      updateScenarioUrl(name);
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
