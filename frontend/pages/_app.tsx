// pages/_app.tsx
// Entrypoint de Next.js: Tailwind, Chakra UI, React Query y protección básica de rutas

import '../styles/globals.css'
import React, { useEffect, useMemo } from 'react'
import { ChakraProvider } from '@chakra-ui/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '@contexts/AuthContext'
import MainLayout from '@layouts/MainLayout'
import { theme } from '@styles/theme'
import type { AppProps } from 'next/app'
import { useRouter } from 'next/router'

// Un único QueryClient para toda la app
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

/** Componente contenedor que aplica las redirecciones una vez Auth está listo */
function AppShell({ Component, pageProps }: AppProps) {
  const router = useRouter()
  const { auth, isReady } = useAuth()

  const isLogin = router.pathname === '/login'
  const protectedRoutes = useMemo(() => ['/', '/clients', '/purchases', '/stock'], [])

  useEffect(() => {
    if (!isReady) return // evita parpadeos: espera a hidratar localStorage

    const hasToken = Boolean(auth?.token)

    // No autenticado intentando entrar en ruta protegida → login
    if (!hasToken && protectedRoutes.includes(router.pathname)) {
      router.replace('/login')
      return
    }

    // Autenticado en /login → dashboard
    if (hasToken && isLogin) {
      router.replace('/')
    }
  }, [isReady, auth?.token, router.pathname, isLogin, protectedRoutes, router])

  // Mientras no esté listo el estado de auth, muestra un placeholder ligero
  if (!isReady) return null

  const PageWithLayout = isLogin
    ? Component
    : (props: any) => (
        <MainLayout>
          <Component {...props} />
        </MainLayout>
      )

  return <PageWithLayout {...pageProps} />
}

export default function App(props: AppProps) {
  return (
    <ChakraProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AppShell {...props} />
        </AuthProvider>
      </QueryClientProvider>
    </ChakraProvider>
  )
}
