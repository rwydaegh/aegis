export interface AuthResponse {
  ok: boolean
  expires_at: string
  session_id: string
}

export async function login(password: string): Promise<AuthResponse> {
  const resp = await fetch('/api/auth', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  if (!resp.ok) {
    const data = await resp.json()
    throw new Error(data.error || 'Authentication failed')
  }
  return resp.json()
}
