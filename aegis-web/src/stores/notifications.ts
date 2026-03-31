import { create } from 'zustand'

export type NotificationLevel = 'error' | 'warning' | 'info'

export interface Notification {
  id: string
  level: NotificationLevel
  message: string
  detail?: string
  timestamp: number
}

interface NotificationStore {
  notifications: Notification[]
  addNotification: (level: NotificationLevel, message: string, detail?: string) => void
  dismiss: (id: string) => void
  dismissByLevel: (level: NotificationLevel) => void
}

let nextId = 0

const DEDUP_WINDOW_MS = 3000

export const useNotificationStore = create<NotificationStore>((set, get) => ({
  notifications: [],
  addNotification: (level, message, detail) => {
    const now = Date.now()
    const existing = get().notifications
    // De-duplicate: skip if an identical notification was added within the window
    if (existing.some(n => n.level === level && n.message === message && now - n.timestamp < DEDUP_WINDOW_MS)) {
      return
    }
    const id = String(++nextId)
    set((state) => ({
      notifications: [...state.notifications.slice(-4), { id, level, message, detail, timestamp: now }],
    }))
  },
  dismiss: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
  dismissByLevel: (level) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.level !== level),
    })),
}))
