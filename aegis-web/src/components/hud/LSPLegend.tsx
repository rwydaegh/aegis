import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useEnvironmentStore } from '@/stores/environment'
import { VIRIDIS_GRADIENT_CSS } from '@/lib/colormap'
import { getLSPMeta } from '@/lib/lsp-labels'
import Tex from '@/components/ui/Tex'
import GradientBar from '@/components/hud/GradientBar'

function formatTickValue(value: number): string {
  if (value === 0) return '0'
  const abs = Math.abs(value)
  if (abs >= 100) return value.toFixed(0)
  if (abs >= 1) return value.toFixed(1)
  if (abs >= 0.01) return value.toFixed(3)
  return value.toExponential(1)
}

export default function LSPLegend() {
  const pathSource = useSceneStore(s => s.pathSource)
  const envSource = useEnvironmentStore(s => s.source)
  const visible = useSimulationStore(s => s.lspHeatmapVisible)
  const param = useSimulationStore(s => s.lspHeatmapParam)
  const data = useSimulationStore(s => s.lspHeatmapData)
  const range = useSimulationStore(s => s.lspHeatmapRange)
  const lspHeatmapLoading = useSimulationStore(s => s.lspHeatmapLoading)

  if (pathSource !== 'stochastic' || envSource !== 'none' || !visible || !data) return null

  const [vmin, vmax] = range
  const meta = getLSPMeta(param)

  const N = 5
  const ticks = Array.from({ length: N }, (_, i) => {
    const frac = i / (N - 1)
    const value = vmax - frac * (vmax - vmin)
    return { label: formatTickValue(value), pct: frac }
  })

  const titleNode = (
    <span className="text-xs font-medium text-foreground">
      <Tex math={meta.latex} />
    </span>
  )

  return (
    <GradientBar
      gradient={VIRIDIS_GRADIENT_CSS}
      ticks={ticks}
      title={titleNode}
      shimmer={lspHeatmapLoading}
    />
  )
}
