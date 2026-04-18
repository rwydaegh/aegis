import { useUIStore } from '@/stores/ui'
import { SIDEBAR_GROUPS, type GroupId } from '@/components/layout/sidebar-config'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

export default function IconRail() {
  const sidebarMode = useUIStore(s => s.sidebarMode)
  const activeGroup = useUIStore(s => s.activeGroup)
  const setSidebarMode = useUIStore(s => s.setSidebarMode)
  const setActiveGroup = useUIStore(s => s.setActiveGroup)

  function handleClick(groupId: GroupId) {
    if (sidebarMode === 'expanded' && activeGroup === groupId) {
      setSidebarMode('rail')
    } else {
      setActiveGroup(groupId)
      setSidebarMode('expanded')
    }
  }

  return (
    <div data-tour="icon-rail" className="w-12 shrink-0 h-full flex flex-col items-center pt-2 gap-1 border-r border-border">
      {SIDEBAR_GROUPS.map(group => {
        const Icon = group.icon
        const isActive = activeGroup === group.id
        return (
          <Tooltip key={group.id}>
            <TooltipTrigger
              onClick={() => handleClick(group.id)}
              data-testid={`sidebar-group-${group.id}`}
              className={cn(
                'relative w-10 h-10 flex items-center justify-center rounded-md transition-colors cursor-pointer',
                isActive && sidebarMode === 'expanded'
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground',
              )}
              aria-label={group.label}
            >
              {isActive && sidebarMode === 'expanded' && (
                <div className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-full bg-primary" />
              )}
              <Icon className="size-5" />
            </TooltipTrigger>
            <TooltipContent side="right">{group.label}</TooltipContent>
          </Tooltip>
        )
      })}
    </div>
  )
}
