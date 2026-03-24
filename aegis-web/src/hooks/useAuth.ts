import { create } from 'zustand'
import { login as apiLogin } from '@/api/auth'

interface AuthStore {
  authenticated: boolean | null
  expiresAt: Date | null
  error: string | null
  login: (password: string) => Promise<void>
  logout: () => void
  isExpired: () => boolean
}

export const useAuth = create<AuthStore>((set, get) => ({
  // null = unknown (waiting for first API call to determine if auth is required)
  authenticated: null,
  expiresAt: null,
  error: null,

  login: async (password: string) => {
    set({ error: null })
    try {
      const resp = await apiLogin(password)
      set({
        authenticated: true,
        expiresAt: new Date(resp.expires_at),
        error: null,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Authentication failed'
      set({ error: message })
    }
  },

  logout: () => set({ authenticated: false, expiresAt: null }),

  isExpired: () => {
    const { expiresAt } = get()
    if (!expiresAt) return false
    return expiresAt < new Date()
  },
}))
