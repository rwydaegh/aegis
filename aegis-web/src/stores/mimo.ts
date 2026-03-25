import { create } from 'zustand'
import { useSimulationStore } from './simulation'
import { useSceneStore } from './scene'
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
    if (!arrayConfig) {
      const antennaPos = useSimulationStore.getState().antennaPos
      arrayConfig = {
        type: 'upa' as const,
        n_h: 4, n_v: 4,
        d_h_wavelengths: 0.5, d_v_wavelengths: 0.5,
        position: antennaPos ?? [5, 2, 3],
        broadside: [-1, 0, 0] as [number, number, number],
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
    set({
      users,
      _nextUserNumber: num + 1,
      _configVersion: get()._configVersion + 1,
      ...(isFirst ? { focusedUserId: id, controlledUserId: id } : {}),
    })
  },

  removeUser: (id) => {
    const users = new Map(get().users)
    const removed = users.get(id)
    removed?.bodyGeometry?.dispose()
    users.delete(id)
    const { focusedUserId, controlledUserId, precoderType, arrayConfig } = get()
    const nextId = users.size > 0 ? users.keys().next().value! : null
    // Fall back to MRT if ZF/MMSE becomes infeasible (M < K)
    const nElements = arrayConfig ? arrayConfig.n_h * arrayConfig.n_v : 0
    const needsFallback = precoderType !== 'mrt' && nElements > 0 && nElements < users.size
    set({
      users,
      _configVersion: get()._configVersion + 1,
      focusedUserId: focusedUserId === id ? nextId : focusedUserId,
      controlledUserId: controlledUserId === id ? nextId : controlledUserId,
      ...(needsFallback ? { precoderType: 'mrt' as PrecoderType } : {}),
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

  reset: () => {
    // Dispose all body geometries to free GPU memory
    for (const user of get().users.values()) {
      user.bodyGeometry?.dispose()
    }
    set({ ...INITIAL_STATE, users: new Map() })
  },
}))
