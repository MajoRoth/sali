import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { isSupabaseConfigured, supabase } from './supabase'

export interface AuthUser {
  id: string
  email: string | null
  name: string | null
  avatarUrl: string | null
}

interface AuthState {
  user: AuthUser | null
  /** True until the initial session lookup settles. */
  loading: boolean
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

const LOCAL_USER_KEY = 'sali.localUser'

/** Stand-in account used only while Supabase is unconfigured. */
function readLocalUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(LOCAL_USER_KEY)
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!supabase) {
      setUser(readLocalUser())
      setLoading(false)
      return
    }

    supabase.auth.getSession().then(({ data }) => {
      setUser(toAuthUser(data.session?.user))
      setLoading(false)
    })

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(toAuthUser(session?.user))
      setLoading(false)
    })
    return () => sub.subscription.unsubscribe()
  }, [])

  const signInWithGoogle = async () => {
    if (!supabase) {
      // Local mode: fabricate a session so the gated flow stays testable.
      const fake: AuthUser = {
        id: 'local-user',
        email: 'local@sali.dev',
        name: 'משתמש מקומי',
        avatarUrl: null,
      }
      localStorage.setItem(LOCAL_USER_KEY, JSON.stringify(fake))
      setUser(fake)
      return
    }
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
  }

  const signOut = async () => {
    if (!supabase) {
      localStorage.removeItem(LOCAL_USER_KEY)
      setUser(null)
      return
    }
    await supabase.auth.signOut()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, signInWithGoogle, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

function toAuthUser(u: { id: string; email?: string; user_metadata?: Record<string, unknown> } | undefined) {
  if (!u) return null
  const meta = u.user_metadata ?? {}
  return {
    id: u.id,
    email: u.email ?? null,
    name: (meta.full_name as string) ?? (meta.name as string) ?? null,
    avatarUrl: (meta.avatar_url as string) ?? null,
  }
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

export { isSupabaseConfigured }
