# Phase 3a: Frontend MIMO store + 3D rendering

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-user MIMO support to the frontend: a Zustand store for MIMO state, an API client for MIMO endpoints, an adaptor hook that makes existing components work in both single-user and MIMO mode, a reusable BodyMeshInstance component, and an AntennaArray 3D visualization.

**Architecture:** New `useMIMOStore` holds per-user state (Map of UserMIMOState). A `useActiveSimulation()` adaptor hook returns the focused user's data in MIMO mode or delegates to the existing single-user store. `BodyMeshInstance` is a pure-props component extracted from the current `BodyMesh`. `SceneRoot` conditionally renders multiple bodies + AntennaArray in MIMO mode. The existing single-user path is untouched when MIMO is disabled.

**Tech Stack:** React 19, Three.js 0.183, @react-three/fiber 9, @react-three/drei 10, Zustand 5, TypeScript 5.9, Vitest

**Spec:** `docs/design/multi-user-mimo-decisions.md` (sections G1-G4, F1)

---

## File structure

### New files

| File | Purpose |
|------|---------|
| `aegis-web/src/stores/mimo.ts` | Zustand MIMO store: users Map, focused/controlled user, precoder type, array config, summary stats |
| `aegis-web/src/stores/__tests__/mimo.test.ts` | Unit tests for MIMO store actions and selectors |
| `aegis-web/src/api/mimo.ts` | API client: `computeMIMO`, `fetchMIMOResult`, `fetchMIMOSummary` |
| `aegis-web/src/api/__tests__/mimo.test.ts` | Unit tests for MIMO API payload construction |
| `aegis-web/src/hooks/useActiveSimulation.ts` | Adaptor hook dispatching single-user vs MIMO based on `mimoEnabled` |
| `aegis-web/src/components/scene/BodyMeshInstance.tsx` | Reusable body mesh component with explicit props (geometry, sabArray, position, rotation, opacity, onClick) |
| `aegis-web/src/components/scene/AntennaArray.tsx` | UPA grid visualization using InstancedMesh, broadside arrow, draggable |

### Modified files

| File | Change |
|------|--------|
| `aegis-web/src/api/types.ts` | Add MIMO-related type definitions (ArrayConfig, UserMIMOState, MIMOSummary, MIMOComputeRequest, MIMOComputeResponse) |
| `aegis-web/src/components/scene/BodyMesh.tsx` | Refactor to delegate to BodyMeshInstance, passing props from store |
| `aegis-web/src/components/scene/SceneRoot.tsx` | Conditionally render MIMO scene (multiple BodyMeshInstance + AntennaArray) vs single-user scene |

---

## Task 1: MIMO types in api/types.ts

**Files:**
- Modify: `aegis-web/src/api/types.ts:270-272`

- [ ] **Step 1: Add MIMO type definitions**

Append to `aegis-web/src/api/types.ts` before the final `ScenePos` re-export:

```typescript
// --- MIMO types ---

export interface ArrayConfig {
  type: 'upa'
  n_h: number
  n_v: number
  d_h_wavelengths: number
  d_v_wavelengths: number
  position: ScenePos
  broadside: [number, number, number]
}

export interface MIMOUserConfig {
  id: string
  phantom: string
  position: ScenePos
  orientation: number
  device_offset: [number, number, number]
}

export interface MIMOComputeRequest {
  array: ArrayConfig
  users: MIMOUserConfig[]
  freq_hz: number
  power_dbm: number
  precoder_type: string
  changed?: {
    type: string
    user_id?: string
  }
}

export interface MIMOComputeResponse {
  user_ids: string[]
  compute_time_ms: number
  precoder_type: string
}

export interface MIMOUserSummary {
  id: string
  p_abs: number
  p_abs_mw: number
  peak_sab: number
  compliant: boolean
  margin_db: number
}

export interface MIMOSummary {
  users: MIMOUserSummary[]
  precoder: {
    type: string
    power_total: number
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add aegis-web/src/api/types.ts
git commit -m "Add MIMO type definitions to api/types.ts"
```

---

## Task 2: MIMO Zustand store

**Files:**
- Create: `aegis-web/src/stores/mimo.ts`
- Test: `aegis-web/src/stores/__tests__/mimo.test.ts`

- [ ] **Step 1: Write failing tests for the MIMO store**

Create `aegis-web/src/stores/__tests__/mimo.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { useMIMOStore } from '../mimo'
import type { BufferGeometry } from 'three'

describe('MIMO store', () => {
  beforeEach(() => {
    useMIMOStore.getState().reset()
  })

  it('starts disabled with no users', () => {
    const s = useMIMOStore.getState()
    expect(s.enabled).toBe(false)
    expect(s.users.size).toBe(0)
    expect(s.focusedUserId).toBeNull()
    expect(s.controlledUserId).toBeNull()
  })

  it('addUser creates a user and sets focus/control if first', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [2, 0, -3])
    const state = useMIMOStore.getState()
    expect(state.users.size).toBe(1)
    const user = [...state.users.values()][0]
    expect(user.phantomName).toBe('thelonious')
    expect(user.position).toEqual([2, 0, -3])
    expect(state.focusedUserId).toBe(user.userId)
    expect(state.controlledUserId).toBe(user.userId)
  })

  it('addUser auto-names sequentially', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    s.addUser('duke', [2, 0, 0])
    const names = [...useMIMOStore.getState().users.values()].map(u => u.displayName)
    expect(names).toEqual(['User 1', 'User 2'])
  })

  it('removeUser deletes user and transfers focus', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    s.addUser('duke', [2, 0, 0])
    const ids = [...useMIMOStore.getState().users.keys()]
    s.removeUser(ids[0])
    const state = useMIMOStore.getState()
    expect(state.users.size).toBe(1)
    expect(state.focusedUserId).toBe(ids[1])
    expect(state.controlledUserId).toBe(ids[1])
  })

  it('removeUser does not renumber display names', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    s.addUser('duke', [2, 0, 0])
    s.addUser('eartha', [4, 0, 0])
    const ids = [...useMIMOStore.getState().users.keys()]
    s.removeUser(ids[1]) // remove User 2
    const names = [...useMIMOStore.getState().users.values()].map(u => u.displayName)
    expect(names).toEqual(['User 1', 'User 3'])
  })

  it('setFocusedUser changes focused user', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    s.addUser('duke', [2, 0, 0])
    const ids = [...useMIMOStore.getState().users.keys()]
    s.setFocusedUser(ids[1])
    expect(useMIMOStore.getState().focusedUserId).toBe(ids[1])
  })

  it('moveUser updates position', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    const id = [...useMIMOStore.getState().users.keys()][0]
    s.moveUser(id, [5, 0, -2])
    expect(useMIMOStore.getState().users.get(id)?.position).toEqual([5, 0, -2])
  })

  it('setUserResult updates sab and stats for a user', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    const id = [...useMIMOStore.getState().users.keys()][0]
    const sab = new Float32Array([1, 2, 3])
    const stats = { peak_sab: 10, p_abs_mw: 5, compliant: true } as any
    s.setUserResult(id, sab, stats)
    const user = useMIMOStore.getState().users.get(id)
    expect(user?.sabArray).toBe(sab)
    expect(user?.stats).toBe(stats)
    expect(user?.compliant).toBe(true)
  })

  it('setPrecoderType updates precoder', () => {
    useMIMOStore.getState().setPrecoderType('mmse')
    expect(useMIMOStore.getState().precoderType).toBe('mmse')
  })

  it('focusedUser selector returns the focused user state', () => {
    const s = useMIMOStore.getState()
    s.addUser('thelonious', [0, 0, 0])
    const focused = useMIMOStore.getState().focusedUser()
    expect(focused).not.toBeNull()
    expect(focused?.phantomName).toBe('thelonious')
  })

  it('focusedUser returns null when no users', () => {
    expect(useMIMOStore.getState().focusedUser()).toBeNull()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/user/worktrees/multi-user-3a/aegis-web && npx vitest run src/stores/__tests__/mimo.test.ts`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement the MIMO store**

Create `aegis-web/src/stores/mimo.ts`:

```typescript
import { create } from 'zustand'
import type { BufferGeometry } from 'three'
import type { ScenePos } from '@/api/coordinates'
import type { DosimetryStats, ArrayConfig, MIMOSummary } from '@/api/types'

export type PrecoderType = 'mrt' | 'zf' | 'mmse' | 'zf_exposure'

export interface UserMIMOState {
  userId: string
  displayName: string
  phantomName: string
  position: ScenePos
  orientation: number
  deviceOrientation: [number, number, number]
  bodyGeometry: BufferGeometry | null
  sabArray: Float32Array | null
  stats: DosimetryStats | null
  compliant: boolean | null
}

interface MIMOStore {
  enabled: boolean
  users: Map<string, UserMIMOState>
  focusedUserId: string | null
  controlledUserId: string | null
  precoderType: PrecoderType
  arrayConfig: ArrayConfig | null
  summaryStats: MIMOSummary | null
  showAllHeatmaps: boolean
  _nextUserNumber: number

  // Derived
  focusedUser: () => UserMIMOState | null

  // Actions
  setEnabled: (on: boolean) => void
  addUser: (phantom: string, position: ScenePos) => void
  removeUser: (id: string) => void
  setFocusedUser: (id: string) => void
  setControlledUser: (id: string) => void
  moveUser: (id: string, position: ScenePos) => void
  setUserOrientation: (id: string, orientation: number) => void
  setUserBodyGeometry: (id: string, geometry: BufferGeometry) => void
  setUserResult: (id: string, sab: Float32Array, stats: DosimetryStats) => void
  setPrecoderType: (type: PrecoderType) => void
  setArrayConfig: (config: ArrayConfig) => void
  setSummaryStats: (summary: MIMOSummary) => void
  setShowAllHeatmaps: (on: boolean) => void
  clearAllResults: () => void
  reset: () => void
}

const INITIAL_STATE = {
  enabled: false,
  users: new Map<string, UserMIMOState>(),
  focusedUserId: null as string | null,
  controlledUserId: null as string | null,
  precoderType: 'zf' as PrecoderType,
  arrayConfig: null as ArrayConfig | null,
  summaryStats: null as MIMOSummary | null,
  showAllHeatmaps: false,
  _nextUserNumber: 1,
}

export const useMIMOStore = create<MIMOStore>((set, get) => ({
  ...INITIAL_STATE,

  focusedUser: () => {
    const { users, focusedUserId } = get()
    if (!focusedUserId) return null
    return users.get(focusedUserId) ?? null
  },

  setEnabled: (on) => set({ enabled: on }),

  addUser: (phantom, position) => {
    const id = crypto.randomUUID()
    const num = get()._nextUserNumber
    const user: UserMIMOState = {
      userId: id,
      displayName: `User ${num}`,
      phantomName: phantom,
      position,
      orientation: 0,
      deviceOrientation: [0, 1, 0],
      bodyGeometry: null,
      sabArray: null,
      stats: null,
      compliant: null,
    }
    const users = new Map(get().users)
    users.set(id, user)
    const isFirst = users.size === 1
    set({
      users,
      _nextUserNumber: num + 1,
      ...(isFirst ? { focusedUserId: id, controlledUserId: id } : {}),
    })
  },

  removeUser: (id) => {
    const users = new Map(get().users)
    users.delete(id)
    const { focusedUserId, controlledUserId } = get()
    const nextId = users.size > 0 ? users.keys().next().value! : null
    set({
      users,
      focusedUserId: focusedUserId === id ? nextId : focusedUserId,
      controlledUserId: controlledUserId === id ? nextId : controlledUserId,
    })
  },

  setFocusedUser: (id) => set({ focusedUserId: id }),
  setControlledUser: (id) => set({ controlledUserId: id }),

  moveUser: (id, position) => {
    const users = new Map(get().users)
    const user = users.get(id)
    if (!user) return
    users.set(id, { ...user, position })
    set({ users })
  },

  setUserOrientation: (id, orientation) => {
    const users = new Map(get().users)
    const user = users.get(id)
    if (!user) return
    users.set(id, { ...user, orientation })
    set({ users })
  },

  setUserBodyGeometry: (id, geometry) => {
    const users = new Map(get().users)
    const user = users.get(id)
    if (!user) return
    users.set(id, { ...user, bodyGeometry: geometry })
    set({ users })
  },

  setUserResult: (id, sab, stats) => {
    const users = new Map(get().users)
    const user = users.get(id)
    if (!user) return
    users.set(id, {
      ...user,
      sabArray: sab,
      stats,
      compliant: stats.compliant ?? null,
    })
    set({ users })
  },

  setPrecoderType: (type) => set({ precoderType: type }),
  setArrayConfig: (config) => set({ arrayConfig: config }),
  setSummaryStats: (summary) => set({ summaryStats: summary }),
  setShowAllHeatmaps: (on) => set({ showAllHeatmaps: on }),

  clearAllResults: () => {
    const users = new Map(get().users)
    for (const [id, user] of users) {
      users.set(id, { ...user, sabArray: null, stats: null, compliant: null })
    }
    set({ users, summaryStats: null })
  },

  reset: () => set({ ...INITIAL_STATE, users: new Map() }),
}))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/user/worktrees/multi-user-3a/aegis-web && npx vitest run src/stores/__tests__/mimo.test.ts`
Expected: all 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/stores/mimo.ts aegis-web/src/stores/__tests__/mimo.test.ts
git commit -m "Add MIMO Zustand store with user lifecycle actions"
```

---

## Task 3: MIMO API client

**Files:**
- Create: `aegis-web/src/api/mimo.ts`
- Test: `aegis-web/src/api/__tests__/mimo.test.ts`

- [ ] **Step 1: Write failing tests for the API module**

Create `aegis-web/src/api/__tests__/mimo.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { buildMIMOComputePayload } from '../mimo'
import type { ScenePos } from '../coordinates'
import type { ArrayConfig, MIMOUserConfig } from '../types'

describe('MIMO API', () => {
  const array: ArrayConfig = {
    type: 'upa',
    n_h: 4,
    n_v: 4,
    d_h_wavelengths: 0.5,
    d_v_wavelengths: 0.5,
    position: [5, 3, 0] as ScenePos, // Y-up scene coords
    broadside: [-1, 0, 0],
  }

  const users: MIMOUserConfig[] = [
    { id: 'u1', phantom: 'thelonious', position: [0, 0, 0] as ScenePos, orientation: 0, device_offset: [0.25, 1.4, 0] },
    { id: 'u2', phantom: 'duke', position: [2, 0, -1] as ScenePos, orientation: 0.5, device_offset: [0.25, 1.4, 0] },
  ]

  it('converts scene positions to server positions', () => {
    const payload = buildMIMOComputePayload({
      array,
      users,
      freq_hz: 28e9,
      power_dbm: 60,
      precoder_type: 'zf',
    })
    // toServer swaps: [x, y, z] -> [x, -z, y]
    expect(payload.array.position).toEqual([5, 0, 3])
    expect(payload.users[0].position).toEqual([0, 0, 0])
    expect(payload.users[1].position).toEqual([2, 1, 0])
  })

  it('preserves non-position fields', () => {
    const payload = buildMIMOComputePayload({
      array,
      users,
      freq_hz: 28e9,
      power_dbm: 60,
      precoder_type: 'zf',
    })
    expect(payload.freq_hz).toBe(28e9)
    expect(payload.power_dbm).toBe(60)
    expect(payload.precoder_type).toBe('zf')
    expect(payload.users[0].phantom).toBe('thelonious')
    expect(payload.users[1].orientation).toBe(0.5)
  })

  it('includes changed field when provided', () => {
    const payload = buildMIMOComputePayload({
      array,
      users,
      freq_hz: 28e9,
      power_dbm: 60,
      precoder_type: 'zf',
      changed: { type: 'user_moved', user_id: 'u1' },
    })
    expect(payload.changed).toEqual({ type: 'user_moved', user_id: 'u1' })
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/user/worktrees/multi-user-3a/aegis-web && npx vitest run src/api/__tests__/mimo.test.ts`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement the MIMO API client**

Create `aegis-web/src/api/mimo.ts`:

```typescript
import type {
  ArrayConfig,
  MIMOUserConfig,
  MIMOComputeRequest,
  MIMOComputeResponse,
  MIMOSummary,
  DosimetryStats,
} from './types'
import { toServer, type ScenePos } from './coordinates'

/** Server-side payload (Z-up positions). */
interface MIMOServerPayload {
  array: Omit<ArrayConfig, 'position'> & { position: [number, number, number] }
  users: Array<Omit<MIMOUserConfig, 'position'> & { position: [number, number, number] }>
  freq_hz: number
  power_dbm: number
  precoder_type: string
  changed?: { type: string; user_id?: string }
}

/** Convert scene-coords payload to server-coords payload. */
export function buildMIMOComputePayload(req: MIMOComputeRequest): MIMOServerPayload {
  return {
    array: {
      ...req.array,
      position: toServer(req.array.position),
    },
    users: req.users.map(u => ({
      ...u,
      position: toServer(u.position),
    })),
    freq_hz: req.freq_hz,
    power_dbm: req.power_dbm,
    precoder_type: req.precoder_type,
    ...(req.changed ? { changed: req.changed } : {}),
  }
}

/** Trigger MIMO computation for all users. */
export async function computeMIMO(
  req: MIMOComputeRequest,
  signal?: AbortSignal,
): Promise<MIMOComputeResponse> {
  const payload = buildMIMOComputePayload(req)
  const res = await fetch('/api/mimo/compute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok) throw new Error(`MIMO compute failed: ${res.status}`)
  return res.json()
}

/** Fetch a single user's sab result as binary. */
export async function fetchMIMOResult(
  userId: string,
  signal?: AbortSignal,
): Promise<{ sab: Float32Array; stats: DosimetryStats }> {
  const resp = await fetch(`/api/mimo/result/${userId}`, { signal })
  if (!resp.ok) throw new Error(`MIMO result fetch failed: ${resp.status}`)
  const statsHeader = resp.headers.get('X-Stats')
  const stats: DosimetryStats = statsHeader ? JSON.parse(statsHeader) : {}
  const buf = await resp.arrayBuffer()
  const sab = new Float32Array(buf)
  return { sab, stats }
}

/** Fetch summary stats for all users. */
export async function fetchMIMOSummary(
  signal?: AbortSignal,
): Promise<MIMOSummary> {
  const resp = await fetch('/api/mimo/summary', { signal })
  if (!resp.ok) throw new Error(`MIMO summary fetch failed: ${resp.status}`)
  return resp.json()
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/user/worktrees/multi-user-3a/aegis-web && npx vitest run src/api/__tests__/mimo.test.ts`
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/api/mimo.ts aegis-web/src/api/__tests__/mimo.test.ts
git commit -m "Add MIMO API client with coordinate conversion"
```

---

## Task 4: BodyMeshInstance component (extract from BodyMesh)

**Files:**
- Create: `aegis-web/src/components/scene/BodyMeshInstance.tsx`
- Modify: `aegis-web/src/components/scene/BodyMesh.tsx`

This is the key refactor: extract the heatmap-painting and rendering logic from `BodyMesh` into a pure-props `BodyMeshInstance`. The existing `BodyMesh` becomes a thin wrapper that reads from the single-user store and delegates.

- [ ] **Step 1: Create BodyMeshInstance with explicit props**

Create `aegis-web/src/components/scene/BodyMeshInstance.tsx`:

```tsx
import { useRef, useEffect } from 'react'
import * as THREE from 'three'
import { useUIStore } from '@/stores/ui'
import { useSimulationStore } from '@/stores/simulation'
import { jetColor, gainTFromLinear, arrayMax } from '@/lib/colormap'
import type { DosimetryStats, ComplianceInfo } from '@/api/types'
import type { ScenePos } from '@/api/coordinates'
import PeakIndicator from './PeakIndicator'

/** Compliance color: green -> yellow -> orange -> red at thresholds 0.5, 0.8, 1.0 */
function complianceColor(ratio: number): [number, number, number] {
  ratio = Math.max(0, Math.min(1.5, ratio))
  if (ratio < 0.5) {
    return [0.29, 0.87, 0.50]
  } else if (ratio < 0.8) {
    const u = (ratio - 0.5) / 0.3
    return [0.29 + u * (0.98 - 0.29), 0.87 + u * (0.75 - 0.87), 0.50 + u * (0.15 - 0.50)]
  } else if (ratio < 1.0) {
    const u = (ratio - 0.8) / 0.2
    return [0.98, 0.75 - u * 0.30, 0.15 - u * 0.10]
  } else {
    return [0.97, 0.44, 0.44]
  }
}

export interface BodyMeshInstanceProps {
  geometry: THREE.BufferGeometry | null
  sabArray: Float32Array | null
  sabAveragedArray?: Float32Array | null
  sincArray?: Float32Array | null
  sab1cm2AveragedArray?: Float32Array | null
  stats?: DosimetryStats | null
  compliance?: ComplianceInfo | null
  position: ScenePos
  rotationY: number
  opacity?: number
  onClick?: () => void
}

export default function BodyMeshInstance({
  geometry,
  sabArray,
  sabAveragedArray,
  sincArray,
  sab1cm2AveragedArray,
  stats,
  compliance,
  position,
  rotationY,
  opacity = 1,
  onClick,
}: BodyMeshInstanceProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const wireframe = useUIStore(s => s.wireframe)
  const legendScale = useUIStore(s => s.legendScale)
  const dynamicRangeDb = useUIStore(s => s.dynamicRangeDb)
  const colormapLocked = useUIStore(s => s.colormapLocked)
  const colormapLockedMax = useUIStore(s => s.colormapLockedMax)
  const ratioMode = useUIStore(s => s.ratioMode)
  const displayQuantity = useSimulationStore(s => s.displayQuantity)

  // Pick data array based on display quantity (matches original BodyMesh logic)
  const arrayMap: Record<string, Float32Array | null> = {
    sab: sabArray,
    sab_4cm2: sabAveragedArray ?? null,
    sab_1cm2: sab1cm2AveragedArray ?? null,
    sinc_local: sincArray ?? null,
  }
  const dataArray = arrayMap[displayQuantity] ?? sabArray

  // Ratio mode: find limit from compliance checks (matches original logic)
  let isRatioMode = ratioMode && displayQuantity !== 'sab'
  let ratioLimit = 1.0
  if (isRatioMode && compliance?.checks) {
    const limitMap: Record<string, (c: { label: string }) => boolean> = {
      sab_4cm2: (c) => c.label.includes('4 cm'),
      sab_1cm2: (c) => c.label.includes('1 cm'),
      sinc_local: (c) => c.label.includes('S_inc') && c.label.includes('local'),
    }
    const finder = limitMap[displayQuantity]
    if (finder) {
      ratioLimit = compliance.checks.find(finder)?.limit ?? 20.0
    }
  }

  // Apply heatmap colors
  useEffect(() => {
    if (!geometry) return
    const colorAttr = geometry.getAttribute('color') as THREE.BufferAttribute
    if (!colorAttr) return

    if (!dataArray) {
      for (let i = 0; i < colorAttr.count; i++) {
        colorAttr.setXYZ(i, 0.5, 0.5, 0.5)
      }
    } else if (isRatioMode) {
      const nFaces = dataArray.length
      for (let f = 0; f < nFaces; f++) {
        const ratio = ratioLimit > 0 ? dataArray[f] / ratioLimit : 0
        const [r, g, b] = complianceColor(ratio)
        colorAttr.setXYZ(f * 3, r, g, b)
        colorAttr.setXYZ(f * 3 + 1, r, g, b)
        colorAttr.setXYZ(f * 3 + 2, r, g, b)
      }
    } else {
      const currentMax = arrayMax(dataArray)
      if (colormapLocked && colormapLockedMax == null) {
        useUIStore.getState().setColormapLockedMax(currentMax)
      }
      const maxSab = (colormapLocked && colormapLockedMax != null) ? colormapLockedMax : currentMax
      const nFaces = dataArray.length
      for (let f = 0; f < nFaces; f++) {
        let t: number
        if (legendScale === 'dB') {
          t = gainTFromLinear(dataArray[f], maxSab, dynamicRangeDb)
        } else {
          t = maxSab > 0 ? dataArray[f] / maxSab : 0
        }
        const [r, g, b] = jetColor(t)
        colorAttr.setXYZ(f * 3, r, g, b)
        colorAttr.setXYZ(f * 3 + 1, r, g, b)
        colorAttr.setXYZ(f * 3 + 2, r, g, b)
      }
    }
    colorAttr.needsUpdate = true
  }, [dataArray, isRatioMode, ratioLimit, geometry, legendScale, dynamicRangeDb, colormapLocked, colormapLockedMax])

  if (!geometry) return null

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      <mesh
        ref={meshRef}
        geometry={geometry}
        castShadow
        onClick={onClick}
      >
        <meshStandardMaterial
          vertexColors
          wireframe={wireframe}
          roughness={0.7}
          metalness={0.1}
          transparent={opacity < 1}
          opacity={opacity}
        />
      </mesh>
      <PeakIndicator />
    </group>
  )
}
```

- [ ] **Step 2: Refactor BodyMesh to delegate to BodyMeshInstance**

Replace the body of `aegis-web/src/components/scene/BodyMesh.tsx` with:

```tsx
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useBodyLoader } from '@/hooks/useBodyLoader'
import BodyMeshInstance from './BodyMeshInstance'

export default function BodyMesh() {
  useBodyLoader()

  const geometry = useSceneStore(s => s.bodyGeometry)
  const sabArray = useSimulationStore(s => s.sabArray)
  const sabAveragedArray = useSimulationStore(s => s.sabAveragedArray)
  const sincArray = useSimulationStore(s => s.sincArray)
  const sab1cm2AveragedArray = useSimulationStore(s => s.sab1cm2AveragedArray)
  const stats = useSimulationStore(s => s.stats)
  const compliance = useSimulationStore(s => s.compliance)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const bodyRotationY = useSimulationStore(s => s.bodyRotationY)

  return (
    <BodyMeshInstance
      geometry={geometry}
      sabArray={sabArray}
      sabAveragedArray={sabAveragedArray}
      sincArray={sincArray}
      sab1cm2AveragedArray={sab1cm2AveragedArray}
      stats={stats}
      compliance={compliance}
      position={bodyOffset}
      rotationY={bodyRotationY}
    />
  )
}
```

- [ ] **Step 3: Verify existing functionality is preserved**

Run: `cd /home/user/worktrees/multi-user-3a/aegis-web && npx tsc --noEmit`
Expected: no type errors

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/scene/BodyMeshInstance.tsx aegis-web/src/components/scene/BodyMesh.tsx
git commit -m "Extract BodyMeshInstance from BodyMesh for multi-body rendering"
```

---

## Task 5: AntennaArray 3D component

**Files:**
- Create: `aegis-web/src/components/scene/AntennaArray.tsx`

- [ ] **Step 1: Create the AntennaArray component**

Create `aegis-web/src/components/scene/AntennaArray.tsx`:

```tsx
import { useMemo, useRef, useEffect } from 'react'
import * as THREE from 'three'
import type { ArrayConfig } from '@/api/types'
import type { ScenePos } from '@/api/coordinates'

interface AntennaArrayProps {
  config: ArrayConfig
  freqHz: number
}

const ELEMENT_RADIUS = 0.03
const ELEMENT_COLOR = new THREE.Color(0.8, 0.2, 0.2)
const POLE_RADIUS = 0.04
const POLE_COLOR = new THREE.Color(0.4, 0.4, 0.4)
const ARROW_COLOR = new THREE.Color(1, 0.4, 0)

export default function AntennaArray({ config, freqHz }: AntennaArrayProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const nElements = config.n_h * config.n_v

  // Compute element positions in local coords (array-centered)
  const localPositions = useMemo(() => {
    const positions: THREE.Vector3[] = []
    const broadside = new THREE.Vector3(...config.broadside).normalize()

    // Build local coordinate frame: broadside is the normal,
    // h-axis and v-axis span the array plane
    const up = new THREE.Vector3(0, 1, 0)
    let hAxis = new THREE.Vector3().crossVectors(up, broadside).normalize()
    if (hAxis.length() < 0.01) {
      hAxis = new THREE.Vector3(1, 0, 0)
    }
    const vAxis = new THREE.Vector3().crossVectors(broadside, hAxis).normalize()

    const lambda = 3e8 / freqHz
    const dH = config.d_h_wavelengths * lambda
    const dV = config.d_v_wavelengths * lambda

    for (let iv = 0; iv < config.n_v; iv++) {
      for (let ih = 0; ih < config.n_h; ih++) {
        const oh = (ih - (config.n_h - 1) / 2) * dH
        const ov = (iv - (config.n_v - 1) / 2) * dV
        positions.push(
          new THREE.Vector3()
            .addScaledVector(hAxis, oh)
            .addScaledVector(vAxis, ov)
        )
      }
    }
    return positions
  }, [config.n_h, config.n_v, config.d_h_wavelengths, config.d_v_wavelengths, config.broadside, freqHz])

  // Update instanced mesh transforms
  useEffect(() => {
    if (!meshRef.current) return
    const dummy = new THREE.Object3D()
    for (let i = 0; i < localPositions.length; i++) {
      dummy.position.copy(localPositions[i])
      dummy.updateMatrix()
      meshRef.current.setMatrixAt(i, dummy.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  }, [localPositions])

  const sphereGeo = useMemo(() => new THREE.SphereGeometry(ELEMENT_RADIUS, 8, 8), [])

  // Pole: from ground to array center height
  const poleHeight = config.position[1]

  // Arrow direction for broadside
  const arrowDir = useMemo(
    () => new THREE.Vector3(...config.broadside).normalize(),
    [config.broadside],
  )

  return (
    <group position={config.position}>
      {/* Element spheres */}
      <instancedMesh
        ref={meshRef}
        args={[sphereGeo, undefined, nElements]}
      >
        <meshStandardMaterial color={ELEMENT_COLOR} />
      </instancedMesh>

      {/* Pole from ground to array center */}
      {poleHeight > 0 && (
        <mesh position={[0, -poleHeight / 2, 0]}>
          <cylinderGeometry args={[POLE_RADIUS, POLE_RADIUS, poleHeight, 8]} />
          <meshStandardMaterial color={POLE_COLOR} />
        </mesh>
      )}

      {/* Broadside arrow */}
      <arrowHelper
        args={[arrowDir, new THREE.Vector3(0, 0, 0), 0.5, ARROW_COLOR.getHex(), 0.15, 0.08]}
      />
    </group>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `cd /home/user/worktrees/multi-user-3a/aegis-web && npx tsc --noEmit`
Expected: no type errors

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/scene/AntennaArray.tsx
git commit -m "Add AntennaArray component with InstancedMesh UPA grid"
```

---

## Task 6: useActiveSimulation adaptor hook

**Files:**
- Create: `aegis-web/src/hooks/useActiveSimulation.ts`

This hook is the bridge that lets existing HUD components (StatsCard, CompliancePanel, ColorLegend) work in MIMO mode without changes. It returns the same shape as the single-user store fields.

- [ ] **Step 1: Create the adaptor hook**

Create `aegis-web/src/hooks/useActiveSimulation.ts`:

```typescript
import { useSimulationStore } from '@/stores/simulation'
import { useMIMOStore } from '@/stores/mimo'
import { useSceneStore } from '@/stores/scene'
import type { ScenePos } from '@/api/coordinates'
import type { DosimetryStats, ComplianceInfo } from '@/api/types'
import type { BufferGeometry } from 'three'

export interface ActiveSimulation {
  sabArray: Float32Array | null
  sabAveragedArray: Float32Array | null
  sincArray: Float32Array | null
  sab1cm2AveragedArray: Float32Array | null
  stats: DosimetryStats | null
  compliance: ComplianceInfo | null
  bodyGeometry: BufferGeometry | null
  bodyOffset: ScenePos
  bodyRotationY: number
}

export function useActiveSimulation(): ActiveSimulation {
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const focusedUserId = useMIMOStore(s => s.focusedUserId)
  const focusedUser = useMIMOStore(s =>
    s.focusedUserId ? s.users.get(s.focusedUserId) ?? null : null
  )

  // Single-user fallback values
  const singleSab = useSimulationStore(s => s.sabArray)
  const singleSabAvg = useSimulationStore(s => s.sabAveragedArray)
  const singleSinc = useSimulationStore(s => s.sincArray)
  const singleSab1cm2 = useSimulationStore(s => s.sab1cm2AveragedArray)
  const singleStats = useSimulationStore(s => s.stats)
  const singleCompliance = useSimulationStore(s => s.compliance)
  const singleGeometry = useSceneStore(s => s.bodyGeometry)
  const singleOffset = useSimulationStore(s => s.bodyOffset)
  const singleRotation = useSimulationStore(s => s.bodyRotationY)

  if (mimoEnabled && focusedUser) {
    return {
      sabArray: focusedUser.sabArray,
      sabAveragedArray: null, // MIMO compute returns only sab for now
      sincArray: null,
      sab1cm2AveragedArray: null,
      stats: focusedUser.stats,
      compliance: focusedUser.stats?.compliance ?? null,
      bodyGeometry: focusedUser.bodyGeometry,
      bodyOffset: focusedUser.position,
      bodyRotationY: focusedUser.orientation,
    }
  }

  return {
    sabArray: singleSab,
    sabAveragedArray: singleSabAvg,
    sincArray: singleSinc,
    sab1cm2AveragedArray: singleSab1cm2,
    stats: singleStats,
    compliance: singleCompliance,
    bodyGeometry: singleGeometry,
    bodyOffset: singleOffset,
    bodyRotationY: singleRotation,
  }
}
```

- [ ] **Step 2: Type-check**

Run: `cd /home/user/worktrees/multi-user-3a/aegis-web && npx tsc --noEmit`
Expected: no type errors

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/hooks/useActiveSimulation.ts
git commit -m "Add useActiveSimulation adaptor hook for single-user/MIMO dispatch"
```

---

## Task 7: Update SceneRoot for MIMO rendering

**Files:**
- Modify: `aegis-web/src/components/scene/SceneRoot.tsx`

This is the integration task. SceneRoot conditionally renders multiple BodyMeshInstance + AntennaArray when MIMO is enabled, or the existing single-user components when disabled.

- [ ] **Step 1: Add MIMO imports to SceneRoot**

Add these imports at the top of `SceneRoot.tsx` (after the existing scene component imports):

```typescript
import { useMIMOStore } from '@/stores/mimo'
import BodyMeshInstance from './BodyMeshInstance'
import AntennaArrayViz from './AntennaArray'
```

- [ ] **Step 2: Create MIMOScene component inside SceneRoot.tsx**

Add a new component inside the file, before the main `SceneRoot` export:

```tsx
function MIMOScene() {
  const users = useMIMOStore(s => s.users)
  const focusedUserId = useMIMOStore(s => s.focusedUserId)
  const showAllHeatmaps = useMIMOStore(s => s.showAllHeatmaps)
  const arrayConfig = useMIMOStore(s => s.arrayConfig)
  const setFocusedUser = useMIMOStore(s => s.setFocusedUser)
  const freqGhz = useSimulationStore(s => s.freqGhz)

  return (
    <>
      {[...users.values()].map(user => (
        <BodyMeshInstance
          key={user.userId}
          geometry={user.bodyGeometry}
          sabArray={showAllHeatmaps ? user.sabArray : (
            user.userId === focusedUserId ? user.sabArray : null
          )}
          position={user.position}
          rotationY={user.orientation}
          opacity={user.userId === focusedUserId ? 1.0 : 0.7}
          onClick={() => setFocusedUser(user.userId)}
        />
      ))}
      {arrayConfig && <AntennaArrayViz config={arrayConfig} freqHz={freqGhz * 1e9} />}
    </>
  )
}
```

- [ ] **Step 3: Update SceneRoot JSX to conditionally render MIMO or single-user**

In the `SceneRoot` component, add MIMO state reading:

```typescript
const mimoEnabled = useMIMOStore(s => s.enabled)
```

Then replace the section that renders `<BodyMesh />`, `<Antenna />`, and `<DistanceLine />` (approximately lines 222-226) with:

```tsx
{mimoEnabled ? (
  <MIMOScene />
) : (
  <>
    <BodyMesh />
    <Antenna />
    <DistanceLine />
  </>
)}
```

Keep `<RayPaths />`, `<DosimetryController />`, `<PhysicsController />`, etc. outside the conditional (they work in both modes or are single-user-only and harmless when inactive).

- [ ] **Step 4: Type-check**

Run: `cd /home/user/worktrees/multi-user-3a/aegis-web && npx tsc --noEmit`
Expected: no type errors

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/components/scene/SceneRoot.tsx
git commit -m "Wire MIMO multi-body rendering into SceneRoot"
```

---

## Task 8: Run full test suite and lint

**Files:** none (verification only)

- [ ] **Step 1: Run all frontend tests**

Run: `cd /home/user/worktrees/multi-user-3a/aegis-web && npx vitest run`
Expected: all tests pass (existing + new MIMO store + MIMO API tests)

- [ ] **Step 2: Run TypeScript type-check**

Run: `cd /home/user/worktrees/multi-user-3a/aegis-web && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 3: Run backend lint (ruff) to make sure no Python was accidentally broken**

Run: `cd /home/user/worktrees/multi-user-3a && python -m ruff check src/ tests/`
Expected: no errors

- [ ] **Step 4: Final commit if any fixups were needed**

```bash
git add -p  # review changes
git commit -m "Fix lint/type issues from Phase 3a integration"
```

---

## Dependency graph

```
Task 1 (types) ──┬──> Task 2 (store) ──┐
                 │                      ├──> Task 6 (adaptor hook) ──> Task 7 (SceneRoot)
                 ├──> Task 3 (API)      │                                    │
                 │                      │                                    v
                 ├──> Task 4 (BodyMeshInstance) ─────────────────────> Task 7 (SceneRoot)
                 │                                                           │
                 └──> Task 5 (AntennaArray) ─────────────────────────> Task 7 (SceneRoot)
                                                                             │
                                                                             v
                                                                      Task 8 (verify)
```

Tasks 2, 3, 4, 5 can run in parallel after Task 1. Task 6 needs Task 2. Task 7 needs Tasks 4, 5, 6. Task 8 is the final verification.
