import { useUIStore } from '@/stores/ui'
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

export default function Sidebar() {
  const { sidebarOpen } = useUIStore()

  return (
    <aside
      className="absolute top-0 left-0 h-full z-20 flex flex-col
        bg-card/90 backdrop-blur-xl border-r border-border
        transition-all duration-200 ease-in-out overflow-hidden"
      style={{ width: sidebarOpen ? '320px' : '0px', visibility: sidebarOpen ? 'visible' : 'hidden' }}
      aria-hidden={!sidebarOpen}
      {...(!sidebarOpen && { inert: true as any })}
    >
      <div className="w-[320px] h-full flex flex-col overflow-y-auto overflow-x-hidden">
        <div className="p-3 border-b border-border shrink-0">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Controls</p>
        </div>

        <div className="flex-1 overflow-y-auto">
          <Accordion multiple defaultValue={['parameters']}>
            <AccordionItem value="parameters" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">Parameters</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <ParametersPanel />
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

            <AccordionItem value="phantom" className="border-b border-border px-3">
              <AccordionTrigger className="text-sm font-medium py-3">Phantom</AccordionTrigger>
              <AccordionContent>
                <div className="py-2">
                  <PhantomPanel />
                </div>
              </AccordionContent>
            </AccordionItem>

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
          </Accordion>
        </div>
      </div>
    </aside>
  )
}
