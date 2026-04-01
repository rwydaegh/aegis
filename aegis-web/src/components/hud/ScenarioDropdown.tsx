import { useState, useRef, useEffect, useCallback } from 'react';
import { Layers, Check, Loader2, Radio } from 'lucide-react';
import { useUIStore } from '../../stores/ui';
import { useSimulationStore } from '../../stores/simulation';
import { useScenario } from '../../hooks/useScenario';

const CLOUDRF_PRESETS = [
  { key: 'cloudrf_5g_cband', label: '5G C-Band macro (3.5 GHz)', freqGhz: 3.5, powerDbm: 42.0 },
  { key: 'cloudrf_lte_b3', label: 'LTE eNodeB B3 (1.8 GHz)', freqGhz: 1.8, powerDbm: 29.0 },
  { key: 'cloudrf_lora', label: 'LoRa EU gateway (868 MHz)', freqGhz: 0.868, powerDbm: 19.9 },
  { key: 'cloudrf_wifi', label: 'WiFi 2.4 GHz AP', freqGhz: 2.4, powerDbm: 25.0 },
  { key: 'cloudrf_pmr446', label: 'PMR446 handheld', freqGhz: 0.446, powerDbm: 27.0 },
] as const;

export function ScenarioDropdown() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const activeScenario = useUIStore((s) => s.activeScenario);
  const scenarioLoading = useUIStore((s) => s.scenarioLoading);
  const { visibleScenarios, hiddenScenarios, loadScenario } = useScenario();

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const handleSelect = (key: string) => {
    setOpen(false);
    void loadScenario(key);
  };

  const handleCloudRFPreset = useCallback((preset: typeof CLOUDRF_PRESETS[number]) => {
    setOpen(false);
    const sim = useSimulationStore.getState();
    sim.setFreqGhz(preset.freqGhz);
    sim.setPowerDbm(preset.powerDbm);
    useUIStore.getState().setActiveScenario(preset.key);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-0.5 text-xs font-medium text-primary hover:bg-primary/20 transition-colors shrink-0"
      >
        {scenarioLoading ? (
          <Loader2 size={12} className="animate-spin" />
        ) : (
          <Layers size={12} />
        )}
        Scenarios
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 w-64 rounded-lg bg-card border border-border shadow-xl z-50 py-1">
          {visibleScenarios.map(([key, s]) => (
            <button
              key={key}
              onClick={() => handleSelect(key)}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted text-left transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm text-foreground">{s.label}</div>
                {s.description && (
                  <div className="text-xs text-muted-foreground truncate">{s.description}</div>
                )}
              </div>
              {activeScenario === key && (
                <Check size={14} className="text-primary shrink-0" />
              )}
            </button>
          ))}

          {hiddenScenarios.length > 0 && (
            <>
              <div className="border-t border-border my-1" />
              {hiddenScenarios.map(([key, s]) => (
                <button
                  key={key}
                  onClick={() => handleSelect(key)}
                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted text-left transition-colors"
                >
                  <div className="text-sm text-muted-foreground">{s.label}</div>
                  {activeScenario === key && (
                    <Check size={14} className="text-primary shrink-0 ml-auto" />
                  )}
                </button>
              ))}
            </>
          )}

          <div className="border-t border-border my-1" />
          <div className="px-3 py-1.5 flex items-center gap-1.5">
            <Radio size={12} className="text-muted-foreground" />
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Real-world radios</span>
          </div>
          {CLOUDRF_PRESETS.map(preset => (
            <button
              key={preset.key}
              onClick={() => handleCloudRFPreset(preset)}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted text-left transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm text-foreground">{preset.label}</div>
              </div>
              {activeScenario === preset.key && (
                <Check size={14} className="text-primary shrink-0" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
