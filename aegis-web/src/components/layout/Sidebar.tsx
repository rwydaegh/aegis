import { useEffect } from 'react'
import { useUIStore, selectSidebarOpen } from '@/stores/ui'
import { useMIMOStore } from '@/stores/mimo'
import { useIsMobile } from '@/hooks/useIsMobile'
import { SIDEBAR_GROUPS } from '@/components/layout/sidebar-config'
import IconRail from '@/components/layout/IconRail'
import SidebarPanel from '@/components/layout/SidebarPanel'
import { cn } from '@/lib/utils'

function MobileTabBar() {
  const activeGroup = useUIStore(s => s.activeGroup)
  const setActiveGroup = useUIStore(s => s.setActiveGroup)

  return (
    <div
      className="flex border-b border-border shrink-0"
      role="tablist"
      aria-label="Sidebar groups"
    >
      {SIDEBAR_GROUPS.map(group => {
        const Icon = group.icon
        const isActive = activeGroup === group.id
        return (
          <button
            key={group.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => setActiveGroup(group.id)}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors',
              isActive
                ? 'text-primary border-b-2 border-primary'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Icon className="size-4" />
            <span>{group.label}</span>
          </button>
        )
      })}
    </div>
  )
}

export default function Sidebar() {
  const sidebarMode = useUIStore(s => s.sidebarMode)
  const activeGroup = useUIStore(s => s.activeGroup)
  const setActiveGroup = useUIStore(s => s.setActiveGroup)
  const setGroupOpenSections = useUIStore(s => s.setGroupOpenSections)
  const sidebarOpen = useUIStore(selectSidebarOpen)
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const isMobile = useIsMobile()

  const activeGroupDef = SIDEBAR_GROUPS.find(g => g.id === activeGroup)!

  // Auto-open MIMO section and switch to Source group when MIMO is toggled on
  useEffect(() => {
    const store = useUIStore.getState()
    const sourceSections = store.openSectionsByGroup.source
    if (mimoEnabled) {
      if (!sourceSections.includes('mimo')) {
        setGroupOpenSections('source', [...sourceSections, 'mimo'])
      }
      setActiveGroup('source')
    } else {
      if (sourceSections.includes('mimo')) {
        setGroupOpenSections('source', sourceSections.filter(s => s !== 'mimo'))
      }
    }
  }, [mimoEnabled, setActiveGroup, setGroupOpenSections])

  // Compute sidebar width
  let width: string
  if (!sidebarOpen) {
    width = '0px'
  } else if (isMobile) {
    width = '100vw'
  } else if (sidebarMode === 'rail') {
    width = '48px'
  } else {
    width = '320px'
  }

  // Panel width (desktop only, inside the flex container)
  const panelWidth = sidebarMode === 'expanded' ? '272px' : '0px'

  return (
    <aside
      data-tour="sidebar"
      className="absolute top-0 left-0 h-full z-20 flex flex-col
        bg-card/90 backdrop-blur-xl border-r border-border
        transition-all duration-200 ease-in-out overflow-hidden"
      style={{ width }}
      aria-hidden={!sidebarOpen}
      {...(!sidebarOpen && { inert: true as any })}
    >
      {isMobile ? (
        /* Mobile: horizontal tabs + panel content, no rail */
        <div className="w-screen h-full flex flex-col">
          <MobileTabBar />
          <div className="flex-1 overflow-hidden">
            <SidebarPanel group={activeGroupDef} />
          </div>
        </div>
      ) : (
        /* Desktop: icon rail + expandable panel */
        <div className="flex h-full">
          <IconRail />
          <div
            className="overflow-hidden transition-all duration-200 ease-in-out"
            style={{ width: panelWidth }}
            {...(sidebarMode !== 'expanded' && { inert: true as any })}
            aria-hidden={sidebarMode !== 'expanded'}
          >
            <div className="w-[272px] h-full">
              <SidebarPanel group={activeGroupDef} />
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
