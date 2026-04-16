import { useEnvironmentStore } from '@/stores/environment'

export function ErrorMessage() {
  const error = useEnvironmentStore((s) => s.error)
  if (!error) return null

  return (
    <p className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1.5">
      {error}
    </p>
  )
}
