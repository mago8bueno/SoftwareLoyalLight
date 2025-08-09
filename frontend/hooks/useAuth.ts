// hooks/useAuth.ts
// Custom React hook para exponer AuthContext de forma tipada
// - Acceso a usuario autenticado y token
// - Funciones signIn y signOut

import { useContext } from 'react';
import AuthContext from '@contexts/AuthContext';

/**
 * useAuth
 * @returns {
 *   auth: { token: string; user: { name: string } } | null,
 *   signIn: (email: string, password: string) => Promise<void>,
 *   signOut: () => void
 * }
 */
export function useAuth() {
  const { auth, signIn, signOut } = useContext(AuthContext);
  return { auth, signIn, signOut };
}
