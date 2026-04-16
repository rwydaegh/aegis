import { useEnvironmentStore } from '@/stores/environment'
import { useCoverageStore } from '@/stores/coverage'
import { useUIStore } from '@/stores/ui'
import { SOURCE_OPTIONS, labelClass } from './constants'

export function SourceSelector() {
  const source = useEnvironmentStore((s) => s.source)
  const setSource = useEnvironmentStore((s) => s.setSource)
  const setCameraMode = useUIStore((s) => s.setCameraMode)
  const setCameraPreset = useUIStore((s) => s.setCameraPreset)

  return (
    <div>
      <label className={labelClass}>Source</label>
      <div className="grid grid-cols-5 gap-1">
        {SOURCE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => {
              const prev = source
              setSource(opt.value)
              if (opt.value === 'coverage') {
                const cov = useCoverageStore.getState()
                cov.setEnabled(true)
                cov.fetch()
              } else {
                if (prev === 'coverage') {
                  useCoverageStore.getState().setEnabled(false)
                  setCameraMode('orbit')
                  setCameraPreset('reset')
                }
              }
            }}
            className={`px-2 py-1.5 rounded text-xs font-medium transition-colors ${
              source === opt.value
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:text-foreground'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  )
}
