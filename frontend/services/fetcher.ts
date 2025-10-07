// services/fetcher.ts — VERSIÓN CORREGIDA Y ENDURECIDA
import axios, {
  AxiosError,
  AxiosInstance,
  AxiosResponse,
  AxiosHeaders,
  InternalAxiosRequestConfig,
} from "axios";

/* ==========================
   Resolución de baseURL
   ========================== */
function normalizeBase(url?: string | null) {
  if (!url) return url ?? undefined;
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

const isBrowser = typeof window !== "undefined";
const envBase =
  // Compatibilidad con diferentes nombres:
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof import.meta !== "undefined" ? (import.meta as any).env?.VITE_API_BASE_URL : undefined);

const fallbackProd = "https://softwareloyallight-production.up.railway.app";
const fallbackDev = "https://softwareloyallight-production.up.railway.app";
const isProdHost = isBrowser && /vercel\.app$/.test(window.location.hostname);

// Forzar HTTPS siempre - solución temporal
let baseURL = normalizeBase(envBase) || (isProdHost ? fallbackProd : fallbackDev);

// 🔧 FIX TEMPORAL: Forzar HTTPS si detectamos HTTP
if (baseURL && baseURL.startsWith('http://')) {
  baseURL = baseURL.replace('http://', 'https://');
  console.warn('[fetcher] URL convertida a HTTPS:', baseURL);
}

/* ==========================
   Axios instance
   ========================== */
export const fetcher: AxiosInstance = axios.create({
  baseURL,
  timeout: 25000,
  withCredentials: false,
  headers: { 
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest"
  },
});

if (isBrowser) {
  console.log("[fetcher] ===== CONFIGURACIÓN FETCHER =====");
  console.log("[fetcher] envBase =", envBase);
  console.log("[fetcher] isProdHost =", isProdHost);
  console.log("[fetcher] baseURL final =", baseURL);
  console.log("[fetcher] =================================");
}

/* ==========================
   Helpers auth (solo cliente)
   ========================== */
function readAuthFromStorage():
  | { access_token?: string; token_type?: string; user?: any }
  | null {
  if (!isBrowser) return null;
  try {
    const raw = localStorage.getItem("auth");
    if (!raw) return null;
    const parsed = JSON.parse(raw);

    // Compatibilidad con formatos antiguos { token, user }:
    const access_token: string | undefined =
      parsed?.access_token ?? parsed?.token ?? undefined;
    const token_type: string | undefined =
      parsed?.token_type ?? (parsed?.access_token ? "bearer" : undefined);

    return access_token
      ? { access_token, token_type, user: parsed?.user }
      : null;
  } catch {
    return null;
  }
}

/* ==========================
   Interceptor de REQUEST
   ========================== */
fetcher.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (!config.headers) config.headers = new AxiosHeaders();

  // 🔧 FIX CRÍTICO: Forzar HTTPS en todas las peticiones
  if (config.baseURL && config.baseURL.startsWith('http://')) {
    config.baseURL = config.baseURL.replace('http://', 'https://');
    console.warn('[fetcher] 🚨 URL forzada a HTTPS:', config.baseURL);
  }

  // 🔍 DEBUG: Log de la URL que se va a usar
  if (isBrowser) {
    console.log("[fetcher] 🌐 Petición a:", `${config.baseURL}${config.url}`);
    console.log("[fetcher] 🔍 URL completa:", config.baseURL, "+", config.url);
    console.log("[fetcher] 🔍 Método:", config.method);
    console.log("[fetcher] 🔍 Headers:", config.headers);
  }

  if (isBrowser) {
    const auth = readAuthFromStorage();

    if (auth?.access_token) {
      // Nunca loguees el token en claro
      const preview = `${auth.access_token.slice(0, 6)}…${auth.access_token.slice(-4)}`;
      console.debug("[fetcher] Añadiendo Authorization: Bearer <token>", {
        tokenPreview: preview,
        tokenType: auth.token_type || "bearer",
      });

      (config.headers as AxiosHeaders).set(
        "Authorization",
        `Bearer ${auth.access_token}`
      );
    } else {
      console.warn("[fetcher] No hay token en storage → petición saldrá sin Authorization");
    }

    // DEBUG para rutas sensibles (sin exponer secretos)
    if (config.url?.includes("/analytics/")) {
      const hasAuth = !!(config.headers as AxiosHeaders).get?.("Authorization");
      console.debug("[fetcher] Headers → /analytics/*", {
        hasAuthorization: hasAuth,
        url: `${baseURL}${config.url}`,
      });
    }
  }

  return config;
});

/* ==========================
   Interceptor de RESPONSE
   ========================== */
let alreadyHandled401 = false;

fetcher.interceptors.response.use(
  (res: AxiosResponse) => {
    if (res.config.url?.includes("/analytics/")) {
      console.debug("[fetcher] ✅ Analytics response:", {
        status: res.status,
        dataKeys: res?.data ? Object.keys(res.data) : [],
        url: res.config.url,
      });
    }
    return res;
  },
  (err: AxiosError) => {
    const url = err.config?.baseURL
      ? `${err.config.baseURL}${err.config?.url ?? ""}`
      : err.config?.url;

    const isAnalytics = err.config?.url?.includes("/analytics/") ?? false;

    console.error(
      `[fetcher] ${isAnalytics ? "🔴 ANALYTICS" : "Axios"} error:`,
      {
        message: err.message,
        url,
        status: err.response?.status,
        data: err.response?.data,
      }
    );

    const status = err.response?.status;

    if (status === 401) {
      console.error("[fetcher] 🚫 401 no autorizado: token inválido/expirado");

      if (isBrowser && !alreadyHandled401) {
        alreadyHandled401 = true; // evita bucles
        try {
          localStorage.removeItem("auth");
        } catch {}
        // Redirige siempre a login en el primer 401
        // (si quieres condicionar por ruta, hazlo aquí)
        window.location.href = "/login";
      }
    } else if (status === 403) {
      console.error("[fetcher] 🚫 403: sin permisos");
    } else if (status === 422) {
      console.error("[fetcher] 🚫 422: datos inválidos");
    }

    return Promise.reject(err);
  }
);

/* ==========================
   Debug helper (p/ consola)
   ========================== */
export function debugFetcher() {
  console.log("=== DEBUG FETCHER ===");
  console.log("baseURL:", baseURL);
  console.log("isBrowser:", isBrowser);

  if (isBrowser) {
    const auth = readAuthFromStorage();
    console.log("auth in storage:", {
      hasAccessToken: !!auth?.access_token,
      tokenType: auth?.token_type,
      userId: auth?.user?.id,
    });
  }
}

if (isBrowser) {
  (window as any).debugFetcher = debugFetcher;
  (window as any).fetcherInstance = fetcher;
  
  // 🔍 DEBUG: Verificar si hay múltiples instancias
  console.log("[fetcher] 🔧 Instancia creada:", fetcher.defaults.baseURL);
}
