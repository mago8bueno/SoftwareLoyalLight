// services/fetcher.ts
import axios, {
  AxiosError,
  AxiosInstance,
  AxiosResponse,
  AxiosHeaders,
  InternalAxiosRequestConfig,
} from 'axios'

const baseURL = process.env.NEXT_PUBLIC_API_URL

if (!baseURL) {
  // eslint-disable-next-line no-console
  console.error('[fetcher] Falta NEXT_PUBLIC_API_URL en .env.local')
}

export const fetcher: AxiosInstance = axios.create({
  baseURL,                // ej: http://localhost:8000  (sin barra final)
  timeout: 25000,         // subimos a 25s para descartar latencia
  withCredentials: false, // no enviamos cookies, solo Bearer
})

// Log básico en cliente
if (typeof window !== 'undefined') {
  console.log('[fetcher] baseURL =', baseURL)
}

// Log pre-request para ver método y URL finales
fetcher.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (!config.headers) config.headers = new AxiosHeaders()
  // Añade Authorization si hay token
  if (typeof window !== 'undefined') {
    try {
      const raw = localStorage.getItem('auth')
      if (raw) {
        const { token } = JSON.parse(raw) as { token?: string }
        if (token) (config.headers as AxiosHeaders).set('Authorization', `Bearer ${token}`)
      }
    } catch {}
  }
  // eslint-disable-next-line no-console
  console.log('[fetcher][request]', { method: config.method, baseURL: config.baseURL, url: config.url })
  return config
})

fetcher.interceptors.response.use(
  (res: AxiosResponse) => res,
  (err: AxiosError) => {
    // eslint-disable-next-line no-console
    console.error('[fetcher] Axios error:', {
      message: err.message,
      url: err.config?.baseURL ? `${err.config.baseURL}${err.config.url ?? ''}` : err.config?.url,
      status: err.response?.status,
      data: err.response?.data,
    })
    return Promise.reject(err)
  }
)
