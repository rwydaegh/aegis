import { useUIStore } from '@/stores/ui'
import { useMIMOStore } from '@/stores/mimo'
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '@/components/ui/accordion'
import { PanelErrorBoundary } from '@/components/layout/PanelErrorBoundary'
import type { GroupDef } from '@/components/layout/sidebar-config'

interface SidebarPanelProps {
  group: GroupDef
}

export default function SidebarPanel({ group }: SidebarPanelProps) {
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const openSections = useUIStore(s => s.openSectionsByGroup[group.id])
  const setGroupOpenSections = useUIStore(s => s.setGroupOpenSections)

  const visibleSections = group.sections.filter(
    s => !s.conditionalOn || s.conditionalOn({ mimoEnabled })
  )

  const GroupIcon = group.icon

  return (
    <div className="h-full flex flex-col min-w-0">
      <div className="px-3 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <GroupIcon className="size-3.5 text-muted-foreground" />
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            {group.label}
          </p>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        <Accordion
          multiple
          value={openSections}
          onValueChange={(v: string[]) => setGroupOpenSections(group.id, v)}
        >
          {visibleSections.map(section => {
            const SectionIcon = section.icon
            const Panel = section.component
            return (
              <AccordionItem
                key={section.value}
                value={section.value}
                className="border-b border-border px-3"
              >
                <AccordionTrigger data-testid={`sidebar-section-${section.value}`} className="text-sm font-medium py-3">
                  <div className="flex items-center gap-2">
                    <SectionIcon className="size-4 text-muted-foreground shrink-0" />
                    <span>{section.label}</span>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="py-2">
                    <PanelErrorBoundary name={section.label}>
                      <Panel />
                    </PanelErrorBoundary>
                  </div>
                </AccordionContent>
              </AccordionItem>
            )
          })}
        </Accordion>
      </div>
    </div>
  )
}
