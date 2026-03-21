import { useUIStore } from '@/stores/ui'
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '@/components/ui/accordion'

const SECTIONS = [
  { value: 'parameters', title: 'Parameters' },
  { value: 'scene', title: 'Scene' },
  { value: 'phantom', title: 'Phantom' },
  { value: 'layers', title: 'Layers' },
  { value: 'raytracing', title: 'Ray Tracing' },
]

export default function Sidebar() {
  const { sidebarOpen } = useUIStore()

  return (
    <aside
      className="absolute top-0 left-0 h-full z-20 flex flex-col
        bg-card/90 backdrop-blur-xl border-r border-border
        transition-all duration-200 ease-in-out overflow-hidden"
      style={{ width: sidebarOpen ? '320px' : '0px' }}
      aria-hidden={!sidebarOpen}
    >
      <div className="w-[320px] h-full flex flex-col overflow-y-auto overflow-x-hidden">
        <div className="p-3 border-b border-border shrink-0">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Controls</p>
        </div>

        <div className="flex-1 overflow-y-auto">
          <Accordion multiple defaultValue={['parameters']}>
            {SECTIONS.map(({ value, title }) => (
              <AccordionItem key={value} value={value} className="border-b border-border px-3">
                <AccordionTrigger className="text-sm font-medium py-3">{title}</AccordionTrigger>
                <AccordionContent>
                  <div className="py-2 text-xs text-muted-foreground">
                    {/* Content filled in later tasks */}
                    {title} controls will appear here.
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </aside>
  )
}
