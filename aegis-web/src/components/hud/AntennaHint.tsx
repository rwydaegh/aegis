import { useSimulationStore } from '../../stores/simulation';
import { useMIMOStore } from '../../stores/mimo';
import { useUIStore } from '../../stores/ui';

export function AntennaHint() {
  const antennaPos = useSimulationStore((s) => s.antennaPos);
  const mimoEnabled = useMIMOStore((s) => s.enabled);
  const welcomeDismissed = useUIStore((s) => s.welcomeDismissed);

  if (!welcomeDismissed || antennaPos != null || mimoEnabled) return null;

  return (
    <div className="absolute bottom-8 left-1/2 -translate-x-1/2 pointer-events-none z-10">
      <div className="px-4 py-2 rounded-full bg-zinc-800/80 border border-zinc-700
        text-xs text-zinc-400 backdrop-blur-sm">
        Click the scene to place an antenna
      </div>
    </div>
  );
}
