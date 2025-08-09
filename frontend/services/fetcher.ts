// services/fetcher.ts
import axios, {
  AxiosError,
  AxiosInstance,
  AxiosResponse,
  AxiosHeaders,
  InternalAxiosRequestConfig,
} from 'axios';

function normalizeBase(url?: string) {
<<<<<<< Updated upstream
  if (!url) return url
  // quita barra final para evitar // al concatenar
  return url.endsWith('/') ? url.slice(0, -1) : url
}

const rawBaseURL = process.env.NEXT_PUBLIC_API_URL
const baseURL = normalizeBase(rawBaseURL)

if (!baseURL) {
  if (typeof window !== 'undefined') {
    console.error('[fetcher] Falta NEXT_PUBLIC_API_URL en .env')
=======
  if (!url) return url;
  // quita barra final para evitar // al concatenar
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

const rawBaseURL = process.env.NEXT_PUBLIC_API_URL;
const baseURL = normalizeBase(rawBaseURL);

if (!baseURL) {
  if (typeof window !== 'undefined') {
    console.error('[fetcher] Falta NEXT_PUBLIC_API_URL en .env');
>>>>>>> Stashed changes
  }
}

export const fetcher: AxiosInstance = axios.create({
<<<<<<< Updated upstream
  baseURL,                // e.g. https://softwareloyallight-production.up.railway.app
  timeout: 25000,
  withCredentials: false, // solo Bearer, sin cookies
})

// Logs: solo en dev
const isDev = process.env.NODE_ENV !== 'production'
if (typeof window !== 'undefined' && isDev) {
  console.log('[fetcher] baseURL =', baseURL)
}

fetcher.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (!config.headers) config.headers = new AxiosHeaders()
=======
  baseURL, // e.g. https://softwareloyallight-production.up.railway.app
  timeout: 25000,
  withCredentials: false, // solo Bearer, sin cookies
});

// Logs: solo en dev
const isDev = process.env.NODE_ENV !== 'production';
if (typeof window !== 'undefined' && isDev) {
  console.log('[fetcher] baseURL =', baseURL);
}

fetcher.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (!config.headers) config.headers = new AxiosHeaders();
>>>>>>> Stashed changes

  // Authorization Bearer si existe
  if (typeof window !== 'undefined') {
    try {
      const raw = localStorage.getItem('auth');
      if (raw) {
        const { token } = JSON.parse(raw) as { token?: string };
        if (token) (config.headers as AxiosHeaders).set('Authorization', `Bearer ${token}`);
      }
<<<<<<< Updated upstream
    } catch { /* noop */ }
  }

  if (isDev) {
    console.log('[fetcher][request]', {
      method: config.method,
      url: `${config.baseURL ?? ''}${config.url ?? ''}`,
    })
  }
  return config
})
=======
    } catch {
      /* noop */
    }
  }

  if (isDev) {
    console.log('[fetcher][request]', {
      method: config.method,
      url: `${config.baseURL ?? ''}${config.url ?? ''}`,
    });
  }
  return config;
});
>>>>>>> Stashed changes

fetcher.interceptors.response.use(
  (res: AxiosResponse) => res,
  (err: AxiosError) => {
    if (isDev) {
      console.error('[fetcher] Axios error:', {
        message: err.message,
        url: err.config?.baseURL ? `${err.config.baseURL}${err.config.url ?? ''}` : err.config?.url,
        status: err.response?.status,
        data: err.response?.data,
<<<<<<< Updated upstream
      })
    }
    return Promise.reject(err)
  }
)
=======
      });
    }
    return Promise.reject(err);
  },
);
>>>>>>> Stashed changes
