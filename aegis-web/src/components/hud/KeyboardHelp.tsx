import { useEffect } from 'react'
import { useUIStore } from '@/stores/ui'
import { useMIMOStore } from '@/stores/mimo'

interface Shortcut {
  keys: string[]
  description: string
}

interface ShortcutGroup {
  title: string
  shortcuts: Shortcut[]
}

function Kbd({ children }: { children: string }) {
  return (
    <kbd className="inline-flex items-center justify-center min-w-[1.5rem] h-6 px-1.5 rounded border border-border bg-muted text-foreground text-[11px] font-mono font-medium">
      {children}
    </kbd>
  )
}

function ShortcutRow({ shortcut }: { shortcut: Shortcut }) {
  return (
    <div className="flex items-center justify-between gap-4 py-1">
      <span className="text-xs text-foreground/80">{shortcut.description}</span>
      <div className="flex items-center gap-1 shrink-0">
        {shortcut.keys.map((key, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <span className="text-[10px] text-muted-foreground">+</span>}
            <Kbd>{key}</Kbd>
          </span>
        ))}
      </div>
    </div>
  )
}

export default function KeyboardHelp() {
  const helpOpen = useUIStore(s => s.helpOpen)
  const toggleHelp = useUIStore(s => s.toggleHelp)
  const mimoEnabled = useMIMOStore(s => s.enabled)

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (
        e.target instanceof HTMLInputElement
        || e.target instanceof HTMLSelectElement
        || e.target instanceof HTMLTextAreaElement
      ) return
      if (e.key === '?' || (e.key === '/' && e.shiftKey)) {
        e.preventDefault()
        toggleHelp()
      }
      if (e.key === 'Escape' && helpOpen) {
        e.preventDefault()
        toggleHelp()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [helpOpen, toggleHelp])

  if (!helpOpen) return null

  const groups: ShortcutGroup[] = [
    {
      title: 'Camera',
      shortcuts: [
        { keys: ['WASD'], description: 'Move camera' },
        { keys: ['QE'], description: 'Rotate camera' },
        { keys: ['Space'], description: 'Move up' },
      ],
    },
    {
      title: 'Antenna',
      shortcuts: [
        { keys: ['Click'], description: 'Place antenna on body' },
        { keys: ['\u2190\u2192\u2191\u2193'], description: 'Nudge antenna (1m)' },
        { keys: ['Shift', '\u2190\u2192\u2191\u2193'], description: 'Nudge antenna (3m)' },
        { keys: ['Del'], description: 'Remove antenna' },
      ],
    },
    ...(mimoEnabled ? [{
      title: 'MIMO',
      shortcuts: [
        { keys: ['Tab'], description: 'Cycle to next user' },
        { keys: ['1-9'], description: 'Select user by number' },
      ],
    }] : []),
    {
      title: 'General',
      shortcuts: [
        { keys: ['?'], description: 'Toggle this help' },
        { keys: ['Shift', 'B'], description: 'Report a bug' },
      ],
    },
  ]

  return (
    <>
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 z-50 pointer-events-auto"
        onClick={toggleHelp}
      />
      {/* Modal */}
      <div className="absolute inset-0 flex items-center justify-center z-50 pointer-events-none">
        <div
          className="bg-card/95 backdrop-blur-md rounded-xl border border-border shadow-2xl p-5 min-w-[280px] max-w-[360px] pointer-events-auto animate-in fade-in zoom-in-95 duration-150"
          onClick={e => e.stopPropagation()}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-heading">Keyboard shortcuts</h2>
            <button
              onClick={toggleHelp}
              className="text-muted-foreground hover:text-foreground transition-colors text-xs"
              aria-label="Close"
            >
              Esc
            </button>
          </div>
          <div className="space-y-3">
            {groups.map(group => (
              <div key={group.title}>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1">
                  {group.title}
                </div>
                <div className="divide-y divide-border/50">
                  {group.shortcuts.map((s, i) => (
                    <ShortcutRow key={i} shortcut={s} />
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t border-border/50 text-center">
            <span className="text-[10px] text-muted-foreground">
              Press <Kbd>?</Kbd> or <Kbd>Esc</Kbd> to close
            </span>
          </div>
        </div>
      </div>
    </>
  )
}
