import { create } from 'zustand'

export type NotificationLevel = 'error' | 'warning' | 'info'

export interface Notification {
  id: string
  level: NotificationLevel
  message: string
  timestamp: number
}

interface NotificationStore {
  notifications: Notification[]
  addNotification: (level: NotificationLevel, message: string) => void
  dismiss: (id: string) => void
}

let nextId = 0

export const useNotificationStore = create<NotificationStore>((set) => ({
  notifications: [],
  addNotification: (level, message) => {
    const id = String(++nextId)
    set((state) => ({
      notifications: [...state.notifications.slice(-4), { id, level, message, timestamp: Date.now() }],
    }))
  },
  dismiss: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
}))
