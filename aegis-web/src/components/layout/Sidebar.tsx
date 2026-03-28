import { useState, useEffect } from 'react'
import { useUIStore } from '@/stores/ui'
import { useMIMOStore } from '@/stores/mimo'
import { useIsMobile } from '@/hooks/useIsMobile'
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '@/components/ui/accordion'
import ParametersPanel from '@/components/panels/ParametersPanel'
import PhantomPanel from '@/components/panels/PhantomPanel'
import LayersPanel from '@/components/panels/LayersPanel'
import ScenePanel from '@/components/panels/ScenePanel'
import RayTracingPanel from '@/components/panels/RayTracingPanel'
import StochasticPanel from '@/components/panels/StochasticPanel'
import TissuePanel from '@/components/panels/TissuePanel'
import ExportPanel from '@/components/panels/ExportPanel'
import AnalysisPanel from '@/components/panels/AnalysisPanel'
import AntennaPanel from '@/components/panels/AntennaPanel'
import MIMOPanel from '@/components/hud/MIMOPanel'
import BaseStationsPanel from '@/components/panels/BaseStationsPanel'

export default function Sidebar() {
  const { sidebarOpen } = useUIStore()
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const isMobile = useIsMobile()
  const openWidth = isMobile ? '100vw' : '320px'
  const [openSections, setOpenSections] = useState<string[]>(['parameters'])

  // Auto-open MIMO accordion when MIMO mode is toggled on
  useEffect(() => {
    if (mimoEnabled) {
      setOpenSections(prev => prev.includes('mimo') ? prev : [...prev, 'mimo'])
    } else {
      setOpenSections(prev => prev.filter(s => s !== 'mimo'))
    }
  }, [mimoEnabled])

  return (
    <aside
      className="absolute top-0 left-0 h-full z-20 flex flex-col
        bg-card/90 backdrop-blur-xl border-r border-border
        transition-all duration-200 ease-in-out overflow-hidden"
      style={{ width: sidebarOpen ? openWidth : '0px', visibility: sidebarOpen ? 'visible' : 'hidden' }}
      aria-hidden={!sidebarOpen}
      {...(!sidebarOpen && { inert: true as any })}
    >
      <div className={`${isMobile ? 'w-full' : 'w-[320px]'} h-full flex flex-col overflow-y-auto overflow-x-hidden`}>
        <div className="p-3 border-b border-border shrink-0">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Controls</p>
        </div>

        <div className="flex-1 overflow-y-auto">
          <Accordion multiple value={openSections} onValueChange={(v: string[]) => setOpenSections(v)}>
            <AccordionItem value="parameters" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">Parameters</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <ParametersPanel />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="analysis" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">Analysis</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <AnalysisPanel />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="scene" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">Scene</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <ScenePanel />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="mimo" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">MIMO</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <MIMOPanel />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="basestations" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">Base Stations</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <BaseStationsPanel />
                </div>
              </AccordionContent>
            </AccordionItem>

            {mimoEnabled && (
              <AccordionItem value="antenna" className="border-b border-border px-3">
                <AccordionTrigger className="text-sm font-medium py-3">Antenna</AccordionTrigger>
                <AccordionContent>
                  <div className="py-2">
                    <AntennaPanel />
                  </div>
                </AccordionContent>
              </AccordionItem>
            )}

            {!mimoEnabled && (
              <AccordionItem value="phantom" className="border-b border-border px-3">
                <AccordionTrigger className="text-sm font-medium py-3">Phantom</AccordionTrigger>
                <AccordionContent>
                  <div className="py-2">
                    <PhantomPanel />
                  </div>
                </AccordionContent>
              </AccordionItem>
            )}

            <AccordionItem value="layers" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">Layers</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <LayersPanel />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="raytracing" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">Ray Tracing</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <RayTracingPanel />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="stochastic" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">Stochastic</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <StochasticPanel />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="tissue" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">Tissue</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <TissuePanel />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="export" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">Export</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <ExportPanel />
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </div>
    </aside>
  )
}
