import { create } from 'zustand'
import { useSimulationStore } from './simulation'
import { useSceneStore } from './scene'
import { useNotificationStore } from './notifications'
import type { BufferGeometry } from 'three'
import type { ScenePos } from '@/api/coordinates'
import type { DosimetryStats, ArrayConfig, MIMOSummary, ElementPattern } from '@/api/types'

export type PrecoderType = 'mrt' | 'zf' | 'mmse' | 'zf_exposure'

const DEFAULT_FOCUS_POINT: [number, number, number] = [0, 1.0, 0]

/** Compute broadside = normalize(focusPoint - position), with safe fallback. */
function deriveBroadside(
  focusPoint: [number, number, number],
  position: [number, number, number],
): [number, number, number] {
  const dx = focusPoint[0] - position[0]
  const dy = focusPoint[1] - position[1]
  const dz = focusPoint[2] - position[2]
  const len = Math.sqrt(dx * dx + dy * dy + dz * dz)
  if (len < 1e-6) return [-1, 0, 0]
  return [dx / len, dy / len, dz / len]
}

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
  focusPoint: [number, number, number]
  summaryStats: MIMOSummary | null
  precoderWeights: { real: number[][]; imag: number[][] } | null
  showAllHeatmaps: boolean
  showArrayPattern: boolean
  _nextUserNumber: number
  _configVersion: number

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
  setFocusPoint: (p: [number, number, number]) => void
  setSummaryStats: (summary: MIMOSummary) => void
  setPrecoderWeights: (w: { real: number[][]; imag: number[][] } | null) => void
  setShowAllHeatmaps: (on: boolean) => void
  setShowArrayPattern: (on: boolean) => void
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
  focusPoint: DEFAULT_FOCUS_POINT as [number, number, number],
  summaryStats: null as MIMOSummary | null,
  precoderWeights: null as { real: number[][]; imag: number[][] } | null,
  showAllHeatmaps: false,
  showArrayPattern: true,
  _nextUserNumber: 1,
  _configVersion: 0,
}

export const useMIMOStore = create<MIMOStore>((set, get) => ({
  ...INITIAL_STATE,

  focusedUser: () => {
    const { users, focusedUserId } = get()
    if (!focusedUserId) return null
    return users.get(focusedUserId) ?? null
  },

  setEnabled: (on) => {
    if (!on) {
      set({ enabled: false })
      return
    }

    // Build array config if first time enabling
    let arrayConfig = get().arrayConfig
    const fp = get().focusPoint
    if (!arrayConfig) {
      const antennaPos = useSimulationStore.getState().antennaPos
      // Single-antenna antennaPos is the click point (ground level).
      // The MIMO panel position is the antenna center, so add pole height.
      const poleH = useSceneStore.getState().viewerConfig?.antenna?.pole_height ?? 2
      const pos: [number, number, number] = antennaPos
        ? [antennaPos[0], antennaPos[1] + poleH, antennaPos[2]]
        : [5, 2, 3]
      arrayConfig = {
        type: 'upa' as const,
        n_h: 4, n_v: 4,
        d_h_wavelengths: 0.5, d_v_wavelengths: 0.5,
        position: pos,
        broadside: deriveBroadside(fp, pos),
        element_pattern: 'patch' as ElementPattern,
      }
    }

    // Auto-add current phantom as User 1 if no users exist
    if (get().users.size === 0) {
      const { bodyOffset, bodyRotationY } = useSimulationStore.getState()
      const bodyName = useSceneStore.getState().bodyName || 'thelonious'
      const id = crypto.randomUUID()
      const num = get()._nextUserNumber
      const user: UserMIMOState = {
        userId: id,
        displayName: `User ${num}`,
        phantomName: bodyName,
        position: bodyOffset,
        orientation: bodyRotationY,
        deviceOrientation: [0, 1, 0],
        bodyGeometry: null,
        sabArray: null,
        stats: null,
        compliant: null,
      }
      const users = new Map(get().users)
      users.set(id, user)
      set({
        enabled: true,
        arrayConfig,
        users,
        _nextUserNumber: num + 1,
        _configVersion: get()._configVersion + 1,
        focusedUserId: id,
        controlledUserId: id,
      })
    } else {
      set({ enabled: true, arrayConfig })
    }
  },

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
    // Fall back to MRT if adding this user makes ZF/MMSE infeasible (K > M)
    const { precoderType, arrayConfig } = get()
    const nElements = arrayConfig ? arrayConfig.n_h * arrayConfig.n_v : 0
    const needsFallback = precoderType !== 'mrt' && nElements > 0 && nElements < users.size
    if (needsFallback) {
      useNotificationStore.getState().addNotification(
        'warning',
        `Switched to MRT precoder (${precoderType.toUpperCase()} requires M \u2265 K)`,
      )
    }
    set({
      users,
      _nextUserNumber: num + 1,
      _configVersion: get()._configVersion + 1,
      ...(isFirst ? { focusedUserId: id, controlledUserId: id } : {}),
      ...(needsFallback ? { precoderType: 'mrt' as PrecoderType } : {}),
    })
  },

  removeUser: (id) => {
    const users = new Map(get().users)
    const removed = users.get(id)
    removed?.bodyGeometry?.dispose()
    users.delete(id)
    const { focusedUserId, controlledUserId } = get()
    const nextId = users.size > 0 ? users.keys().next().value! : null
    set({
      users,
      _configVersion: get()._configVersion + 1,
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
    set({ users, _configVersion: get()._configVersion + 1 })
  },

  setUserOrientation: (id, orientation) => {
    const users = new Map(get().users)
    const user = users.get(id)
    if (!user) return
    users.set(id, { ...user, orientation })
    set({ users, _configVersion: get()._configVersion + 1 })
  },

  setUserBodyGeometry: (id, geometry) => {
    const users = new Map(get().users)
    const user = users.get(id)
    if (!user) return
    user.bodyGeometry?.dispose()
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
  setArrayConfig: (config) => {
    const fp = get().focusPoint
    const broadside = deriveBroadside(fp, config.position)
    const { precoderType, users } = get()
    const nElements = config.n_h * config.n_v
    const needsFallback =
      precoderType !== 'mrt' && nElements > 0 && nElements < users.size
    if (needsFallback) {
      useNotificationStore.getState().addNotification(
        'warning',
        `Switched to MRT precoder (${precoderType.toUpperCase()} requires M \u2265 K)`,
      )
    }
    set({
      arrayConfig: { ...config, broadside },
      _configVersion: get()._configVersion + 1,
      ...(needsFallback ? { precoderType: 'mrt' as PrecoderType } : {}),
    })
  },
  setFocusPoint: (fp) => {
    const cfg = get().arrayConfig
    if (!cfg) { set({ focusPoint: fp }); return }
    const broadside = deriveBroadside(fp, cfg.position)
    set({ focusPoint: fp, arrayConfig: { ...cfg, broadside }, _configVersion: get()._configVersion + 1 })
  },
  setSummaryStats: (summary) => set({ summaryStats: summary }),
  setPrecoderWeights: (w) => set({ precoderWeights: w }),
  setShowAllHeatmaps: (on) => set({ showAllHeatmaps: on }),
  setShowArrayPattern: (on) => set({ showArrayPattern: on }),

  clearAllResults: () => {
    const users = new Map(get().users)
    for (const [id, user] of users) {
      users.set(id, { ...user, sabArray: null, stats: null, compliant: null })
    }
    set({ users, summaryStats: null })
  },

  reset: () => {
    // Dispose all body geometries to free GPU memory
    for (const user of get().users.values()) {
      user.bodyGeometry?.dispose()
    }
    set({ ...INITIAL_STATE, users: new Map() })
  },
}))
