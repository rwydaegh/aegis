# Phase 3b: Frontend UI panels + user management

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the MIMO user management UI: user list panel, compliance badges, compute trigger hook, and keyboard controls for multi-user positioning.

**Architecture:** Four new files (MIMOPanel, UserBadges, useMIMODosimetry, useMIMOKeyboard) plus integration edits to Sidebar, Toolbar, HudOverlay, and SceneRoot. All new components consume the existing `useMIMOStore` (Phase 3a) and `computeMIMO`/`fetchMIMOResult`/`fetchMIMOSummary` API client (Phase 3a). The `useMIMODosimetry` hook mirrors the existing `useDosimetry` pattern (debounce, abort controller, generation counter) but calls MIMO endpoints. Backend MIMO routes (`/api/mimo/*`) are Phase 2b and may not exist yet; the hook will error gracefully.

**Tech Stack:** React 19, Zustand, TypeScript, Tailwind CSS, lucide-react icons, Vitest for tests.

**Spec:** `docs/design/multi-user-mimo-decisions.md` sections G1-G6, G+.

**Deferred to v2:** Editable display names (spec G3), per-user phantom change after creation (spec G3), drag preview mode with level-2 incoherent (spec G6), bystander support (spec D3).

---

## File map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `aegis-web/src/components/hud/MIMOPanel.tsx` | User list, add/remove, phantom picker, focus/control buttons, precoder selector, show-all-heatmaps toggle |
| Create | `aegis-web/src/components/hud/UserBadges.tsx` | Per-user compliance dot badges for toolbar summary |
| Create | `aegis-web/src/hooks/useMIMODosimetry.ts` | Watches MIMO store, debounces, calls MIMO compute API, fetches per-user results, loads body geometry |
| Create | `aegis-web/src/hooks/useMIMOKeyboard.ts` | WASD moves controlled user, Tab cycles, 1-9 switches, R rotates |
| Modify | `aegis-web/src/components/layout/Sidebar.tsx` | Add MIMOPanel accordion section (visible when MIMO enabled, replaces Phantom panel) |
| Modify | `aegis-web/src/components/layout/Toolbar.tsx` | Add MIMO toggle button, replace ComplianceBadge with UserBadges when MIMO enabled |
| Modify | `aegis-web/src/components/layout/HudOverlay.tsx` | Show MIMO-aware StatsCard (uses useActiveSimulation) |
| Modify | `aegis-web/src/components/scene/SceneRoot.tsx` | Wire useMIMODosimetry and useMIMOKeyboard hooks |
| Create | `aegis-web/src/__tests__/useMIMOKeyboard.test.ts` | Unit tests for keyboard hook |
| Create | `aegis-web/src/__tests__/MIMOPanel.test.tsx` | Unit tests for panel rendering |

---

### Task 1: useMIMOKeyboard hook

**Files:**
- Create: `aegis-web/src/hooks/useMIMOKeyboard.ts`
- Create: `aegis-web/src/__tests__/useMIMOKeyboard.test.ts`

- [ ] **Step 1: Write the hook**

```typescript
// aegis-web/src/hooks/useMIMOKeyboard.ts
import { useEffect } from 'react'
import { useMIMOStore } from '@/stores/mimo'
import { useSceneStore } from '@/stores/scene'

const MOVE_STEP = 0.2
const MOVE_STEP_SHIFT = 1.0
const ROTATION_STEP = Math.PI / 12 // 15 degrees

export function useMIMOKeyboard() {
  const enabled = useMIMOStore(s => s.enabled)

  useEffect(() => {
    if (!enabled) return

    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return

      const store = useMIMOStore.getState()
      if (!store.enabled) return
      const userId = store.controlledUserId
      if (!userId) return

      const user = store.users.get(userId)
      if (!user) return

      const step = e.shiftKey ? MOVE_STEP_SHIFT : MOVE_STEP
      const [x, y, z] = user.position

      // WASD movement
      if (e.code === 'KeyW') { e.preventDefault(); store.moveUser(userId, [x, y, z - step]); return }
      if (e.code === 'KeyS') { e.preventDefault(); store.moveUser(userId, [x, y, z + step]); return }
      if (e.code === 'KeyA') { e.preventDefault(); store.moveUser(userId, [x - step, y, z]); return }
      if (e.code === 'KeyD') { e.preventDefault(); store.moveUser(userId, [x + step, y, z]); return }

      // R to rotate
      if (e.code === 'KeyR') {
        e.preventDefault()
        store.setUserOrientation(userId, user.orientation + ROTATION_STEP)
        return
      }

      // Tab cycles controlled user
      if (e.code === 'Tab') {
        e.preventDefault()
        const ids = [...store.users.keys()]
        if (ids.length < 2) return
        const idx = ids.indexOf(userId)
        const nextIdx = (idx + 1) % ids.length
        store.setControlledUser(ids[nextIdx])
        store.setFocusedUser(ids[nextIdx])
        return
      }

      // Number keys 1-9 switch controlled user
      if (e.code.startsWith('Digit') && !e.ctrlKey && !e.metaKey) {
        const num = parseInt(e.code.replace('Digit', ''), 10)
        if (num < 1 || num > 9) return
        const ids = [...store.users.keys()]
        if (num <= ids.length) {
          e.preventDefault()
          store.setControlledUser(ids[num - 1])
          store.setFocusedUser(ids[num - 1])
        }
        return
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [enabled])
}
```

- [ ] **Step 2: Write unit test**

```typescript
// aegis-web/src/__tests__/useMIMOKeyboard.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useMIMOStore } from '@/stores/mimo'

describe('useMIMOKeyboard store interactions', () => {
  beforeEach(() => {
    useMIMOStore.getState().reset()
  })

  it('Tab cycles through users by insertion order', () => {
    const store = useMIMOStore.getState()
    store.setEnabled(true)
    store.addUser('duke', [0, 0, 0])
    store.addUser('ella', [2, 0, 0])
    const ids = [...useMIMOStore.getState().users.keys()]
    expect(ids).toHaveLength(2)

    // First user is auto-controlled
    expect(useMIMOStore.getState().controlledUserId).toBe(ids[0])

    // Simulate what Tab does: cycle to next
    const current = ids.indexOf(ids[0])
    const nextIdx = (current + 1) % ids.length
    store.setControlledUser(ids[nextIdx])
    expect(useMIMOStore.getState().controlledUserId).toBe(ids[1])
  })

  it('moveUser updates position', () => {
    const store = useMIMOStore.getState()
    store.setEnabled(true)
    store.addUser('duke', [0, 0, 0])
    const id = [...useMIMOStore.getState().users.keys()][0]
    store.moveUser(id, [0.2, 0, 0])
    expect(useMIMOStore.getState().users.get(id)?.position).toEqual([0.2, 0, 0])
  })

  it('number key selects user by index', () => {
    const store = useMIMOStore.getState()
    store.setEnabled(true)
    store.addUser('duke', [0, 0, 0])
    store.addUser('ella', [2, 0, 0])
    const ids = [...useMIMOStore.getState().users.keys()]

    // Select user 2 (1-indexed)
    store.setControlledUser(ids[1])
    store.setFocusedUser(ids[1])
    expect(useMIMOStore.getState().controlledUserId).toBe(ids[1])
    expect(useMIMOStore.getState().focusedUserId).toBe(ids[1])
  })
})
```

- [ ] **Step 3: Run tests**

Run: `cd aegis-web && npx vitest run src/__tests__/useMIMOKeyboard.test.ts`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/hooks/useMIMOKeyboard.ts aegis-web/src/__tests__/useMIMOKeyboard.test.ts
git commit -m "Add useMIMOKeyboard hook for WASD, Tab, number key controls"
```

---

### Task 2: useMIMODosimetry hook

**Files:**
- Create: `aegis-web/src/hooks/useMIMODosimetry.ts`

This hook watches the MIMO store for changes (user positions, precoder type, array config) and triggers MIMO compute calls. It also loads body geometry for new users via `fetchBody()`.

- [ ] **Step 1: Write the hook**

```typescript
// aegis-web/src/hooks/useMIMODosimetry.ts
import { useEffect, useRef, useCallback } from 'react'
import { useMIMOStore } from '@/stores/mimo'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { computeMIMO, fetchMIMOResult, fetchMIMOSummary } from '@/api/mimo'
import { fetchBody } from '@/api/client'
import * as THREE from 'three'
import type { MIMOComputeRequest, MIMOUserConfig } from '@/api/types'

/** Load body geometry for any MIMO user that lacks it. */
async function loadMissingBodies() {
  const { users, setUserBodyGeometry } = useMIMOStore.getState()
  const promises: Promise<void>[] = []

  for (const [id, user] of users) {
    if (user.bodyGeometry) continue
    promises.push(
      fetchBody(user.phantomName).then(({ binary: { positions, normals } }) => {
        const geo = new THREE.BufferGeometry()
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
        geo.setAttribute('normal', new THREE.BufferAttribute(normals, 3))
        // Per-vertex color attribute (3 floats per vertex for jet colormap)
        const colors = new Float32Array(positions.length)
        colors.fill(0.5)
        geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
        geo.computeBoundingSphere()
        setUserBodyGeometry(id, geo)
      })
    )
  }
  await Promise.all(promises)
}

export function useMIMODosimetry() {
  const enabled = useMIMOStore(s => s.enabled)
  const users = useMIMOStore(s => s.users)
  const precoderType = useMIMOStore(s => s.precoderType)
  const arrayConfig = useMIMOStore(s => s.arrayConfig)
  const freqGhz = useSimulationStore(s => s.freqGhz)
  const powerDbm = useSimulationStore(s => s.powerDbm)

  const abortRef = useRef<AbortController | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const generationRef = useRef(0)

  const triggerCompute = useCallback(async () => {
    if (!enabled || !arrayConfig || users.size === 0) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const gen = ++generationRef.current

    const setComputing = useUIStore.getState().setComputing
    setComputing(true)

    try {
      // Load body geometry for new users
      await loadMissingBodies()
      if (gen !== generationRef.current) return

      // Build request
      const mimoUsers: MIMOUserConfig[] = [...useMIMOStore.getState().users.values()].map(u => ({
        id: u.userId,
        phantom: u.phantomName,
        position: u.position,
        orientation: u.orientation,
        device_offset: [0.25, 0, 1.4] as [number, number, number], // default: hand height, 25cm forward
      }))

      const req: MIMOComputeRequest = {
        array: arrayConfig,
        users: mimoUsers,
        freq_hz: freqGhz * 1e9,
        power_dbm: powerDbm,
        precoder_type: precoderType,
      }

      // Trigger server-side compute
      const response = await computeMIMO(req, controller.signal)
      if (gen !== generationRef.current) return

      // Fetch per-user results
      const { setUserResult, setSummaryStats } = useMIMOStore.getState()
      await Promise.all(
        response.user_ids.map(async (uid) => {
          const { sab, stats } = await fetchMIMOResult(uid, controller.signal)
          if (gen !== generationRef.current) return
          setUserResult(uid, sab, stats)
        })
      )
      if (gen !== generationRef.current) return

      // Fetch summary
      const summary = await fetchMIMOSummary(controller.signal)
      if (gen === generationRef.current) {
        setSummaryStats(summary)
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      useNotificationStore.getState().addNotification(
        'error',
        `MIMO compute failed: ${(err as Error).message ?? err}`
      )
    } finally {
      if (gen === generationRef.current) setComputing(false)
    }
  }, [enabled, users, precoderType, arrayConfig, freqGhz, powerDbm])

  // Debounced trigger on dependency change
  useEffect(() => {
    if (!enabled || !arrayConfig) return
    if (timerRef.current) clearTimeout(timerRef.current)

    const config = useSceneStore.getState().viewerConfig
    const debounceMs = config?.interaction?.debounce_ms ?? 500
    timerRef.current = setTimeout(() => { void triggerCompute() }, debounceMs)

    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [enabled, users, precoderType, arrayConfig, freqGhz, powerDbm, triggerCompute])

  // Cancel on unmount
  useEffect(() => {
    return () => { abortRef.current?.abort() }
  }, [])
}
```

- [ ] **Step 2: Run lint**

Run: `cd aegis-web && npx tsc --noEmit`
Expected: No type errors in the new file. Warnings from other files are ok.

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/hooks/useMIMODosimetry.ts
git commit -m "Add useMIMODosimetry hook for MIMO compute orchestration"
```

---

### Task 3: MIMOPanel component

**Files:**
- Create: `aegis-web/src/components/hud/MIMOPanel.tsx`
- Create: `aegis-web/src/__tests__/MIMOPanel.test.tsx`

The MIMOPanel is a sidebar panel showing user list, add/remove buttons, phantom picker per user, focus/control selection, precoder type, and show-all-heatmaps toggle. Follows the visual style of existing panels.

- [ ] **Step 1: Write MIMOPanel**

```tsx
// aegis-web/src/components/hud/MIMOPanel.tsx
import { useMIMOStore, type PrecoderType } from '@/stores/mimo'
import { Eye, Gamepad2, X, Plus, Layers } from 'lucide-react'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { formatSab } from '@/lib/format'

const PHANTOMS = ['duke', 'ella', 'eartha', 'thelonious']
const PRECODERS: Array<{ value: PrecoderType; label: string; tooltip: string }> = [
  { value: 'mrt', label: 'MRT', tooltip: 'Maximum Ratio Transmission' },
  { value: 'zf', label: 'ZF', tooltip: 'Zero-Forcing' },
  { value: 'mmse', label: 'MMSE', tooltip: 'Regularized ZF (MMSE)' },
  { value: 'zf_exposure', label: 'ZF+Exp', tooltip: 'ZF with exposure scaling' },
]

const K_MAX = 8
const DEFAULT_SPACING = 1.0 // meters lateral offset between users

function complianceColor(compliant: boolean | null, marginDb?: number | null): string {
  if (compliant === null) return '#666'
  if (!compliant) return '#f87171'  // red: exceeds limit
  if (marginDb != null && marginDb < 1) return '#fbbf24'  // yellow: within ~10% of limit
  return '#4ade80'  // green: compliant with margin
}

const selectClass =
  'w-full bg-background border border-border rounded px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring'

const btnClass =
  'inline-flex items-center justify-center size-6 rounded transition-colors hover:bg-muted text-muted-foreground hover:text-foreground'

export default function MIMOPanel() {
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
  const setPrecoderType = useMIMOStore(s => s.setPrecoderType)
  const setShowAllHeatmaps = useMIMOStore(s => s.setShowAllHeatmaps)

  const userList = [...users.values()]
  const canAdd = userList.length < K_MAX
  const nElements = arrayConfig ? arrayConfig.n_h * arrayConfig.n_v : 0
  const zfDisabled = nElements > 0 && nElements < userList.length

  function handleAddUser(phantom: string) {
    const offset = userList.length * DEFAULT_SPACING
    addUser(phantom, [offset, 0, 0])
  }

  return (
    <div className="space-y-3">
      {/* Precoder selector */}
      <div>
        <label className="text-xs text-muted-foreground block mb-1">Precoder</label>
        <div className="flex gap-1">
          {PRECODERS.map(({ value, label, tooltip }) => {
            const disabled = (value === 'zf' || value === 'mmse' || value === 'zf_exposure') && zfDisabled
            return (
              <Tooltip key={value}>
                <TooltipTrigger
                  className={cn(
                    'flex-1 px-2 py-1 rounded text-xs font-mono border transition-colors',
                    precoderType === value
                      ? 'bg-primary/15 border-primary/30 text-primary'
                      : 'border-border text-muted-foreground hover:bg-muted hover:text-foreground',
                    disabled && 'opacity-40 pointer-events-none',
                  )}
                  onClick={() => !disabled && setPrecoderType(value)}
                >
                  {label}
                </TooltipTrigger>
                <TooltipContent>
                  {tooltip}
                  {disabled && ` (needs M >= K, have ${nElements} < ${userList.length})`}
                </TooltipContent>
              </Tooltip>
            )
          })}
        </div>
      </div>

      {/* Show all heatmaps toggle */}
      <div className="flex items-center justify-between">
        <label className="text-xs text-muted-foreground">Show all heatmaps</label>
        <button
          className={cn(
            'size-6 rounded flex items-center justify-center transition-colors',
            showAllHeatmaps ? 'bg-primary/15 text-primary' : 'text-muted-foreground hover:bg-muted',
          )}
          onClick={() => setShowAllHeatmaps(!showAllHeatmaps)}
        >
          <Layers className="size-3.5" />
        </button>
      </div>

      {/* User list */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-muted-foreground">
            Users ({userList.length}/{K_MAX})
          </label>
        </div>

        <div className="space-y-1">
          {userList.map((user, idx) => (
            <div
              key={user.userId}
              className={cn(
                'flex items-center gap-2 rounded px-2 py-1.5 text-xs border transition-colors',
                user.userId === focusedUserId
                  ? 'border-primary/30 bg-primary/5'
                  : 'border-transparent hover:bg-muted/50',
              )}
            >
              {/* Compliance dot */}
              <span
                className="size-2 rounded-full shrink-0"
                style={{ backgroundColor: complianceColor(user.compliant, user.stats?.compliance?.margin_db) }}
                title={user.compliant === null ? 'Not computed' : user.compliant ? 'Compliant' : 'Non-compliant'}
              />

              {/* Index + name */}
              <span className="font-mono text-muted-foreground w-4 shrink-0">{idx + 1}</span>
              <span className="truncate flex-1 text-foreground">{user.displayName}</span>

              {/* Peak Sab */}
              <span className="text-muted-foreground font-mono text-[10px] shrink-0">
                {user.stats ? formatSab(user.stats.peak_sab) : '--'}
              </span>

              {/* Focus button */}
              <Tooltip>
                <TooltipTrigger
                  className={cn(btnClass, user.userId === focusedUserId && 'text-primary')}
                  onClick={() => setFocusedUser(user.userId)}
                >
                  <Eye className="size-3" />
                </TooltipTrigger>
                <TooltipContent>Focus (show heatmap)</TooltipContent>
              </Tooltip>

              {/* Control button */}
              <Tooltip>
                <TooltipTrigger
                  className={cn(btnClass, user.userId === controlledUserId && 'text-primary')}
                  onClick={() => setControlledUser(user.userId)}
                >
                  <Gamepad2 className="size-3" />
                </TooltipTrigger>
                <TooltipContent>Control (WASD moves this user)</TooltipContent>
              </Tooltip>

              {/* Remove button */}
              <Tooltip>
                <TooltipTrigger
                  className={cn(btnClass, 'hover:text-destructive')}
                  onClick={() => removeUser(user.userId)}
                >
                  <X className="size-3" />
                </TooltipTrigger>
                <TooltipContent>Remove user</TooltipContent>
              </Tooltip>
            </div>
          ))}
        </div>

        {/* Add user dropdown */}
        {canAdd && (
          <div className="mt-2">
            <label className="text-xs text-muted-foreground block mb-1">Add user</label>
            <div className="flex gap-1 flex-wrap">
              {PHANTOMS.map(p => (
                <button
                  key={p}
                  className="px-2 py-1 rounded text-xs border border-border text-muted-foreground
                    hover:bg-muted hover:text-foreground transition-colors capitalize"
                  onClick={() => handleAddUser(p)}
                >
                  <Plus className="size-3 inline mr-0.5 -mt-px" />
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Write unit test**

```tsx
// aegis-web/src/__tests__/MIMOPanel.test.tsx
import { describe, it, expect, beforeEach } from 'vitest'
import { useMIMOStore } from '@/stores/mimo'

describe('MIMOPanel store interactions', () => {
  beforeEach(() => {
    useMIMOStore.getState().reset()
  })

  it('addUser creates user with auto-incremented name', () => {
    const store = useMIMOStore.getState()
    store.addUser('duke', [0, 0, 0])
    store.addUser('ella', [1, 0, 0])
    const users = [...useMIMOStore.getState().users.values()]
    expect(users).toHaveLength(2)
    expect(users[0].displayName).toBe('User 1')
    expect(users[1].displayName).toBe('User 2')
  })

  it('removeUser does not renumber remaining users', () => {
    const store = useMIMOStore.getState()
    store.addUser('duke', [0, 0, 0])
    store.addUser('ella', [1, 0, 0])
    const firstId = [...useMIMOStore.getState().users.keys()][0]
    store.removeUser(firstId)
    const remaining = [...useMIMOStore.getState().users.values()]
    expect(remaining).toHaveLength(1)
    expect(remaining[0].displayName).toBe('User 2') // not renumbered
  })

  it('first user becomes focused and controlled', () => {
    useMIMOStore.getState().addUser('duke', [0, 0, 0])
    const id = [...useMIMOStore.getState().users.keys()][0]
    expect(useMIMOStore.getState().focusedUserId).toBe(id)
    expect(useMIMOStore.getState().controlledUserId).toBe(id)
  })

  it('setPrecoderType updates store', () => {
    useMIMOStore.getState().setPrecoderType('mmse')
    expect(useMIMOStore.getState().precoderType).toBe('mmse')
  })
})
```

- [ ] **Step 3: Run tests**

Run: `cd aegis-web && npx vitest run src/__tests__/MIMOPanel.test.tsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/hud/MIMOPanel.tsx aegis-web/src/__tests__/MIMOPanel.test.tsx
git commit -m "Add MIMOPanel with user list, precoder selector, add/remove controls"
```

---

### Task 4: UserBadges component

**Files:**
- Create: `aegis-web/src/components/hud/UserBadges.tsx`

Small component for the toolbar showing per-user compliance dots and a summary like "2/3 compliant".

- [ ] **Step 1: Write UserBadges**

```tsx
// aegis-web/src/components/hud/UserBadges.tsx
import { useMIMOStore } from '@/stores/mimo'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'

export default function UserBadges() {
  const users = useMIMOStore(s => s.users)
  const userList = [...users.values()]
  if (userList.length === 0) return null

  const computed = userList.filter(u => u.compliant !== null)
  const compliant = computed.filter(u => u.compliant === true)
  const allComputed = computed.length === userList.length && userList.length > 0

  if (!allComputed) {
    return (
      <Badge variant="outline" className="text-muted-foreground border-muted-foreground/30 font-mono text-xs">
        {userList.length} users
      </Badge>
    )
  }

  const allPass = compliant.length === computed.length
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="flex items-center gap-1.5">
          <Badge
            className={
              allPass
                ? 'bg-success/20 text-success border-success/30 font-mono text-xs'
                : 'bg-destructive/20 text-destructive border-destructive/30 font-mono text-xs'
            }
          >
            {compliant.length}/{computed.length}
          </Badge>
          <div className="flex gap-0.5">
            {userList.map(u => (
              <span
                key={u.userId}
                className="size-1.5 rounded-full"
                style={{
                  backgroundColor:
                    u.compliant === null ? '#666' : u.compliant ? '#4ade80' : '#f87171',
                }}
              />
            ))}
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        {compliant.length} of {computed.length} users compliant
      </TooltipContent>
    </Tooltip>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add aegis-web/src/components/hud/UserBadges.tsx
git commit -m "Add UserBadges toolbar component for MIMO compliance summary"
```

---

### Task 5: Integrate into Sidebar

**Files:**
- Modify: `aegis-web/src/components/layout/Sidebar.tsx:1-112`

When MIMO is enabled, show MIMOPanel in the accordion (as "MIMO Users" section before Phantom). The Phantom panel is hidden when MIMO is on (phantom selection happens per-user inside MIMOPanel).

- [ ] **Step 1: Edit Sidebar.tsx**

Add import at top:
```typescript
import { useMIMOStore } from '@/stores/mimo'
import MIMOPanel from '@/components/hud/MIMOPanel'
```

Inside the `Sidebar` function, after `const { sidebarOpen } = useUIStore()`:
```typescript
const mimoEnabled = useMIMOStore(s => s.enabled)
```

Add a new AccordionItem before the Phantom panel (between Scene and Phantom):
```tsx
{mimoEnabled && (
  <AccordionItem value="mimo-users" className="border-b border-border px-3">
    <AccordionTrigger className="text-sm font-medium py-3">MIMO Users</AccordionTrigger>
    <AccordionContent>
      <div className="py-2">
        <MIMOPanel />
      </div>
    </AccordionContent>
  </AccordionItem>
)}

{!mimoEnabled && (
  <AccordionItem value="phantom" className="border-b border-border px-3">
    ...existing phantom panel...
  </AccordionItem>
)}
```

The `defaultValue` should include `'mimo-users'` when MIMO is enabled so it opens automatically.

- [ ] **Step 2: Run lint**

Run: `cd aegis-web && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/layout/Sidebar.tsx
git commit -m "Wire MIMOPanel into sidebar, hide Phantom panel in MIMO mode"
```

---

### Task 6: Integrate into Toolbar

**Files:**
- Modify: `aegis-web/src/components/layout/Toolbar.tsx:1-198`

Add MIMO toggle button and swap ComplianceBadge for UserBadges when MIMO is enabled.

- [ ] **Step 1: Edit Toolbar.tsx**

Add imports:
```typescript
import { useMIMOStore } from '@/stores/mimo'
import UserBadges from '@/components/hud/UserBadges'
import { Users } from 'lucide-react'
```

In the Toolbar function, add:
```typescript
const mimoEnabled = useMIMOStore(s => s.enabled)
const setMIMOEnabled = useMIMOStore(s => s.setEnabled)
```

In the center-left compliance section, replace `<ComplianceBadge stats={stats} />` with:
```tsx
{mimoEnabled ? <UserBadges /> : <ComplianceBadge stats={stats} />}
```

In the right button group (before Share button), add a MIMO toggle:
```tsx
<Tooltip>
  <TooltipTrigger
    onClick={() => setMIMOEnabled(!mimoEnabled)}
    className={cn(
      'inline-flex items-center justify-center size-7 rounded-md transition-colors',
      'hover:bg-muted text-muted-foreground hover:text-foreground',
      mimoEnabled && 'bg-primary/15 text-primary',
    )}
    aria-label="Toggle MIMO mode"
  >
    <Users className="size-4" />
  </TooltipTrigger>
  <TooltipContent>
    {mimoEnabled ? 'Disable MIMO mode' : 'Enable MIMO mode'}
  </TooltipContent>
</Tooltip>
```

- [ ] **Step 2: Run lint**

Run: `cd aegis-web && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/layout/Toolbar.tsx
git commit -m "Add MIMO toggle and UserBadges to toolbar"
```

---

### Task 7: Wire hooks into SceneRoot and fix WASD conflict

**Files:**
- Modify: `aegis-web/src/components/scene/SceneRoot.tsx:1-276`
- Modify: `aegis-web/src/hooks/useKeyboard.ts:1-84`

Add the two new hooks so they run when the canvas is active.

- [ ] **Step 1: Edit SceneRoot.tsx**

Add imports:
```typescript
import { useMIMODosimetry } from '@/hooks/useMIMODosimetry'
import { useMIMOKeyboard } from '@/hooks/useMIMOKeyboard'
```

Add two new controller components (alongside existing DosimetryController):
```typescript
function MIMODosimetryController() {
  useMIMODosimetry()
  return null
}

function MIMOKeyboardController() {
  useMIMOKeyboard()
  return null
}
```

In the SceneRoot render, after `<DosimetryController />`, add:
```tsx
<MIMODosimetryController />
<MIMOKeyboardController />
```

Note: `useMIMOKeyboard` listens to window events so it works outside the Canvas, but placing it inside the Canvas tree keeps the lifecycle tied to the scene. The `useMIMODosimetry` hook checks `enabled` internally so it no-ops in single-user mode.

**Important: WASD conflict.** The existing `useKeyboard` hook also claims WASD for physics-based body movement. When MIMO is enabled, both hooks would fire on WASD. Fix: in `useKeyboard.ts`, add a guard at the top of `handleKeyDown`:
```typescript
if (useMIMOStore.getState().enabled) return
```
This disables single-user WASD/physics when MIMO is active. Import `useMIMOStore` at the top of `useKeyboard.ts`.

- [ ] **Step 2: Run lint**

Run: `cd aegis-web && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/scene/SceneRoot.tsx
git commit -m "Wire useMIMODosimetry and useMIMOKeyboard into SceneRoot"
```

---

### Task 8: Update HudOverlay for MIMO awareness

**Files:**
- Modify: `aegis-web/src/components/layout/HudOverlay.tsx:1-43`
- Modify: `aegis-web/src/components/hud/StatsCard.tsx:1-83`
- Modify: `aegis-web/src/components/hud/CompliancePanel.tsx:1-120`

Make StatsCard and CompliancePanel use `useActiveSimulation` so they show the focused user's data in MIMO mode.

- [ ] **Step 1: Update StatsCard.tsx**

Replace direct `useSimulationStore` reads with `useActiveSimulation`:

```typescript
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
```

Change: `const { stats } = useSimulationStore()` to `const { stats } = useActiveSimulation()`

Keep the `bodyName` from `useSceneStore` for mass lookup. In MIMO mode, the focused user's phantom determines mass. Add:
```typescript
import { useMIMOStore } from '@/stores/mimo'
```
Then:
```typescript
const mimoEnabled = useMIMOStore(s => s.enabled)
const focusedUser = useMIMOStore(s =>
  s.focusedUserId ? s.users.get(s.focusedUserId) ?? null : null
)
const phantomName = mimoEnabled && focusedUser ? focusedUser.phantomName : bodyName
const meta = PHANTOM_META[phantomName.toLowerCase()]
```

Note: do NOT use `s.focusedUser()` inside a Zustand selector. Use the inline derivation pattern shown above (same as `useActiveSimulation.ts:23-25`).

- [ ] **Step 2: Update CompliancePanel.tsx**

Add `useActiveSimulation` import and use it for stats:
```typescript
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
```

Replace `const stats = useSimulationStore(s => s.stats)` with `const { stats } = useActiveSimulation()`.

- [ ] **Step 3: Run lint**

Run: `cd aegis-web && npx tsc --noEmit`

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/hud/StatsCard.tsx aegis-web/src/components/hud/CompliancePanel.tsx
git commit -m "Make StatsCard and CompliancePanel MIMO-aware via useActiveSimulation"
```

---

### Task 9: Set default ArrayConfig on MIMO enable

**Files:**
- Modify: `aegis-web/src/stores/mimo.ts:65-167`

When MIMO is enabled and no `arrayConfig` exists, set a sensible default (4x4 UPA at the current antenna position). This ensures the MIMOPanel and scene have something to work with immediately.

- [ ] **Step 1: Edit mimo.ts setEnabled action**

Replace the `setEnabled` action:
```typescript
setEnabled: (on) => {
  const updates: Partial<MIMOStore> = { enabled: on }
  if (on && !get().arrayConfig) {
    // Default 4x4 UPA at current antenna position or [5, 0, 3]
    const antennaPos = useSimulationStore.getState().antennaPos
    updates.arrayConfig = {
      type: 'upa',
      n_h: 4,
      n_v: 4,
      d_h_wavelengths: 0.5,
      d_v_wavelengths: 0.5,
      position: antennaPos ?? [5, 0, 3],
      broadside: [-1, 0, 0],
    }
  }
  set(updates)
},
```

Add import at top of mimo.ts:
```typescript
import { useSimulationStore } from './simulation'
```

- [ ] **Step 2: Run store tests**

Run: `cd aegis-web && npx vitest run src/stores/__tests__/mimo.test.ts`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/stores/mimo.ts
git commit -m "Set default 4x4 ArrayConfig when MIMO is first enabled"
```

---

### Task 10: Integration verification

- [ ] **Step 1: Run all frontend tests**

Run: `cd aegis-web && npx vitest run`
Expected: All tests pass.

- [ ] **Step 2: Run TypeScript check**

Run: `cd aegis-web && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Build check**

Run: `cd aegis-web && npm run build`
Expected: Build succeeds.

- [ ] **Step 4: Commit any fixes, then final commit**

If any fixes were needed, commit them. Then push:
```bash
git push origin wt/multi-user-3b
```
