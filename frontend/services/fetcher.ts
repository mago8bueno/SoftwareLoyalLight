// services/fetcher.ts - VERSIÓN CON DEBUGGING MEJORADO
import axios, {
  AxiosError,
  AxiosInstance,
  AxiosResponse,
  AxiosHeaders,
  InternalAxiosRequestConfig,
} from "axios";

function normalizeBase(url?: string) {
  if (!url) return url;
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

const raw = process.env.NEXT_PUBLIC_API_URL;
const fallbackProd = "https://softwareloyallight-production.up.railway.app";
const fallbackDev = "http://localhost:8000";

const isBrowser = typeof window !== "undefined";
const isProdHost = isBrowser && /vercel\.app$/.test(window.location.hostname);

const baseURL = normalizeBase(raw) || (isProdHost ? fallbackProd : fallbackDev);

export const fetcher: AxiosInstance = axios.create({
  baseURL,
  timeout: 25000,
  withCredentials: false,
  headers: { "Content-Type": "application/json" },
});

if (isBrowser) {
  console.log("[fetcher] baseURL =", baseURL);
}

// 🔧 INTERCEPTOR DE REQUEST MEJORADO CON DEBUGGING
fetcher.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (!config.headers) config.headers = new AxiosHeaders();

  if (isBrowser) {
    try {
      const rawAuth = localStorage.getItem("auth");
      
      // 🐛 DEBUG: Mostrar auth completo
      console.log("[fetcher] Auth raw:", rawAuth);
      
      if (rawAuth) {
        const parsed = JSON.parse(rawAuth);
        const token: string | undefined = parsed?.token ?? parsed?.access_token;
        const userId: string | undefined = parsed?.user?.id;

        console.log("[fetcher] Parsed auth:", {
          hasToken: !!token,
          tokenLength: token?.length || 0,
          hasUserId: !!userId,
          userId: userId
        });

        if (token) {
          (config.headers as AxiosHeaders).set("Authorization", `Bearer ${token}`);
          console.log("[fetcher] ✅ Token agregado a headers");
        } else {
          console.warn("[fetcher] ❌ No hay token disponible");
        }
        
        if (userId) {
          (config.headers as AxiosHeaders).set("X-User-Id", userId);
          console.log("[fetcher] ✅ User-Id agregado:", userId);
        }
      } else {
        console.warn("[fetcher] ❌ No hay auth en localStorage");
      }
      
      // 🐛 DEBUG: Mostrar headers finales para requests importantes
      if (config.url?.includes('/analytics/')) {
        console.log("[fetcher] Headers para analytics:", {
          authorization: config.headers.get('Authorization'),
          userId: config.headers.get('X-User-Id'),
          url: `${baseURL}${config.url}`
        });
      }
      
    } catch (error) {
      console.error("[fetcher] Error parsing auth:", error);
    }
  }
  
  return config;
});

// 🔧 INTERCEPTOR DE RESPONSE MEJORADO
fetcher.interceptors.response.use(
  (res: AxiosResponse) => {
    // Success logging para analytics
    if (res.config.url?.includes('/analytics/')) {
      console.log("[fetcher] ✅ Analytics response:", {
        status: res.status,
        dataKeys: Object.keys(res.data || {}),
        url: res.config.url
      });
    }
    return res;
  },
  (err: AxiosError) => {
    const isAnalytics = err.config?.url?.includes('/analytics/');
    
    console.error(`[fetcher] ${isAnalytics ? '🔴 ANALYTICS' : 'Axios'} error:`, {
      message: err.message,
      url: err.config?.baseURL ? `${err.config.baseURL}${err.config.url ?? ""}` : err.config?.url,
      status: err.response?.status,
      data: err.response?.data,
      headers: err.response?.headers
    });
    
    // Casos específicos de error
    if (err.response?.status === 401) {
      console.error("[fetcher] 🚫 Error 401: Token inválido o expirado");
      // Opcional: limpiar localStorage y redirigir al login
      if (isBrowser && isAnalytics) {
        console.warn("[fetcher] Considerando limpiar auth y redirigir...");
      }
    } else if (err.response?.status === 403) {
      console.error("[fetcher] 🚫 Error 403: Sin permisos");
    } else if (err.response?.status === 422) {
      console.error("[fetcher] 🚫 Error 422: Datos inválidos");
    }
    
    return Promise.reject(err);
  }
);

// 🆕 FUNCIÓN DE DEBUGGING PARA EL FETCHER
export function debugFetcher() {
  console.log("=== DEBUG FETCHER ===");
  console.log("baseURL:", baseURL);
  console.log("isBrowser:", isBrowser);
  
  if (isBrowser) {
    const auth = localStorage.getItem('auth');
    console.log("localStorage auth:", auth);
    
    if (auth) {
      try {
        const parsed = JSON.parse(auth);
        console.log("Parsed auth:", {
          hasToken: !!parsed.token,
          hasAccessToken: !!parsed.access_token,
          hasUser: !!parsed.user,
          userId: parsed.user?.id
        });
      } catch (e) {
        console.error("Error parsing auth:", e);
      }
    }
  }
}

// Para usar desde la consola del navegador
if (isBrowser) {
  (window as any).debugFetcher = debugFetcher;
}
