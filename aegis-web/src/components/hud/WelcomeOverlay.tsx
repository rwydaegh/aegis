import { useEffect } from 'react';
import { Radio, Zap, Building2, Globe } from 'lucide-react';
import { useSimulationStore } from '../../stores/simulation';
import { useUIStore } from '../../stores/ui';
import { useScenario } from '../../hooks/useScenario';

const ICON_MAP: Record<string, React.FC<{ size?: number; className?: string }>> = {
  radio: Radio,
  zap: Zap,
  building: Building2,
  globe: Globe,
};

export function WelcomeOverlay() {
  const antennaPos = useSimulationStore((s) => s.antennaPos);
  const welcomeDismissed = useUIStore((s) => s.welcomeDismissed);
  const setWelcomeDismissed = useUIStore((s) => s.setWelcomeDismissed);
  const { visibleScenarios, loadScenario } = useScenario();

  const hasScenarioParam = new URLSearchParams(window.location.search).has('scenario');
  const hasShareLink = window.location.hash.startsWith('#s=');

  const shouldShow =
    antennaPos == null &&
    !welcomeDismissed &&
    !hasScenarioParam &&
    !hasShareLink;

  // Dismiss on Escape - MUST be before conditional return (React hooks rules)
  useEffect(() => {
    if (!shouldShow) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setWelcomeDismissed(true);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [shouldShow, setWelcomeDismissed]);

  if (!shouldShow) return null;

  return (
    <div
      className="absolute inset-0 z-20 flex items-center justify-center pointer-events-auto"
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.7)' }}
      onClick={() => setWelcomeDismissed(true)}
    >
      <div
        className="flex flex-col items-center gap-6 max-w-2xl px-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white tracking-tight">
            AEGIS
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Absorbed power density on human bodies
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 w-full">
          {visibleScenarios.map(([key, scenario]) => {
            const Icon = ICON_MAP[scenario.icon];
            return (
              <button
                key={key}
                onClick={() => loadScenario(key)}
                className="flex flex-col items-start gap-2 p-4 rounded-lg
                  bg-zinc-800/80 border border-zinc-700 hover:border-zinc-500
                  transition-colors text-left"
              >
                {Icon && <Icon size={20} className="text-zinc-400" />}
                <div>
                  <div className="text-sm font-medium text-white">
                    {scenario.label}
                  </div>
                  <div className="text-xs text-zinc-400">
                    {scenario.description}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <button
          onClick={() => setWelcomeDismissed(true)}
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          or start with an empty scene
        </button>
      </div>
    </div>
  );
}
