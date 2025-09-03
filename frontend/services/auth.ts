// services/auth.ts - CORREGIDO
import { fetcher } from './fetcher';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface BackendLoginResponseA {
  access_token: string;
  token_type?: string;
  user?: any;
}

export interface BackendLoginResponseB {
  token: string;
  user?: any;
}

export type LoginResponse = {
  token: string;
  user?: any;
};

/**
 * POST /auth/login/
 * Normaliza la respuesta del backend y PERSISTE en localStorage
 */
export async function login(payload: LoginPayload): Promise<LoginResponse> {
  try {
    const { data } = await fetcher.post<BackendLoginResponseA | BackendLoginResponseB>(
      '/auth/login/', 
      payload,
    );

    const token =
      (data as BackendLoginResponseA).access_token ?? (data as BackendLoginResponseB).token;

    if (!token) {
      console.error('[auth.login] Respuesta inesperada del backend:', data);
      throw new Error('Respuesta de login no válida (falta token)');
    }

    const user = (data as any).user;
    
    // ✅ CRÍTICO: Persistir en localStorage con formato esperado por fetcher.ts
    const authData = {
      access_token: token,
      token_type: (data as BackendLoginResponseA).token_type || 'bearer',
      user: user
    };
    
    localStorage.setItem('auth', JSON.stringify(authData));
    console.log('[auth] ✅ Token guardado en localStorage');
    
    return { token, user };
    
  } catch (error: any) {
    console.error('[auth] Error en login:', {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data
    });
    
    // Limpiar cualquier dato corrupto
    localStorage.removeItem('auth');
    throw error;
  }
}

/**
 * Logout: limpia localStorage y redirige
 */
export function logout() {
  localStorage.removeItem('auth');
  window.location.href = '/login';
}

/**
 * Verifica si el usuario está autenticado
 */
export function isAuthenticated(): boolean {
  try {
    const auth = localStorage.getItem('auth');
    if (!auth) return false;
    
    const parsed = JSON.parse(auth);
    return !!(parsed?.access_token || parsed?.token);
  } catch {
    return false;
  }
}
