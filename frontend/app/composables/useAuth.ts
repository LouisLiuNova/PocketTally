import type { FetchError } from 'ofetch'

export interface AuthSession {
  id: string
  username: string
  current: boolean
  createdAt: string
  lastSeenAt: string
  absoluteExpiresAt: string
}

const sessionKey = 'pockettally-auth-session'
const initializedKey = 'pockettally-auth-initialized'

export function useAuth() {
  const session = useState<AuthSession | null>(sessionKey, () => null)
  const initialized = useState(initializedKey, () => false)
  const api = useApi()

  async function refresh() {
    try {
      session.value = await api<AuthSession>('/api/v1/auth/session')
    } catch (error) {
      if ((error as FetchError)?.statusCode === 401) session.value = null
      else throw error
    } finally {
      initialized.value = true
    }
    return session.value
  }

  async function login(username: string, password: string) {
    session.value = await api<AuthSession>('/api/v1/auth/login', {
      method: 'POST',
      body: { username, password },
    })
    initialized.value = true
    return session.value
  }

  async function logout() {
    try {
      await api('/api/v1/auth/logout', { method: 'POST' })
    } finally {
      session.value = null
      initialized.value = true
    }
  }

  function clear() {
    session.value = null
    initialized.value = true
  }

  return { session, initialized, refresh, login, logout, clear }
}
