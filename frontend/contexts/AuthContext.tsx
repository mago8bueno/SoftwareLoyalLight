// contexts/AuthContext.tsx
// Contexto de autenticación (Next.js - Pages Router) con:
// - Hidratación desde localStorage
// - Flags: isReady, isAuthenticated
// - Sincronización entre pestañas (storage event)
// - Helpers: getAuthHeader()
// Alineado con backend: { access_token, token_type: "bearer", user }

import { createContext, useState, useEffect, ReactNode, useContext, useMemo } from "react";
import { useRouter } from "next/router";
import { login as apiLogin } from "@services/auth";

// ==== Tipos que usa el frontend (alineados con el backend) ====
export type AuthUser = {
  id: string;
  email?: string;
  name?: string | null;
};

export type AuthState = {
  access_token: string;
  token_type: string; // "bearer"
  user?: AuthUser | null;
};

type AuthContextValue = {
  auth: AuthState | null;
  isReady: boolean;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  getAuthHeader: () => Record<string, string>;
};

const AuthContext = createContext<AuthContextValue>({
  auth: null,
  isReady: false,
  isAuthenticated: false,
  signIn: async () => {},
  signOut: () => {},
  getAuthHeader: () => ({}),
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [isReady, setIsReady] = useState(false);
  const router = useRouter();

  // ---- Hidratación inicial desde localStorage ----
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem("auth");
      if (raw) {
        const parsed = JSON.parse(raw) as AuthState;
        if (
          parsed &&
          typeof parsed.access_token === "string" &&
          parsed.access_token.trim().length > 0 &&
          typeof parsed.token_type === "string"
        ) {
          setAuth(parsed);
        } else {
          localStorage.removeItem("auth");
        }
      }
    } catch {
      localStorage.removeItem("auth");
    } finally {
      setIsReady(true);
    }
  }, []);

  // ---- Sincronización entre pestañas ----
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onStorage = (e: StorageEvent) => {
      if (e.key === "auth") {
        if (e.newValue) {
          try {
            const parsed = JSON.parse(e.newValue) as AuthState;
            if (parsed?.access_token) setAuth(parsed);
            else setAuth(null);
          } catch {
            setAuth(null);
          }
        } else {
          setAuth(null);
        }
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const isAuthenticated = !!auth?.access_token;

  // ---- Helpers ----
  const getAuthHeader = () =>
    auth?.access_token ? { Authorization: `Bearer ${auth.access_token}` } : {};

  // ---- Acciones ----
  const signIn = async (email: string, password: string) => {
    // El servicio devuelve: { access_token, token_type, user }
    const resp = await apiLogin({ email, password });

    // Normalizamos por si el servicio cambia nombres accidentalmente
    const next: AuthState = {
      access_token: (resp as any).access_token ?? (resp as any).token ?? "",
      token_type: (resp as any).token_type ?? "bearer",
      user: (resp as any).user ?? null,
    };

    if (!next.access_token) {
      // Evita persistir estados inválidos
      throw new Error("Login sin token. Revisa la respuesta del backend.");
    }

    setAuth(next);
    if (typeof window !== "undefined") {
      localStorage.setItem("auth", JSON.stringify(next));
    }
    await router.push("/");
  };

  const signOut = () => {
    setAuth(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem("auth");
    }
    router.push("/login");
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      auth,
      isReady,
      isAuthenticated,
      signIn,
      signOut,
      getAuthHeader,
    }),
    [auth, isReady, isAuthenticated]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Hook de consumo
export function useAuth() {
  return useContext(AuthContext);
}

export default AuthContext;
