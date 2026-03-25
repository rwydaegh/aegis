import { useState, useEffect, type ReactNode } from 'react'
import { useAuth } from '@/hooks/useAuth'

interface LoginGateProps {
  children: ReactNode
}

export default function LoginGate({ children }: LoginGateProps) {
  const { authenticated, error, login } = useAuth()
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  // Probe session on mount: GET /api/auth returns 200 if already authenticated
  useEffect(() => {
    fetch('/api/auth')
      .then((res) => res.json())
      .then((data) => {
        if (data.authenticated) {
          useAuth.setState({
            authenticated: true,
            expiresAt: data.expires_at ? new Date(data.expires_at) : null,
          })
        } else {
          useAuth.setState({ authenticated: false })
        }
      })
      .catch(() => {
        useAuth.setState({ authenticated: false })
      })
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    await login(password)
    setLoading(false)
  }

  // null = unknown (waiting for probe to resolve)
  if (authenticated === null) {
    return (
      <div className="h-screen w-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-muted border-t-primary rounded-full animate-spin mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">Connecting...</p>
        </div>
      </div>
    )
  }

  if (authenticated === false) {
    return (
      <div className="h-screen w-screen bg-background flex items-center justify-center">
        <div className="w-full max-w-sm mx-4">
          <div className="bg-card border border-border rounded-xl p-8 shadow-lg">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold tracking-wider text-heading mb-1">AEGIS</h1>
              <p className="text-muted-foreground text-sm">Enter password to continue</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                autoFocus
                disabled={loading}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary disabled:opacity-50"
              />

              {error && (
                <p className="text-destructive text-sm text-center">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading || password.length === 0}
                className="w-full py-2 px-4 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                    Authenticating...
                  </span>
                ) : (
                  'Enter'
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    )
  }

  // authenticated === true
  return <>{children}</>
}
