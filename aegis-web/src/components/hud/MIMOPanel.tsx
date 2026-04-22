import { Eye, Gamepad2, X, Plus, Layers, Crosshair, AlertTriangle, RefreshCw, Smartphone } from 'lucide-react'
import EcbfWarningChip from './EcbfWarningChip'
import { useMIMOStore, precoderRequiresMgeK, type PrecoderType } from '@/stores/mimo'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import type { UserMIMOState } from '@/stores/mimo'
import { formatSab } from '@/lib/format'
import { cn } from '@/lib/utils'

const PRECODER_OPTIONS: { value: PrecoderType; label: string }[] = [
  { value: 'mrt', label: 'MRT' },
  { value: 'zf', label: 'ZF' },
  { value: 'mmse', label: 'MMSE' },
  { value: 'zf_exposure', label: 'ZF+Exp' },
]

function complianceColor(user: UserMIMOState, errored: boolean): string {
  if (user.compliant === null) return errored ? '#f87171' : '#666'
  if (!user.compliant) return '#f87171'
  const margin = user.stats?.compliance?.margin_db
  if (margin != null && margin < 1) return '#fbbf24'
  return '#4ade80'
}

function complianceTitle(user: UserMIMOState, errored: boolean): string {
  if (user.compliant === null) return errored ? 'Compute failed' : 'Not computed'
  return user.compliant ? 'Compliant' : 'Non-compliant'
}

interface UserRowProps {
  user: UserMIMOState
  idx: number
  focusedUserId: string | null
  controlledUserId: string | null
  errored: boolean
  onFocus: (id: string) => void
  onControl: (id: string) => void
  onRemove: (id: string) => void
}

function UserRow({ user, idx, focusedUserId, controlledUserId, errored, onFocus, onControl, onRemove }: UserRowProps) {
  const isFocused = user.userId === focusedUserId
  const isControlled = user.userId === controlledUserId
  const sabLabel = user.stats ? formatSab(user.stats.peak_sab) : (errored ? 'err' : '--')
  return (
    <div className="flex items-center gap-1.5 px-1.5 py-1 rounded text-xs">
      <span
        className="w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: complianceColor(user, errored && !user.stats) }}
        title={complianceTitle(user, errored && !user.stats)}
      />
      <span className="text-muted-foreground w-3 text-right shrink-0 font-mono text-[10px]">
        {idx + 1}
      </span>
      <span className="text-foreground truncate flex-1" title={user.phantomName}>
        {user.displayName}
      </span>
      <span
        className={cn(
          'font-mono text-[10px] shrink-0',
          errored && !user.stats ? 'text-destructive' : 'text-muted-foreground',
        )}
      >
        {sabLabel}
      </span>
      <button
        onClick={() => onFocus(user.userId)}
        className={cn(
          'p-0.5 rounded transition-colors',
          isFocused ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
        )}
        title="Focus camera"
      >
        <Eye className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={() => onControl(user.userId)}
        className={cn(
          'p-0.5 rounded transition-colors',
          isControlled ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
        )}
        title="Keyboard control"
      >
        <Gamepad2 className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={() => onRemove(user.userId)}
        className="p-0.5 rounded text-muted-foreground hover:text-destructive transition-colors"
        title="Remove user"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

interface AddUserSectionProps {
  availablePhantoms: string[]
  userCount: number
  userListLength: number
}

function AddUserSection({ availablePhantoms, userCount, userListLength }: AddUserSectionProps) {
  const addUser = useMIMOStore(s => s.addUser)
  const maxReached = userCount >= 8
  return (
    <div className="border-t border-border pt-2">
      <p className="text-[10px] text-muted-foreground mb-1">Add user</p>
      <div className="flex flex-wrap gap-1">
        {availablePhantoms.map(phantom => (
          <button
            key={phantom}
            disabled={maxReached}
            onClick={() => {
              const bodyOffset = useSimulationStore.getState().bodyOffset
              addUser(phantom, [bodyOffset[0] + userListLength * 1.0, bodyOffset[1], bodyOffset[2]])
            }}
            className={cn(
              'flex items-center gap-0.5 text-[10px] py-0.5 px-1.5 rounded border',
              'bg-muted/50 text-muted-foreground border-border hover:bg-muted transition-colors',
              maxReached && 'opacity-40 cursor-not-allowed',
            )}
            title={maxReached ? 'Maximum 8 users' : `Add ${phantom}`}
          >
            <Plus className="w-3 h-3" />
            {phantom.charAt(0).toUpperCase() + phantom.slice(1)}
          </button>
        ))}
      </div>
    </div>
  )
}

interface FocusPointControlProps {
  focusPoint: [number, number, number]
  onSet: (fp: [number, number, number]) => void
  onReset: () => void
}

function FocusPointControl({ focusPoint, onSet, onReset }: FocusPointControlProps) {
  return (
    <div className="mb-2">
      <div className="flex items-center gap-1 mb-1">
        <Crosshair className="w-3 h-3 text-[#00e5ff]" />
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Focus point</span>
        <button
          onClick={onReset}
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
                onSet(fp)
              }}
              className="w-full bg-muted/50 border border-border rounded px-1 py-0.5 text-[10px] text-foreground font-mono"
            />
          </label>
        ))}
      </div>
      <p className="text-[9px] text-muted-foreground/60 mt-0.5">Shift+click to place</p>
    </div>
  )
}

interface DeviceOffsetControlProps {
  effective: [number, number, number]
  isOverridden: boolean
  onSet: (offset: [number, number, number]) => void
  onReset: () => void
}

function DeviceOffsetControl({ effective, isOverridden, onSet, onReset }: DeviceOffsetControlProps) {
  const axisLabels = ['X', 'Y', 'Z'] as const
  const axisTitles = ['Right (+) / left (-) of body', 'Forward (+) from body', 'Height above ground']
  return (
    <div className="mb-2">
      <div className="flex items-center gap-1 mb-1">
        <Smartphone className="w-3 h-3 text-[#00e5ff]" />
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Phone offset</span>
        {isOverridden && (
          <button
            onClick={onReset}
            className="ml-auto text-[9px] text-muted-foreground hover:text-foreground transition-colors"
            title="Reset to phantom default"
          >
            reset
          </button>
        )}
      </div>
      <div className="flex gap-1">
        {axisLabels.map((axis, i) => (
          <label key={axis} className="flex items-center gap-0.5 flex-1" title={axisTitles[i]}>
            <span className="text-[9px] text-muted-foreground">{axis}</span>
            <input
              type="number"
              step={0.05}
              value={Number(effective[i].toFixed(3))}
              onChange={e => {
                const v = parseFloat(e.target.value)
                if (isNaN(v)) return
                const next: [number, number, number] = [...effective]
                next[i] = i === 2 ? Math.max(0, v) : v
                onSet(next)
              }}
              className="w-full bg-muted/50 border border-border rounded px-1 py-0.5 text-[10px] text-foreground font-mono"
            />
          </label>
        ))}
      </div>
      <p className="text-[9px] text-muted-foreground/60 mt-0.5">Body-relative, meters (Z-up)</p>
    </div>
  )
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

  const removeUser = useMIMOStore(s => s.removeUser)
  const setFocusedUser = useMIMOStore(s => s.setFocusedUser)
  const setControlledUser = useMIMOStore(s => s.setControlledUser)
  const focusPoint = useMIMOStore(s => s.focusPoint)
  const setFocusPoint = useMIMOStore(s => s.setFocusPoint)
  const showArrayPattern = useMIMOStore(s => s.showArrayPattern)
  const setPrecoderType = useMIMOStore(s => s.setPrecoderType)
  const setShowAllHeatmaps = useMIMOStore(s => s.setShowAllHeatmaps)
  const setShowArrayPattern = useMIMOStore(s => s.setShowArrayPattern)
  const deviceOffsetOverride = useMIMOStore(s => s.deviceOffsetOverride)
  const setDeviceOffsetOverride = useMIMOStore(s => s.setDeviceOffsetOverride)
  const caps = useSceneStore(s => s.capabilities)
  const summaryStats = useMIMOStore(s => s.summaryStats)
  const lastComputeError = useMIMOStore(s => s.lastComputeError)
  const retryCompute = useMIMOStore(s => s.retryCompute)
  const isComputing = useUIStore(s => s.isComputing)

  const userList = [...users.values()]
  const K = users.size
  const M = arrayConfig ? arrayConfig.n_h * arrayConfig.n_v : 0
  const availablePhantoms = caps?.bodies ?? []

  const FALLBACK_DEVICE_OFFSET: [number, number, number] = [0, 0.30, 1.4]
  const focusedUser = focusedUserId ? users.get(focusedUserId) : null
  const defaultOffsetPhantom = focusedUser?.phantomName ?? userList[0]?.phantomName
  const phantomDefault = defaultOffsetPhantom
    ? (caps?.body_device_offsets?.[defaultOffsetPhantom] as [number, number, number] | undefined)
    : undefined
  const effectiveDeviceOffset: [number, number, number] =
    deviceOffsetOverride ?? phantomDefault ?? FALLBACK_DEVICE_OFFSET

  return (
    <div className="bg-card/80 backdrop-blur-md rounded-lg border border-border p-3 min-w-[220px]">
      <label className="flex items-center gap-2 mb-2 cursor-pointer">
        <input
          type="checkbox"
          checked={enabled}
          onChange={e => setEnabled(e.target.checked)}
          data-testid="mimo-enable"
          className="rounded border-border accent-primary h-3.5 w-3.5"
        />
        <span className="text-xs font-medium text-foreground">Enable MIMO mode</span>
      </label>

      {enabled && (
        <>
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            MIMO ({K} user{K !== 1 ? 's' : ''})
          </p>

          <div className="flex gap-1 mb-2">
            {PRECODER_OPTIONS.map(opt => {
              const needsMoreAntennas = precoderRequiresMgeK(opt.value) && M < K
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

          <label className="flex items-center gap-2 mb-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showArrayPattern}
              onChange={e => setShowArrayPattern(e.target.checked)}
              className="rounded border-border accent-primary h-3.5 w-3.5"
            />
            <span className="text-[10px] text-muted-foreground">Show array pattern</span>
          </label>

          {summaryStats?.warning && (
            <div className="flex items-start gap-1.5 mb-2 px-1.5 py-1.5 rounded bg-yellow-500/10 border border-yellow-500/30 text-yellow-400">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span className="text-[10px] leading-tight">{summaryStats.warning}</span>
            </div>
          )}

          {summaryStats?.ecbf_warnings && summaryStats.ecbf_warnings.length > 0 && (
            <EcbfWarningChip warnings={summaryStats.ecbf_warnings} className="mb-2" />
          )}

          {lastComputeError && (
            <div className="flex items-start gap-1.5 mb-2 px-1.5 py-1.5 rounded bg-destructive/10 border border-destructive/30 text-destructive">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="text-[10px] leading-tight font-semibold">MIMO compute failed</div>
                <div className="text-[10px] leading-tight opacity-80 truncate" title={lastComputeError}>
                  {lastComputeError}
                </div>
              </div>
              <button
                onClick={retryCompute}
                disabled={isComputing}
                className={cn(
                  'flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded border border-destructive/40',
                  'hover:bg-destructive/20 transition-colors',
                  isComputing && 'opacity-40 cursor-not-allowed',
                )}
                title="Retry MIMO compute"
              >
                <RefreshCw className="w-3 h-3" />
                Retry
              </button>
            </div>
          )}

          <FocusPointControl
            focusPoint={focusPoint}
            onSet={setFocusPoint}
            onReset={() => setFocusPoint([0, 1.0, 0])}
          />

          <DeviceOffsetControl
            effective={effectiveDeviceOffset}
            isOverridden={deviceOffsetOverride !== null}
            onSet={setDeviceOffsetOverride}
            onReset={() => setDeviceOffsetOverride(null)}
          />

          <div className="space-y-1 mb-2">
            {userList.map((user, idx) => (
              <UserRow
                key={user.userId}
                user={user}
                idx={idx}
                focusedUserId={focusedUserId}
                controlledUserId={controlledUserId}
                errored={lastComputeError !== null}
                onFocus={setFocusedUser}
                onControl={setControlledUser}
                onRemove={removeUser}
              />
            ))}
          </div>

          <AddUserSection
            availablePhantoms={availablePhantoms}
            userCount={K}
            userListLength={userList.length}
          />
        </>
      )}
    </div>
  )
}
