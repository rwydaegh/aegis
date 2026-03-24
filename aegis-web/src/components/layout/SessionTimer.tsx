import { useEffect, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'

function formatRemaining(expiresAt: Date): string {
  const ms = expiresAt.getTime() - Date.now()
  if (ms <= 0) return '0m'
  const totalMinutes = Math.ceil(ms / 60_000)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

export default function SessionTimer() {
  const { authenticated, expiresAt } = useAuth()
  const [, setTick] = useState(0)

  useEffect(() => {
    if (!authenticated || !expiresAt) return
    const id = setInterval(() => setTick((t) => t + 1), 60_000)
    return () => clearInterval(id)
  }, [authenticated, expiresAt])

  if (!authenticated || !expiresAt) return null

  const msRemaining = expiresAt.getTime() - Date.now()
  const warningColor = msRemaining < 10 * 60_000

  return (
    <span
      className={
        warningColor
          ? 'text-xs font-mono text-amber-400'
          : 'text-xs font-mono text-muted-foreground'
      }
    >
      Session: {formatRemaining(expiresAt)}
    </span>
  )
}
