import type { ComponentType } from 'react'
import {
  Map,
  MapPin,
  Building2,
  RadioTower,
  Layers,
  Radio,
  SlidersHorizontal,
  Antenna,
  Grid3X3,
  Target,
  Activity,
  PersonStanding,
  Dice5,
  Microscope,
  BarChart3,
  ChartLine,
  TrendingUp,
  Download,
  Film,
} from 'lucide-react'
import { RayTracingIcon } from '@/components/icons/RayTracingIcon'

import ParametersPanel from '@/components/panels/ParametersPanel'
import AnalysisPanel from '@/components/panels/analysis'
import EnvironmentPanel from '@/components/panels/environment'
import ScenePanel from '@/components/panels/ScenePanel'
import MIMOPanel from '@/components/hud/MIMOPanel'
import OptimizePanel from '@/components/panels/OptimizePanel'
import BaseStationsPanel from '@/components/panels/BaseStationsPanel'
import AntennaPanel from '@/components/panels/AntennaPanel'
import AntennasPanel from '@/components/panels/antennas'
import PhantomPanel from '@/components/panels/PhantomPanel'
import LayersPanel from '@/components/panels/LayersPanel'
import RayTracingPanel from '@/components/panels/rayTracing'
import StochasticPanel from '@/components/panels/StochasticPanel'
import TissuePanel from '@/components/panels/TissuePanel'
import PatternBrowserPanel from '@/components/panels/PatternBrowserPanel'
import ExportPanel from '@/components/panels/ExportPanel'
import ReplayPanel from '@/components/panels/ReplayPanel'

export type GroupId = 'world' | 'source' | 'exposure' | 'analysis'

export interface SectionDef {
  value: string
  label: string
  icon: ComponentType<{ className?: string }>
  component: ComponentType
  conditionalOn?: (ctx: { mimoEnabled: boolean }) => boolean
}

export interface GroupDef {
  id: GroupId
  label: string
  icon: ComponentType<{ className?: string }>
  sections: SectionDef[]
}

export const SIDEBAR_GROUPS: GroupDef[] = [
  {
    id: 'world',
    label: 'World',
    icon: Map,
    sections: [
      { value: 'scene', label: 'Scene', icon: MapPin, component: ScenePanel },
      { value: 'environment', label: 'Environment', icon: Building2, component: EnvironmentPanel },
      { value: 'basestations', label: 'Base Stations', icon: RadioTower, component: BaseStationsPanel },
      { value: 'layers', label: 'Layers', icon: Layers, component: LayersPanel },
    ],
  },
  {
    id: 'source',
    label: 'Source',
    icon: Radio,
    sections: [
      { value: 'parameters', label: 'Parameters', icon: SlidersHorizontal, component: ParametersPanel },
      { value: 'antennas', label: 'Antennas', icon: Antenna, component: AntennasPanel },
      { value: 'antenna', label: 'Antenna', icon: Grid3X3, component: AntennaPanel, conditionalOn: (ctx) => ctx.mimoEnabled },
      { value: 'mimo', label: 'MIMO', icon: Grid3X3, component: MIMOPanel },
      { value: 'patterns', label: 'Antenna Patterns', icon: Target, component: PatternBrowserPanel },
    ],
  },
  {
    id: 'exposure',
    label: 'Exposure',
    icon: Activity,
    sections: [
      { value: 'phantom', label: 'Phantom', icon: PersonStanding, component: PhantomPanel },
      { value: 'raytracing', label: 'Ray Tracing', icon: RayTracingIcon, component: RayTracingPanel },
      { value: 'stochastic', label: 'Stochastic', icon: Dice5, component: StochasticPanel },
      { value: 'tissue', label: 'Tissue', icon: Microscope, component: TissuePanel },
    ],
  },
  {
    id: 'analysis',
    label: 'Analysis',
    icon: BarChart3,
    sections: [
      { value: 'analysis', label: 'Analysis', icon: ChartLine, component: AnalysisPanel },
      { value: 'optimize', label: 'Optimize', icon: TrendingUp, component: OptimizePanel },
      { value: 'replay', label: 'Replay', icon: Film, component: ReplayPanel },
      { value: 'export', label: 'Export', icon: Download, component: ExportPanel },
    ],
  },
]

export const GROUP_IDS = SIDEBAR_GROUPS.map(g => g.id)
