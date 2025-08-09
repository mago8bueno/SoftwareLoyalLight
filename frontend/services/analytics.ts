// services/analytics.ts
// Endpoints de analítica (Dashboard): tendencia de ventas, top clientes/productos y churn risk.
// Usa la instancia Axios `fetcher` (con baseURL y Authorization) definida en `services/fetcher.ts`.

import { fetcher } from './fetcher'

/** Serie temporal de ingresos por día (últimos 7 días) */
export type SalesPoint = { day: string; revenue: number }

/** Top clientes por gasto en los últimos 90 días */
export type TopCustomer = {
  client_id: number
  client_name: string
  email: string | null
  orders_count: number
  total_spent: number
}

/** Top productos por unidades vendidas en los últimos 90 días */
export type TopProduct = {
  item_id: number
  item_name: string
  units_sold: number
  revenue: number
}

/** Clientes en riesgo de churn según su última compra */
export type ChurnRisk = {
  client_id: number
  name: string
  email: string | null
  last_purchase_at: string | null
  churn_score: number
}

/**
 * Utilidad pequeña para envolver llamadas y garantizar que siempre devolvemos arrays.
 * Deja trazas útiles si el backend falla.
 */
async function safeGetArray<T>(path: string, params?: Record<string, unknown>): Promise<T[]> {
  try {
    const { data } = await fetcher.get<T[]>(path, { params })
    // Normaliza: si el backend devolviera algo raro, caemos a []
    return Array.isArray(data) ? data : []
  } catch (err) {
    // El interceptor de fetcher ya loguea detalles; aquí solo devolvemos []
    return []
  }
}

/** GET /analytics/trend7d -> [{ day, revenue }] */
export function getSalesTrend7d(): Promise<SalesPoint[]> {
  return safeGetArray<SalesPoint>('/analytics/trend7d')
}

/** GET /analytics/top-customers?limit=N */
export function getTopCustomers90d(limit = 5): Promise<TopCustomer[]> {
  return safeGetArray<TopCustomer>('/analytics/top-customers', { limit })
}

/** GET /analytics/top-products?limit=N */
export function getTopProducts90d(limit = 5): Promise<TopProduct[]> {
  return safeGetArray<TopProduct>('/analytics/top-products', { limit })
}

/** GET /analytics/churn-risk?limit=N */
export function getChurnRisk(limit = 5): Promise<ChurnRisk[]> {
  return safeGetArray<ChurnRisk>('/analytics/churn-risk', { limit })
}
