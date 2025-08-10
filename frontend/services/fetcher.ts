// services/fetcher.ts
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

// Fallbacks seguros:
const fallbackProd = "https://softwareloyallight-production.up.railway.app";
const fallbackDev = "http://localhost:8000";

const isBrowser = typeof window !== "undefined";
const isProdHost = isBrowser && /vercel\.app$/.test(window.location.hostname);

const baseURL =
  normalizeBase(raw) ||
  (isProdHost ? fallbackProd : fallbackDev); // ← fuerza Railway en vercel.app

export const fetcher: AxiosInstance = axios.create({
  baseURL,
  timeout: 25000,
  withCredentials: false,
  headers: { "Content-Type": "application/json" },
});

// Log mínimo en cliente
if (isBrowser) {
  // eslint-disable-next-line no-console
  console.log("[fetcher] baseURL =", baseURL);
}

fetcher.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (!config.headers) config.headers = new AxiosHeaders();

  // Bearer + multi-tenant header desde localStorage si existe
  if (isBrowser) {
    try {
      const rawAuth = localStorage.getItem("auth");
      if (rawAuth) {
        const parsed = JSON.parse(rawAuth);
        const token: string | undefined = parsed?.token ?? parsed?.access_token;
        const userId: string | undefined =
          parsed?.userId ?? parsed?.user?.id; // soporta ambos formatos

        if (token) (config.headers as AxiosHeaders).set("Authorization", `Bearer ${token}`);
        if (userId) (config.headers as AxiosHeaders).set("X-User-Id", userId);
      }
    } catch {
      /* no-op */
    }
  }
  return config;
});

fetcher.interceptors.response.use(
  (res: AxiosResponse) => res,
  (err: AxiosError) => {
    // eslint-disable-next-line no-console
    console.error("[fetcher] Axios error:", {
      message: err.message,
      url: err.config?.baseURL ? `${err.config.baseURL}${err.config.url ?? ""}` : err.config?.url,
      status: err.response?.status,
      data: err.response?.data,
    });
    return Promise.reject(err);
  }
);
