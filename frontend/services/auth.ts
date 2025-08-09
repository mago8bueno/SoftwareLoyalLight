// services/auth.ts
// Servicio de autenticación: login contra el backend y normaliza la respuesta.

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
 * Normaliza la respuesta del backend a { token, user? }.
 */
export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const { data } = await fetcher.post<BackendLoginResponseA | BackendLoginResponseB>(
    '/auth/login/', // 👈 Añadida barra final para coincidir con backend
    payload,
  );

  const token =
    (data as BackendLoginResponseA).access_token ?? (data as BackendLoginResponseB).token;

  if (!token) {
    // eslint-disable-next-line no-console
    console.error('[auth.login] Respuesta inesperada del backend:', data);
    throw new Error('Respuesta de login no válida (falta token)');
  }

  const user = (data as any).user;
  return { token, user };
}
