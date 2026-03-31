import { useActiveSimulation } from '../../hooks/useActiveSimulation';

export function AnalysisEmptyState() {
  const { stats } = useActiveSimulation();

  if (stats != null) return null;

  return (
    <div className="text-xs text-zinc-500 py-2">
      Place an antenna and compute dosimetry to see results
    </div>
  );
}
