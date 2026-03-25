import { Eye, Gamepad2, X, Plus, Layers, Crosshair } from 'lucide-react'
import { useMIMOStore, type PrecoderType } from '@/stores/mimo'
import type { UserMIMOState } from '@/stores/mimo'
import { formatSab } from '@/lib/format'
import { cn } from '@/lib/utils'

const PRECODER_OPTIONS: { value: PrecoderType; label: string }[] = [
  { value: 'mrt', label: 'MRT' },
  { value: 'zf', label: 'ZF' },
  { value: 'mmse', label: 'MMSE' },
  { value: 'zf_exposure', label: 'ZF+Exp' },
]

const PHANTOMS = ['duke', 'ella', 'eartha', 'thelonious'] as const

function complianceColor(user: UserMIMOState): string {
  if (user.compliant === null) return '#666'
  if (!user.compliant) return '#f87171'
  const margin = user.stats?.compliance?.margin_db
  if (margin != null && margin < 1) return '#fbbf24'
  return '#4ade80'
}

export default function MIMOPanel() {
  const enabled = useMIMOStore(s => s.enabled)
  const setEnabled = useMIMOStore(s => s.setEnabled)
  const users = useMIMOStore(s => s.users)
  const focusedUserId = useMIMOStore(s => s.focusedUserId)
  const controlledUserId = useMIMOStore(s => s.controlledUserId)
  const precoderType = useMIMOStore(s => s.precoderType)
  const showAllHeatmaps = useMIMOStore(s => s.showAllHeatmaps)
  const arrayConfig = useMIMOStore(s => s.arrayConfig)

  const addUser = useMIMOStore(s => s.addUser)
  const removeUser = useMIMOStore(s => s.removeUser)
  const setFocusedUser = useMIMOStore(s => s.setFocusedUser)
  const setControlledUser = useMIMOStore(s => s.setControlledUser)
  const focusPoint = useMIMOStore(s => s.focusPoint)
  const setFocusPoint = useMIMOStore(s => s.setFocusPoint)
  const showArrayPattern = useMIMOStore(s => s.showArrayPattern)
  const setPrecoderType = useMIMOStore(s => s.setPrecoderType)
  const setShowAllHeatmaps = useMIMOStore(s => s.setShowAllHeatmaps)
  const setShowArrayPattern = useMIMOStore(s => s.setShowArrayPattern)

  const userList = [...users.values()]
  const K = users.size
  const M = arrayConfig ? arrayConfig.n_h * arrayConfig.n_v : 0

  return (
    <div className="bg-card/80 backdrop-blur-md rounded-lg border border-border p-3 min-w-[220px]">
      {/* Enable checkbox */}
      <label className="flex items-center gap-2 mb-2 cursor-pointer">
        <input
          type="checkbox"
          checked={enabled}
          onChange={e => setEnabled(e.target.checked)}
          className="rounded border-border accent-primary h-3.5 w-3.5"
        />
        <span className="text-xs font-medium text-foreground">Enable MIMO mode</span>
      </label>

      {enabled && (
        <>
          {/* Header */}
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            MIMO ({K} user{K !== 1 ? 's' : ''})
          </p>

          {/* Precoder selector */}
          <div className="flex gap-1 mb-2">
            {PRECODER_OPTIONS.map(opt => {
              const needsMoreAntennas = opt.value !== 'mrt' && M < K
              return (
                <button
                  key={opt.value}
                  disabled={needsMoreAntennas}
                  onClick={() => setPrecoderType(opt.value)}
                  className={cn(
                    'flex-1 text-[10px] py-1 px-1.5 rounded border transition-colors',
                    precoderType === opt.value
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-muted/50 text-muted-foreground border-border hover:bg-muted',
                    needsMoreAntennas && 'opacity-40 cursor-not-allowed',
                  )}
                  title={needsMoreAntennas ? `Requires M >= K (${M} antennas < ${K} users)` : opt.label}
                >
                  {opt.label}
                </button>
              )
            })}

            {/* Show all heatmaps toggle */}
            <button
              onClick={() => setShowAllHeatmaps(!showAllHeatmaps)}
              className={cn(
                'p-1 rounded border transition-colors',
                showAllHeatmaps
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-muted/50 text-muted-foreground border-border hover:bg-muted',
              )}
              title={showAllHeatmaps ? 'Showing all heatmaps' : 'Show focused heatmap only'}
            >
              <Layers className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Array pattern toggle */}
          <label className="flex items-center gap-2 mb-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showArrayPattern}
              onChange={e => setShowArrayPattern(e.target.checked)}
              className="rounded border-border accent-primary h-3.5 w-3.5"
            />
            <span className="text-[10px] text-muted-foreground">Show array pattern</span>
          </label>

          {/* Focus point */}
          <div className="mb-2">
            <div className="flex items-center gap-1 mb-1">
              <Crosshair className="w-3 h-3 text-[#00e5ff]" />
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Focus point</span>
              <button
                onClick={() => setFocusPoint([0, 1.0, 0])}
                className="ml-auto text-[9px] text-muted-foreground hover:text-foreground transition-colors"
                title="Reset to origin"
              >
                reset
              </button>
            </div>
            <div className="flex gap-1">
              {(['X', 'Y', 'Z'] as const).map((axis, i) => (
                <label key={axis} className="flex items-center gap-0.5 flex-1">
                  <span className="text-[9px] text-muted-foreground">{axis}</span>
                  <input
                    type="number"
                    step={0.5}
                    value={focusPoint[i]}
                    onChange={e => {
                      const v = parseFloat(e.target.value)
                      if (isNaN(v)) return
                      const fp: [number, number, number] = [...focusPoint]
                      fp[i] = i === 1 ? Math.max(0, v) : v
                      setFocusPoint(fp)
                    }}
                    className="w-full bg-muted/50 border border-border rounded px-1 py-0.5 text-[10px] text-foreground font-mono"
                  />
                </label>
              ))}
            </div>
            <p className="text-[9px] text-muted-foreground/60 mt-0.5">Shift+click to place</p>
          </div>

          {/* User list */}
          <div className="space-y-1 mb-2">
            {userList.map((user, idx) => {
              const isFocused = user.userId === focusedUserId
              const isControlled = user.userId === controlledUserId
              return (
                <div
                  key={user.userId}
                  className="flex items-center gap-1.5 px-1.5 py-1 rounded text-xs"
                >
                  {/* Compliance dot */}
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: complianceColor(user) }}
                    title={
                      user.compliant === null
                        ? 'Not computed'
                        : user.compliant
                          ? 'Compliant'
                          : 'Non-compliant'
                    }
                  />

                  {/* Index */}
                  <span className="text-muted-foreground w-3 text-right shrink-0 font-mono text-[10px]">
                    {idx + 1}
                  </span>

                  {/* Name */}
                  <span className="text-foreground truncate flex-1" title={user.phantomName}>
                    {user.displayName}
                  </span>

                  {/* Peak Sab */}
                  <span className="text-muted-foreground font-mono text-[10px] shrink-0">
                    {user.stats ? formatSab(user.stats.peak_sab) : '--'}
                  </span>

                  {/* Focus button */}
                  <button
                    onClick={() => setFocusedUser(user.userId)}
                    className={cn(
                      'p-0.5 rounded transition-colors',
                      isFocused
                        ? 'text-primary'
                        : 'text-muted-foreground hover:text-foreground',
                    )}
                    title="Focus camera"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>

                  {/* Control button */}
                  <button
                    onClick={() => setControlledUser(user.userId)}
                    className={cn(
                      'p-0.5 rounded transition-colors',
                      isControlled
                        ? 'text-primary'
                        : 'text-muted-foreground hover:text-foreground',
                    )}
                    title="Keyboard control"
                  >
                    <Gamepad2 className="w-3.5 h-3.5" />
                  </button>

                  {/* Remove button */}
                  <button
                    onClick={() => removeUser(user.userId)}
                    className="p-0.5 rounded text-muted-foreground hover:text-destructive transition-colors"
                    title="Remove user"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              )
            })}
          </div>

          {/* Add user section */}
          <div className="border-t border-border pt-2">
            <p className="text-[10px] text-muted-foreground mb-1">Add user</p>
            <div className="flex flex-wrap gap-1">
              {PHANTOMS.map(phantom => (
                <button
                  key={phantom}
                  disabled={K >= 8}
                  onClick={() => addUser(phantom, [userList.length * 1.0, 0, 0])}
                  className={cn(
                    'flex items-center gap-0.5 text-[10px] py-0.5 px-1.5 rounded border',
                    'bg-muted/50 text-muted-foreground border-border hover:bg-muted transition-colors',
                    K >= 8 && 'opacity-40 cursor-not-allowed',
                  )}
                  title={K >= 8 ? 'Maximum 8 users' : `Add ${phantom}`}
                >
                  <Plus className="w-3 h-3" />
                  {phantom.charAt(0).toUpperCase() + phantom.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
