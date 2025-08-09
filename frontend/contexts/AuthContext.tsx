// contexts/AuthContext.tsx
// Contexto de autenticación con hidratación desde localStorage, flag isReady y sync entre pestañas.

import {
  createContext,
  useState,
  useEffect,
  ReactNode,
  useContext,
} from 'react'
import { useRouter } from 'next/router'
import { login as apiLogin, type LoginResponse } from '@services/auth'

/** Estado de autenticación que guardamos en memoria y localStorage */
export type Auth = {
  token: string
  user?: any // opcional por compatibilidad con distintos backends
}

type AuthContextValue = {
  auth: Auth | null
  isReady: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue>({
  auth: null,
  isReady: false,
  signIn: async () => {},
  signOut: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<Auth | null>(null)
  const [isReady, setIsReady] = useState(false)
  const router = useRouter()

  // Hidratar desde localStorage (solo en cliente) y marcar isReady
  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      const raw = localStorage.getItem('auth')
      if (raw) {
        const parsed = JSON.parse(raw) as Auth
        // ✅ valida que exista un token no vacío
        if (parsed && typeof parsed.token === 'string' && parsed.token.trim().length > 0) {
          setAuth(parsed)
        } else {
          localStorage.removeItem('auth')
        }
      }
    } catch {
      localStorage.removeItem('auth')
    }
    setIsReady(true)
  }, [])

  // Sincroniza logout/login entre pestañas
  useEffect(() => {
    if (typeof window === 'undefined') return
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'auth') {
        if (e.newValue) {
          try {
            const parsed = JSON.parse(e.newValue) as Auth
            if (parsed?.token) setAuth(parsed)
          } catch {
            setAuth(null)
          }
        } else {
          setAuth(null)
        }
      }
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const signIn = async (email: string, password: string) => {
    try {
      // services/auth.login espera { email, password }
      const resp: LoginResponse = await apiLogin({ email, password })
      const nextAuth: Auth = { token: resp.token, user: resp.user }
      setAuth(nextAuth)
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth', JSON.stringify(nextAuth))
      }
      await router.push('/')
    } catch (err) {
      // 🔁 re-lanza para que login.tsx muestre mensajes por status
      throw err
    }
  }

  const signOut = () => {
    setAuth(null)
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth')
    }
    router.push('/login')
  }

  return (
    <AuthContext.Provider value={{ auth, isReady, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

/** Helper para consumir el contexto con tipado */
export function useAuth() {
  return useContext(AuthContext)
}

export default AuthContext
